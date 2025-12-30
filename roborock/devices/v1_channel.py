"""V1 Channel for Roborock devices.

This module provides a unified channel interface for V1 protocol devices,
handling both MQTT and local connections with automatic fallback.
"""

import asyncio
import datetime
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from roborock.data import HomeDataDevice, NetworkInfo, RoborockBase, UserData
from roborock.exceptions import RoborockException
from roborock.mqtt.health_manager import HealthManager
from roborock.mqtt.session import MqttParams, MqttSession
from roborock.protocols.v1_protocol import (
    CommandType,
    MapResponse,
    ParamsType,
    RequestMessage,
    ResponseData,
    ResponseMessage,
    SecurityData,
    V1RpcChannel,
    create_map_response_decoder,
    create_security_data,
    decode_rpc_response,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand
from roborock.util import RoborockLoggerAdapter

from .cache import DeviceCache
from .channel import Channel
from .local_channel import LocalChannel, LocalSession, create_local_session
from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "create_v1_channel",
]

_T = TypeVar("_T", bound=RoborockBase)
_TIMEOUT = 10.0


# Exponential backoff parameters for reconnecting to local
MIN_RECONNECT_INTERVAL = datetime.timedelta(minutes=1)
MAX_RECONNECT_INTERVAL = datetime.timedelta(minutes=10)
RECONNECT_MULTIPLIER = 1.5
# After this many hours, the network info is refreshed
NETWORK_INFO_REFRESH_INTERVAL = datetime.timedelta(hours=12)
# Interval to check that the local connection is healthy
LOCAL_CONNECTION_CHECK_INTERVAL = datetime.timedelta(seconds=15)


@dataclass(frozen=True)
class RpcStrategy:
    """Strategy for encoding/sending/decoding RPC commands."""

    name: str  # For debug logging
    channel: LocalChannel | MqttChannel
    encoder: Callable[[RequestMessage], RoborockMessage]
    decoder: Callable[[RoborockMessage], ResponseMessage | MapResponse | None]
    health_manager: HealthManager | None = None


class RpcChannel(V1RpcChannel):
    """Provides an RPC interface around a pub/sub transport channel."""

    def __init__(self, rpc_strategies_cb: Callable[[], list[RpcStrategy]], logger: RoborockLoggerAdapter) -> None:
        """Initialize the RpcChannel with an ordered list of strategies."""
        self._rpc_strategies_cb = rpc_strategies_cb
        self._logger = logger

    async def send_command(
        self,
        method: CommandType,
        *,
        response_type: type[_T] | None = None,
        params: ParamsType = None,
    ) -> _T | Any:
        """Send a command and return either a decoded or parsed response."""
        request = RequestMessage(method, params=params)

        # Try each channel in order until one succeeds
        last_exception = None
        for strategy in self._rpc_strategies_cb():
            try:
                decoded_response = await self._send_rpc(strategy, request, self._logger)
            except RoborockException as e:
                self._logger.debug("Command %s failed on %s channel: %s", method, strategy.name, e)
                last_exception = e
            except Exception as e:
                self._logger.exception("Unexpected error sending command %s on %s channel", method, strategy.name)
                last_exception = RoborockException(f"Unexpected error: {e}")
            else:
                if response_type is not None:
                    if not isinstance(decoded_response, dict):
                        raise RoborockException(
                            f"Expected dict response to parse {response_type.__name__}, got {type(decoded_response)}"
                        )
                    return response_type.from_dict(decoded_response)
                return decoded_response

        raise last_exception or RoborockException("No available connection to send command")

    @staticmethod
    async def _send_rpc(
        strategy: RpcStrategy, request: RequestMessage, logger: RoborockLoggerAdapter
    ) -> ResponseData | bytes:
        """Send a command and return a decoded response type.

        This provides an RPC interface over a given channel strategy. The device
        channel only supports publish and subscribe, so this function handles
        associating requests with their corresponding responses.
        """
        future: asyncio.Future[ResponseData | bytes] = asyncio.Future()
        logger.debug(
            "Sending command (%s, request_id=%s): %s, params=%s",
            strategy.name,
            request.request_id,
            request.method,
            request.params,
        )

        message = strategy.encoder(request)

        def find_response(response_message: RoborockMessage) -> None:
            try:
                decoded = strategy.decoder(response_message)
            except RoborockException as ex:
                logger.debug("Exception while decoding message (%s): %s", response_message, ex)
                return
            if decoded is None:
                return
            logger.debug("Received response (%s, request_id=%s)", strategy.name, decoded.request_id)
            if decoded.request_id == request.request_id:
                if isinstance(decoded, ResponseMessage) and decoded.api_error:
                    future.set_exception(decoded.api_error)
                else:
                    future.set_result(decoded.data)

        unsub = await strategy.channel.subscribe(find_response)
        try:
            await strategy.channel.publish(message)
            result = await asyncio.wait_for(future, timeout=_TIMEOUT)
        except TimeoutError as ex:
            if strategy.health_manager:
                await strategy.health_manager.on_timeout()
            future.cancel()
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
        finally:
            unsub()
        if strategy.health_manager:
            await strategy.health_manager.on_success()
        return result


class V1Channel(Channel):
    """Unified V1 protocol channel with automatic MQTT/local connection handling.

    This channel abstracts away the complexity of choosing between MQTT and local
    connections, and provides high-level V1 protocol methods. It automatically
    handles connection setup, fallback logic, and protocol encoding/decoding.
    """

    def __init__(
        self,
        device_uid: str,
        security_data: SecurityData,
        mqtt_channel: MqttChannel,
        local_session: LocalSession,
        device_cache: DeviceCache,
    ) -> None:
        """Initialize the V1Channel."""
        self._device_uid = device_uid
        self._logger = RoborockLoggerAdapter(duid=device_uid, logger=_LOGGER)
        self._security_data = security_data
        self._mqtt_channel = mqtt_channel
        self._local_session = local_session
        self._local_channel: LocalChannel | None = None
        self._mqtt_unsub: Callable[[], None] | None = None
        self._local_unsub: Callable[[], None] | None = None
        self._callback: Callable[[RoborockMessage], None] | None = None
        self._device_cache = device_cache
        self._reconnect_task: asyncio.Task[None] | None = None
        self._last_network_info_refresh: datetime.datetime | None = None

    @property
    def is_connected(self) -> bool:
        """Return whether any connection is available."""
        return self.is_mqtt_connected or self.is_local_connected

    @property
    def is_local_connected(self) -> bool:
        """Return whether local connection is available."""
        return self._local_channel is not None and self._local_channel.is_connected

    @property
    def is_mqtt_connected(self) -> bool:
        """Return whether MQTT connection is available."""
        return self._mqtt_channel.is_connected

    @property
    def rpc_channel(self) -> V1RpcChannel:
        """Return the combined RPC channel that prefers local with a fallback to MQTT.

        The returned V1RpcChannel may be long lived and will respect the
        current connection state of the underlying channels.
        """

        def rpc_strategies_cb() -> list[RpcStrategy]:
            strategies = []
            if local_rpc_strategy := self._create_local_rpc_strategy():
                strategies.append(local_rpc_strategy)
            strategies.append(self._create_mqtt_rpc_strategy())
            return strategies

        return RpcChannel(rpc_strategies_cb, self._logger)

    @property
    def mqtt_rpc_channel(self) -> V1RpcChannel:
        """Return the MQTT-only RPC channel.

        The returned V1RpcChannel may be long lived and will respect the
        current connection state of the underlying channels.
        """
        return RpcChannel(lambda: [self._create_mqtt_rpc_strategy()], self._logger)

    @property
    def map_rpc_channel(self) -> V1RpcChannel:
        """Return the map RPC channel used for fetching map content."""
        decoder = create_map_response_decoder(security_data=self._security_data)
        return RpcChannel(lambda: [self._create_mqtt_rpc_strategy(decoder)], self._logger)

    def _create_local_rpc_strategy(self) -> RpcStrategy | None:
        """Create the RPC strategy for local transport."""
        if self._local_channel is None or not self.is_local_connected:
            return None
        return RpcStrategy(
            name="local",
            channel=self._local_channel,
            encoder=self._local_encoder,
            decoder=decode_rpc_response,
        )

    def _local_encoder(self, x: RequestMessage) -> RoborockMessage:
        """Encode a request message for local transport.

        This will read the current local channel's protocol version which
        changes as the protocol version is discovered.
        """
        if self._local_channel is None:
            raise ValueError("Local channel unavailable for encoding")
        return x.encode_message(
            RoborockMessageProtocol.GENERAL_REQUEST,
            version=self._local_channel.protocol_version,
        )

    def _create_mqtt_rpc_strategy(self, decoder: Callable[[RoborockMessage], Any] = decode_rpc_response) -> RpcStrategy:
        """Create the RPC strategy for MQTT transport with optional custom decoder."""
        return RpcStrategy(
            name="mqtt",
            channel=self._mqtt_channel,
            encoder=lambda x: x.encode_message(
                RoborockMessageProtocol.RPC_REQUEST,
                security_data=self._security_data,
            ),
            decoder=decoder,
            health_manager=self._mqtt_channel.health_manager,
        )

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to all messages from the device.

        This will first attempt to establish a local connection to the device
        using cached network information if available. If that fails, it will
        fall back to using the MQTT connection.

        A background task will be started to monitor and maintain the local
        connection, attempting to reconnect as needed.

        Args:
            callback: Callback to invoke for each received message.

        Returns:
            Unsubscribe function to stop receiving messages and clean up resources.
        """
        if self._callback is not None:
            raise ValueError("Only one subscription allowed at a time")

        # Make an initial, optimistic attempt to connect to local with the
        # cache. The cache information will be refreshed by the background task.
        try:
            await self._local_connect(prefer_cache=True)
        except RoborockException as err:
            self._logger.debug("First local connection attempt failed, will retry: %s", err)

        # Start a background task to manage the local connection health. This
        # happens independent of whether we were able to connect locally now.
        if self._reconnect_task is None:
            loop = asyncio.get_running_loop()
            self._reconnect_task = loop.create_task(self._background_reconnect())

        if not self.is_local_connected:
            # We were not able to connect locally, so fallback to MQTT and at least
            # establish that connection explicitly. If this fails then raise an
            # error and let the caller know we failed to subscribe.
            self._mqtt_unsub = await self._mqtt_channel.subscribe(self._on_mqtt_message)
            self._logger.debug("V1Channel connected to device via MQTT")

        def unsub() -> None:
            """Unsubscribe from all messages."""
            if self._reconnect_task:
                self._reconnect_task.cancel()
                self._reconnect_task = None
            if self._mqtt_unsub:
                self._mqtt_unsub()
                self._mqtt_unsub = None
            if self._local_unsub:
                self._local_unsub()
                self._local_unsub = None
            self._logger.debug("Unsubscribed from device")

        self._callback = callback
        return unsub

    async def _get_networking_info(self, *, prefer_cache: bool = True) -> NetworkInfo:
        """Retrieve networking information for the device.

        This is a cloud only command used to get the local device's IP address.
        """
        device_cache_data = await self._device_cache.get()

        if prefer_cache and device_cache_data.network_info:
            self._logger.debug("Using cached network info")
            return device_cache_data.network_info
        try:
            network_info = await self.mqtt_rpc_channel.send_command(
                RoborockCommand.GET_NETWORK_INFO, response_type=NetworkInfo
            )
        except RoborockException as e:
            self._logger.debug("Error fetching network info for device")
            if device_cache_data.network_info:
                self._logger.debug("Falling back to cached network info after error")
                return device_cache_data.network_info
            raise RoborockException(f"Network info failed for device {self._device_uid}") from e
        self._logger.debug("Network info for device: %s", network_info)
        self._last_network_info_refresh = datetime.datetime.now(datetime.UTC)

        device_cache_data = await self._device_cache.get()
        device_cache_data.network_info = network_info
        await self._device_cache.set(device_cache_data)
        return network_info

    async def _local_connect(self, *, prefer_cache: bool = True) -> None:
        """Set up local connection if possible."""
        self._logger.debug("Attempting to connect to local channel (prefer_cache=%s)", prefer_cache)
        networking_info = await self._get_networking_info(prefer_cache=prefer_cache)
        host = networking_info.ip
        self._logger.debug("Connecting to local channel at %s", host)
        # Create a new local channel and connect
        local_channel = self._local_session(host)
        try:
            await local_channel.connect()
        except RoborockException as e:
            raise RoborockException(f"Error connecting to local device {self._device_uid}: {e}") from e
        # Wire up the new channel
        self._local_channel = local_channel
        self._local_unsub = await self._local_channel.subscribe(self._on_local_message)
        self._logger.info("Connected to local channel successfully")

    async def _background_reconnect(self) -> None:
        """Task to run in the background to manage the local connection."""
        self._logger.debug("Starting background task to manage local connection")
        reconnect_backoff = MIN_RECONNECT_INTERVAL
        local_connect_failures = 0

        while True:
            try:
                if self.is_local_connected:
                    await asyncio.sleep(LOCAL_CONNECTION_CHECK_INTERVAL.total_seconds())
                    continue

                # Not connected, so wait with backoff before trying to connect.
                # The first time through, we don't sleep, we just try to connect.
                local_connect_failures += 1
                if local_connect_failures > 1:
                    await asyncio.sleep(reconnect_backoff.total_seconds())
                    reconnect_backoff = min(reconnect_backoff * RECONNECT_MULTIPLIER, MAX_RECONNECT_INTERVAL)

                use_cache = self._should_use_cache(local_connect_failures)
                await self._local_connect(prefer_cache=use_cache)
                # Reset backoff and failures on success
                reconnect_backoff = MIN_RECONNECT_INTERVAL
                local_connect_failures = 0

            except asyncio.CancelledError:
                self._logger.debug("Background reconnect task cancelled")
                if self._local_channel:
                    self._local_channel.close()
                return
            except RoborockException as err:
                self._logger.debug("Background reconnect failed: %s", err)
            except Exception:
                self._logger.exception("Unhandled exception in background reconnect task")

    def _should_use_cache(self, local_connect_failures: int) -> bool:
        """Determine whether to use cached network info on retries.

        On the first retry we'll avoid the cache to handle the case where
        the network ip may have recently changed. Otherwise, use the cache
        if available then expire at some point.
        """
        if local_connect_failures == 1:
            return False
        elif self._last_network_info_refresh and (
            datetime.datetime.now(datetime.UTC) - self._last_network_info_refresh > NETWORK_INFO_REFRESH_INTERVAL
        ):
            return False
        return True

    def _on_mqtt_message(self, message: RoborockMessage) -> None:
        """Handle incoming MQTT messages."""
        self._logger.debug("V1Channel received MQTT message: %s", message)
        if self._callback:
            self._callback(message)

    def _on_local_message(self, message: RoborockMessage) -> None:
        """Handle incoming local messages."""
        self._logger.debug("V1Channel received local message: %s", message)
        if self._callback:
            self._callback(message)


def create_v1_channel(
    user_data: UserData,
    mqtt_params: MqttParams,
    mqtt_session: MqttSession,
    device: HomeDataDevice,
    device_cache: DeviceCache,
) -> V1Channel:
    """Create a V1Channel for the given device."""
    security_data = create_security_data(user_data.rriot)
    mqtt_channel = MqttChannel(mqtt_session, device.duid, device.local_key, user_data.rriot, mqtt_params)
    local_session = create_local_session(device.local_key, device.duid)
    return V1Channel(
        device.duid,
        security_data,
        mqtt_channel,
        local_session=local_session,
        device_cache=device_cache,
    )

"""V1 Channel for Roborock devices.

This module provides a unified channel interface for V1 protocol devices,
handling both MQTT and local connections with automatic fallback.
"""

import asyncio
import datetime
import logging
from collections.abc import Callable
from typing import TypeVar

from roborock.data import HomeDataDevice, NetworkInfo, RoborockBase, UserData
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams, MqttSession
from roborock.protocols.v1_protocol import (
    SecurityData,
    create_security_data,
)
from roborock.roborock_message import RoborockMessage
from roborock.roborock_typing import RoborockCommand

from .cache import Cache
from .channel import Channel
from .local_channel import LocalChannel, LocalSession, create_local_session
from .mqtt_channel import MqttChannel
from .v1_rpc_channel import (
    PickFirstAvailable,
    V1RpcChannel,
    create_local_rpc_channel,
    create_map_rpc_channel,
    create_mqtt_rpc_channel,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "V1Channel",
]

_T = TypeVar("_T", bound=RoborockBase)

# Exponential backoff parameters for reconnecting to local
MIN_RECONNECT_INTERVAL = datetime.timedelta(minutes=1)
MAX_RECONNECT_INTERVAL = datetime.timedelta(minutes=10)
RECONNECT_MULTIPLIER = 1.5
# After this many hours, the network info is refreshed
NETWORK_INFO_REFRESH_INTERVAL = datetime.timedelta(hours=12)
# Interval to check that the local connection is healthy
LOCAL_CONNECTION_CHECK_INTERVAL = datetime.timedelta(seconds=15)


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
        cache: Cache,
    ) -> None:
        """Initialize the V1Channel.

        Args:
            mqtt_channel: MQTT channel for cloud communication
            local_session: Factory that creates LocalChannels for a hostname.
        """
        self._device_uid = device_uid
        self._mqtt_channel = mqtt_channel
        self._mqtt_rpc_channel = create_mqtt_rpc_channel(mqtt_channel, security_data)
        self._local_session = local_session
        self._local_channel: LocalChannel | None = None
        self._local_rpc_channel: V1RpcChannel | None = None
        # Prefer local, fallback to MQTT
        self._combined_rpc_channel = PickFirstAvailable(
            [lambda: self._local_rpc_channel, lambda: self._mqtt_rpc_channel]
        )
        self._map_rpc_channel = create_map_rpc_channel(mqtt_channel, security_data)
        self._mqtt_unsub: Callable[[], None] | None = None
        self._local_unsub: Callable[[], None] | None = None
        self._callback: Callable[[RoborockMessage], None] | None = None
        self._cache = cache
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
        return self._mqtt_unsub is not None and self._mqtt_channel.is_connected

    @property
    def rpc_channel(self) -> V1RpcChannel:
        """Return the combined RPC channel prefers local with a fallback to MQTT."""
        return self._combined_rpc_channel

    @property
    def mqtt_rpc_channel(self) -> V1RpcChannel:
        """Return the MQTT RPC channel."""
        return self._mqtt_rpc_channel

    @property
    def map_rpc_channel(self) -> V1RpcChannel:
        """Return the map RPC channel used for fetching map content."""
        return self._map_rpc_channel

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
            await self._local_connect(use_cache=True)
        except RoborockException as err:
            _LOGGER.warning("Could not establish local connection for device %s: %s", self._device_uid, err)

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
            _LOGGER.debug("V1Channel connected to device %s via MQTT", self._device_uid)

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
            _LOGGER.debug("Unsubscribed from device %s", self._device_uid)

        self._callback = callback
        return unsub

    async def _get_networking_info(self, *, use_cache: bool = True) -> NetworkInfo:
        """Retrieve networking information for the device.

        This is a cloud only command used to get the local device's IP address.
        """
        cache_data = await self._cache.get()
        if use_cache and cache_data.network_info and (network_info := cache_data.network_info.get(self._device_uid)):
            _LOGGER.debug("Using cached network info for device %s", self._device_uid)
            return network_info
        try:
            network_info = await self._mqtt_rpc_channel.send_command(
                RoborockCommand.GET_NETWORK_INFO, response_type=NetworkInfo
            )
        except RoborockException as e:
            raise RoborockException(f"Network info failed for device {self._device_uid}") from e
        _LOGGER.debug("Network info for device %s: %s", self._device_uid, network_info)
        self._last_network_info_refresh = datetime.datetime.now(datetime.UTC)
        cache_data.network_info[self._device_uid] = network_info
        await self._cache.set(cache_data)
        return network_info

    async def _local_connect(self, *, use_cache: bool = True) -> None:
        """Set up local connection if possible."""
        _LOGGER.debug(
            "Attempting to connect to local channel for device %s (use_cache=%s)", self._device_uid, use_cache
        )
        networking_info = await self._get_networking_info(use_cache=use_cache)
        host = networking_info.ip
        _LOGGER.debug("Connecting to local channel at %s", host)
        # Create a new local channel and connect
        local_channel = self._local_session(host)
        try:
            await local_channel.connect()
        except RoborockException as e:
            raise RoborockException(f"Error connecting to local device {self._device_uid}: {e}") from e
        # Wire up the new channel
        self._local_channel = local_channel
        await self._local_channel.hello()
        self._local_rpc_channel = create_local_rpc_channel(self._local_channel)
        self._local_unsub = await self._local_channel.subscribe(self._on_local_message)
        _LOGGER.info("Successfully connected to local device %s", self._device_uid)

    async def _background_reconnect(self) -> None:
        """Task to run in the background to manage the local connection."""
        _LOGGER.debug("Starting background task to manage local connection for %s", self._device_uid)
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
                await self._local_connect(use_cache=use_cache)
                # Reset backoff and failures on success
                reconnect_backoff = MIN_RECONNECT_INTERVAL
                local_connect_failures = 0

            except asyncio.CancelledError:
                _LOGGER.debug("Background reconnect task cancelled")
                if self._local_channel:
                    self._local_channel.close()
                return
            except RoborockException as err:
                _LOGGER.debug("Background reconnect failed: %s", err)
            except Exception:
                _LOGGER.exception("Unhandled exception in background reconnect task")

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
        _LOGGER.debug("V1Channel received MQTT message from device %s: %s", self._device_uid, message)
        if self._callback:
            self._callback(message)

    def _on_local_message(self, message: RoborockMessage) -> None:
        """Handle incoming local messages."""
        _LOGGER.debug("V1Channel received local message from device %s: %s", self._device_uid, message)
        if self._callback:
            self._callback(message)


def create_v1_channel(
    user_data: UserData,
    mqtt_params: MqttParams,
    mqtt_session: MqttSession,
    device: HomeDataDevice,
    cache: Cache,
) -> V1Channel:
    """Create a V1Channel for the given device."""
    security_data = create_security_data(user_data.rriot)
    mqtt_channel = MqttChannel(mqtt_session, device.duid, device.local_key, user_data.rriot, mqtt_params)
    local_session = create_local_session(device.local_key)
    return V1Channel(device.duid, security_data, mqtt_channel, local_session=local_session, cache=cache)

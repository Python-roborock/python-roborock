"""V1 Channel for Roborock devices.

This module provides a unified channel interface for V1 protocol devices,
handling both MQTT and local connections with automatic fallback.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from roborock.containers import HomeDataDevice, NetworkInfo, RoborockBase, UserData
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
from .v1_rpc_channel import V1RpcChannel, create_combined_rpc_channel, create_mqtt_rpc_channel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "V1Channel",
]

_T = TypeVar("_T", bound=RoborockBase)


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
        self._combined_rpc_channel: V1RpcChannel | None = None
        self._mqtt_unsub: Callable[[], None] | None = None
        self._local_unsub: Callable[[], None] | None = None
        self._callback: Callable[[RoborockMessage], None] | None = None
        self._cache = cache

    @property
    def is_connected(self) -> bool:
        """Return whether any connection is available."""
        return self.is_mqtt_connected or self.is_local_connected

    @property
    def is_local_connected(self) -> bool:
        """Return whether local connection is available."""
        return self._local_unsub is not None

    @property
    def is_mqtt_connected(self) -> bool:
        """Return whether MQTT connection is available."""
        return self._mqtt_unsub is not None and self._mqtt_channel.is_connected

    @property
    def rpc_channel(self) -> V1RpcChannel:
        """Return the combined RPC channel prefers local with a fallback to MQTT."""
        return self._combined_rpc_channel or self._mqtt_rpc_channel

    @property
    def mqtt_rpc_channel(self) -> V1RpcChannel:
        """Return the MQTT RPC channel."""
        return self._mqtt_rpc_channel

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to all messages from the device.

        This will establish MQTT connection first, and also attempt to set up
        local connection if possible. Any failures to subscribe to MQTT will raise
        a RoborockException. A local connection failure will not raise an exception,
        since the local connection is optional.
        """

        if self._mqtt_unsub:
            raise ValueError("Already connected to the device")
        self._callback = callback

        # First establish MQTT connection
        self._mqtt_unsub = await self._mqtt_channel.subscribe(self._on_mqtt_message)
        _LOGGER.debug("V1Channel connected to device %s via MQTT", self._device_uid)

        # Try to establish an optional local connection as well.
        try:
            self._local_unsub = await self._local_connect()
        except RoborockException as err:
            _LOGGER.warning("Could not establish local connection for device %s: %s", self._device_uid, err)
        else:
            _LOGGER.debug("Local connection established for device %s", self._device_uid)

        def unsub() -> None:
            """Unsubscribe from all messages."""
            if self._mqtt_unsub:
                self._mqtt_unsub()
                self._mqtt_unsub = None
            if self._local_unsub:
                self._local_unsub()
                self._local_unsub = None
            _LOGGER.debug("Unsubscribed from device %s", self._device_uid)

        return unsub

    async def _get_networking_info(self) -> NetworkInfo:
        """Retrieve networking information for the device.

        This is a cloud only command used to get the local device's IP address.
        """
        cache_data = await self._cache.get()
        if cache_data.network_info and (network_info := cache_data.network_info.get(self._device_uid)):
            _LOGGER.debug("Using cached network info for device %s", self._device_uid)
            return network_info
        try:
            network_info = await self._mqtt_rpc_channel.send_command(
                RoborockCommand.GET_NETWORK_INFO, response_type=NetworkInfo
            )
        except RoborockException as e:
            raise RoborockException(f"Network info failed for device {self._device_uid}") from e
        _LOGGER.debug("Network info for device %s: %s", self._device_uid, network_info)
        cache_data.network_info[self._device_uid] = network_info
        await self._cache.set(cache_data)
        return network_info

    async def _local_connect(self) -> Callable[[], None]:
        """Set up local connection if possible."""
        _LOGGER.debug("Attempting to connect to local channel for device %s", self._device_uid)
        networking_info = await self._get_networking_info()
        host = networking_info.ip
        _LOGGER.debug("Connecting to local channel at %s", host)
        self._local_channel = self._local_session(host)
        try:
            await self._local_channel.connect()
        except RoborockException as e:
            self._local_channel = None
            raise RoborockException(f"Error connecting to local device {self._device_uid}: {e}") from e
        self._combined_rpc_channel = create_combined_rpc_channel(self._local_channel, self._mqtt_rpc_channel)
        return await self._local_channel.subscribe(self._on_local_message)

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

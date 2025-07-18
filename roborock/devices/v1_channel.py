"""V1 Channel for Roborock devices.

This module provides a unified channel interface for V1 protocol devices,
handling both MQTT and local connections with automatic fallback.
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from roborock.containers import HomeDataDevice, NetworkInfo, RoborockBase, UserData
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams, MqttSession
from roborock.protocols.v1_protocol import (
    CommandType,
    ParamsType,
    SecurityData,
    create_mqtt_payload_encoder,
    create_security_data,
    decode_rpc_response,
    encode_local_payload,
)
from roborock.roborock_message import RoborockMessage
from roborock.roborock_typing import RoborockCommand

from .local_channel import LocalChannel, LocalSession, create_local_session
from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "V1Channel",
]

_T = TypeVar("_T", bound=RoborockBase)


class V1Channel:
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
    ) -> None:
        """Initialize the V1Channel.

        Args:
            mqtt_channel: MQTT channel for cloud communication
            local_session: Factory that creates LocalChannels for a hostname.
        """
        self._device_uid = device_uid
        self._mqtt_channel = mqtt_channel
        self._mqtt_payload_encoder = create_mqtt_payload_encoder(security_data)
        self._local_session = local_session
        self._local_channel: LocalChannel | None = None
        self._mqtt_unsub: Callable[[], None] | None = None
        self._local_unsub: Callable[[], None] | None = None
        self._callback: Callable[[RoborockMessage], None] | None = None
        self._networking_info: NetworkInfo | None = None

    @property
    def is_local_connected(self) -> bool:
        """Return whether local connection is available."""
        return self._local_unsub is not None

    @property
    def is_mqtt_connected(self) -> bool:
        """Return whether MQTT connection is available."""
        return self._mqtt_unsub is not None

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to all messages from the device.

        This will establish MQTT connection first, and also attempt to set up
        local connection if possible.
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
        try:
            return await self._send_mqtt_decoded_command(RoborockCommand.GET_NETWORK_INFO, response_type=NetworkInfo)
        except RoborockException as e:
            raise RoborockException(f"Network info failed for device {self._device_uid}") from e

    async def _local_connect(self) -> Callable[[], None]:
        """Set up local connection if possible."""
        _LOGGER.debug("Attempting to connect to local channel for device %s", self._device_uid)
        if self._networking_info is None:
            self._networking_info = await self._get_networking_info()
        host = self._networking_info.ip
        _LOGGER.debug("Connecting to local channel at %s", host)
        self._local_channel = self._local_session(host)
        try:
            await self._local_channel.connect()
        except RoborockException as e:
            self._local_channel = None
            raise RoborockException(f"Error connecting to local device {self._device_uid}: {e}") from e

        return await self._local_channel.subscribe(self._on_local_message)

    async def send_decoded_command(
        self,
        method: CommandType,
        *,
        response_type: type[_T],
        params: ParamsType = None,
    ) -> _T:
        """Send a command using the best available transport.

        Will try local connection first if available and preferred,
        falling back to MQTT if needed.
        """
        _LOGGER.debug("Sending command: %s, params=%s", method, params)
        if self._local_channel:
            try:
                return await self._send_local_decoded_command(method, response_type=response_type, params=params)
            except RoborockException as e:
                _LOGGER.info("Local command failed, falling back to MQTT: %s", e)

        return await self._send_mqtt_decoded_command(method, response_type=response_type, params=params)

    async def _send_mqtt_raw_command(self, method: CommandType, params: ParamsType | None = None) -> dict[str, Any]:
        """Send a raw command without response handling."""
        message = self._mqtt_payload_encoder(method, params)
        _LOGGER.debug("Sending MQTT message for device %s: %s", self._device_uid, message)
        _LOGGER.debug("Channel=%s", self._mqtt_channel)
        response = await self._mqtt_channel.send_command(message)
        return decode_rpc_response(response)

    async def _send_mqtt_decoded_command(
        self, method: CommandType, *, response_type: type[_T], params: ParamsType | None = None
    ) -> _T:
        """Send a command over MQTT and decode the response."""
        decoded_response = await self._send_mqtt_raw_command(method, params)
        return response_type.from_dict(decoded_response)

    async def _send_local_raw_command(self, method: CommandType, params: ParamsType | None = None) -> dict[str, Any]:
        """Send a raw command over local connection."""
        if not self._local_channel:
            raise RoborockException("Local channel is not connected")

        message = encode_local_payload(method, params)
        _LOGGER.debug("Sending local message for device %s: %s", self._device_uid, message)
        response = await self._local_channel.send_command(message)
        return decode_rpc_response(response)

    async def _send_local_decoded_command(
        self, method: CommandType, *, response_type: type[_T], params: ParamsType | None = None
    ) -> _T:
        """Send a command over local connection and decode the response."""
        if not self._local_channel:
            raise RoborockException("Local channel is not connected")
        decoded_response = await self._send_local_raw_command(method, params)
        return response_type.from_dict(decoded_response)

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
    user_data: UserData, mqtt_params: MqttParams, mqtt_session: MqttSession, device: HomeDataDevice
) -> V1Channel:
    """Create a V1Channel for the given device."""
    security_data = create_security_data(user_data.rriot)
    mqtt_channel = MqttChannel(mqtt_session, device.duid, device.local_key, user_data.rriot, mqtt_params)
    local_session = create_local_session(device.local_key)
    return V1Channel(device.duid, security_data, mqtt_channel, local_session=local_session)

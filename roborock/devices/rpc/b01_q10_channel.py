"""Thin wrapper around the MQTT channel for Roborock B01 Q10 devices."""

import logging
from collections.abc import AsyncGenerator, Callable
from typing import Protocol

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.transport.channel import Channel
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import (
    ParamsType,
    Q10Message,
    decode_message,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage

_LOGGER = logging.getLogger(__name__)


class Q10RpcChannel(Protocol):
    """Protocol for Q10 RPC channels."""

    async def send_command(
        self,
        command: B01_Q10_DP,
        params: ParamsType = None,
    ) -> None:
        """Send a command on the MQTT channel, without waiting for a response."""
        ...


class B01Q10Channel(Channel, Q10RpcChannel):
    """Unified B01 Q10 channel wrapping MQTT transport."""

    def __init__(self, mqtt_channel: MqttChannel) -> None:
        self._mqtt_channel = mqtt_channel

    @property
    def is_connected(self) -> bool:
        return self._mqtt_channel.is_connected

    @property
    def is_local_connected(self) -> bool:
        return False

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        return await self._mqtt_channel.subscribe(callback)

    async def subscribe_stream(self) -> AsyncGenerator[Q10Message, None]:
        """Stream decoded Q10 messages received via MQTT."""
        async for msg in stream_decoded_messages(self._mqtt_channel):
            yield msg

    async def send_command(
        self,
        command: B01_Q10_DP,
        params: ParamsType = None,
    ) -> None:
        await send_command(self._mqtt_channel, command, params)


async def stream_decoded_messages(
    mqtt_channel: MqttChannel,
) -> AsyncGenerator[Q10Message, None]:
    """Stream decoded Q10 messages received via MQTT.

    Each pushed ``RoborockMessage`` is decoded into a typed :data:`Q10Message`
    (a DPS status update, a map packet, or a trace packet). Messages that fail
    to decode or carry an unrecognized payload are skipped.
    """

    async for message in mqtt_channel.subscribe_stream():
        try:
            decoded = decode_message(message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 Q10 message: %s: %s",
                message,
                ex,
            )
            continue
        if decoded is not None:
            yield decoded


async def send_command(
    mqtt_channel: MqttChannel,
    command: B01_Q10_DP,
    params: ParamsType,
) -> None:
    """Send a command on the MQTT channel, without waiting for a response"""
    _LOGGER.debug("Sending B01 MQTT command: cmd=%s params=%s", command, params)
    roborock_message = encode_mqtt_payload(command, params)
    _LOGGER.debug("Sending MQTT message: %s", roborock_message)
    try:
        await mqtt_channel.publish(roborock_message)
    except RoborockException as ex:
        _LOGGER.debug(
            "Error sending B01 decoded command (method=%s params=%s): %s",
            command,
            params,
            ex,
        )
        raise


def create_b01_q10_channel(mqtt_channel: MqttChannel) -> B01Q10Channel:
    """Create a B01Q10Channel wrapping MQTT transport."""
    return B01Q10Channel(mqtt_channel)

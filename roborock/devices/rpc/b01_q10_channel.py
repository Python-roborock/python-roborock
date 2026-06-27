"""Thin wrapper around the MQTT channel for Roborock B01 Q10 devices."""

import logging
from collections.abc import AsyncGenerator

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import (
    ParamsType,
    Q10Message,
    decode_message,
    encode_mqtt_payload,
)

_LOGGER = logging.getLogger(__name__)


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

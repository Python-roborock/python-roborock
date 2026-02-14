"""Thin wrapper around the MQTT channel for Roborock B01 Q10 devices."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import ParamsType, encode_mqtt_payload
from roborock.protocols.b01_q10_protocol import decode_rpc_response

_LOGGER = logging.getLogger(__name__)


async def stream_decoded_responses(
    mqtt_channel: MqttChannel,
) -> AsyncGenerator[dict[B01_Q10_DP, Any], None]:
    """Stream decoded DPS messages received via MQTT."""

    async for response_message in mqtt_channel.subscribe_stream():
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 RPC response: %s: %s",
                response_message,
                ex,
            )
            continue
        yield decoded_dps


async def send_command(
    mqtt_channel: MqttChannel,
    command: B01_Q10_DP,
    params: ParamsType,
) -> None:
    """Send a command on the MQTT channel, without waiting for a response."""
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

"""Thin wrapper around the MQTT channel for Roborock B01 devices."""

from __future__ import annotations

import logging
from typing import Any

from roborock.protocols.b01_protocol import (
    CommandType,
    ParamsType,
    decode_rpc_response,
    encode_mqtt_payload,
)

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    dps: int,
    command: CommandType,
    params: ParamsType,
) -> dict[int, Any]:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending MQTT command: %s", params)
    roborock_message = encode_mqtt_payload(dps, command, params)
    response = await mqtt_channel.send_message(roborock_message)
    return decode_rpc_response(response)  # type: ignore[return-value]

"""Thin wrapper around the MQTT channel for Roborock A01 devices."""

from __future__ import annotations

import logging
from typing import Any, overload

from roborock.protocols.a01_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)


@overload
async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockDyadDataProtocol, Any],
) -> dict[RoborockDyadDataProtocol, Any]:
    ...


@overload
async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockZeoProtocol, Any],
) -> dict[RoborockZeoProtocol, Any]:
    ...


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockDyadDataProtocol, Any] | dict[RoborockZeoProtocol, Any],
) -> dict[RoborockDyadDataProtocol, Any] | dict[RoborockZeoProtocol, Any]:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending MQTT command: %s", params)
    roborock_message = encode_mqtt_payload(params)
    response = await mqtt_channel.send_message(roborock_message)
    return decode_rpc_response(response)  # type: ignore[return-value]

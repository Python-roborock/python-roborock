"""Thin wrapper around the MQTT channel for Roborock B01 devices."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from roborock.exceptions import RoborockException
from roborock.protocols.b01_protocol import (
    CommandType,
    ParamsType,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage
from roborock.util import get_next_int

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    dps: int,
    command: CommandType,
    params: ParamsType,
) -> dict[str, Any]:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending MQTT command: %s", params)
    msg_id = get_next_int(100000000000, 999999999999)
    roborock_message = encode_mqtt_payload(dps, command, params, msg_id)
    finished = asyncio.Event()
    result: dict[str, Any] = {}

    def find_response(response_message: RoborockMessage) -> None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.info("Failed to decode b01 message: %s: %s", response_message, ex)
            return

        for _, dps_value in decoded_dps.items():
            # valid responses are JSON strings wrapped in the dps value
            if isinstance(dps_value, str):
                try:
                    inner = json.loads(dps_value)
                except (json.JSONDecodeError, TypeError):
                    _LOGGER.debug("Received unexpected response: %s", dps_value)
                    continue

                if isinstance(inner, dict) and inner.get("msgId") == msg_id:
                    _LOGGER.debug("Received query response: %s", inner)
                    data = inner.get("data")
                    if isinstance(data, dict):
                        result.update(data)
                    finished.set()
            else:
                _LOGGER.debug("Received unexpected response: %s", dps_value)

    unsub = await mqtt_channel.subscribe(find_response)

    _LOGGER.debug("Sending MQTT message: %s", roborock_message)
    try:
        await mqtt_channel.publish(roborock_message)
        try:
            await asyncio.wait_for(finished.wait(), timeout=_TIMEOUT)
        except TimeoutError as ex:
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
    finally:
        unsub()

    return result

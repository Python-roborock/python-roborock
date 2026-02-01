"""Thin wrapper around the MQTT channel for Roborock B01 Q10 devices."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import (
    ParamsType,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0


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


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    command: B01_Q10_DP,
    params: ParamsType,
    expected_dps: Iterable[B01_Q10_DP] | None = None,
) -> dict[B01_Q10_DP, Any]:
    """Send a command and await the first decoded response.

    Q10 responses are not correlated with a message id, so we filter on
    expected datapoints when provided.
    """
    roborock_message = encode_mqtt_payload(command, params)
    future: asyncio.Future[dict[B01_Q10_DP, Any]] = asyncio.get_running_loop().create_future()

    expected_set = set(expected_dps) if expected_dps is not None else None

    def find_response(response_message: RoborockMessage) -> None:
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 Q10 RPC response (expecting %s): %s: %s",
                command,
                response_message,
                ex,
            )
            return
        if expected_set and not any(dps in decoded_dps for dps in expected_set):
            return
        if not future.done():
            future.set_result(decoded_dps)

    unsub = await mqtt_channel.subscribe(find_response)

    _LOGGER.debug("Sending MQTT message: %s", roborock_message)
    try:
        await mqtt_channel.publish(roborock_message)
        return await asyncio.wait_for(future, timeout=_TIMEOUT)
    except TimeoutError as ex:
        raise RoborockException(f"B01 Q10 command timed out after {_TIMEOUT}s ({command})") from ex
    except RoborockException as ex:
        _LOGGER.warning(
            "Error sending B01 Q10 decoded command (%s): %s",
            command,
            ex,
        )
        raise
    except Exception as ex:
        _LOGGER.exception(
            "Error sending B01 Q10 decoded command (%s): %s",
            command,
            ex,
        )
        raise
    finally:
        unsub()

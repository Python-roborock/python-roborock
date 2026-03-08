"""Thin wrapper around the MQTT channel for Roborock B01 Q7 devices."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import (
    Q7RequestMessage,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0
_T = TypeVar("_T")


def _matches_map_response(response_message: RoborockMessage, *, version: bytes | None) -> bytes | None:
    """Return raw map payload bytes for matching MAP_RESPONSE messages."""
    if (
        response_message.protocol == RoborockMessageProtocol.MAP_RESPONSE
        and response_message.payload
        and response_message.version == version
    ):
        return response_message.payload
    return None


async def _send_command(
    mqtt_channel: MqttChannel,
    request_message: Q7RequestMessage,
    *,
    response_matcher: Callable[[RoborockMessage], _T | None],
    timeout_error: str,
) -> _T:
    """Publish a B01 command and resolve on the first matching response."""
    roborock_message = encode_mqtt_payload(request_message)
    future: asyncio.Future[_T] = asyncio.get_running_loop().create_future()

    def find_response(response_message: RoborockMessage) -> None:
        if future.done():
            return
        try:
            response = response_matcher(response_message)
        except Exception as ex:
            future.set_exception(ex)
            return
        if response is not None:
            future.set_result(response)

    unsub = await mqtt_channel.subscribe(find_response)
    try:
        await mqtt_channel.publish(roborock_message)
        return await asyncio.wait_for(future, timeout=_TIMEOUT)
    except TimeoutError as ex:
        raise RoborockException(timeout_error) from ex
    finally:
        unsub()


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    request_message: Q7RequestMessage,
) -> dict[str, Any] | None:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending B01 MQTT command: %s", request_message)

    def find_response(response_message: RoborockMessage) -> Any | None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 RPC response (expecting method=%s msg_id=%s): %s: %s",
                request_message.command,
                request_message.msg_id,
                response_message,
                ex,
            )
            return None
        for dps_value in decoded_dps.values():
            # valid responses are JSON strings wrapped in the dps value
            if not isinstance(dps_value, str):
                _LOGGER.debug("Received unexpected response: %s", dps_value)
                continue

            try:
                inner = json.loads(dps_value)
            except (json.JSONDecodeError, TypeError):
                _LOGGER.debug("Received unexpected response: %s", dps_value)
                continue
            if isinstance(inner, dict) and inner.get("msgId") == str(request_message.msg_id):
                _LOGGER.debug("Received query response: %s", inner)
                # Check for error code (0 = success, non-zero = error)
                code = inner.get("code", 0)
                if code != 0:
                    error_msg = f"B01 command failed with code {code} ({request_message})"
                    _LOGGER.debug("B01 error response: %s", error_msg)
                    raise RoborockException(error_msg)
                data = inner.get("data")
                # All get commands should be dicts
                if request_message.command.endswith(".get") and not isinstance(data, dict):
                    raise RoborockException(f"Unexpected data type for response {data} ({request_message})")
                return data
        return None

    try:
        return await _send_command(
            mqtt_channel,
            request_message,
            response_matcher=find_response,
            timeout_error=f"B01 command timed out after {_TIMEOUT}s ({request_message})",
        )
    except RoborockException as ex:
        _LOGGER.warning(
            "Error sending B01 decoded command (%ss): %s",
            request_message,
            ex,
        )
        raise

    except Exception as ex:
        _LOGGER.exception(
            "Error sending B01 decoded command (%ss): %s",
            request_message,
            ex,
        )
        raise


async def send_map_command(mqtt_channel: MqttChannel, request_message: Q7RequestMessage) -> bytes:
    """Send map upload command and wait for MAP_RESPONSE payload bytes.

    This stays separate from ``send_decoded_command()`` because map uploads arrive as
    raw ``MAP_RESPONSE`` payload bytes instead of a decoded RPC ``data`` payload.
    """

    version = encode_mqtt_payload(request_message).version
    return await _send_command(
        mqtt_channel,
        request_message,
        response_matcher=lambda response_message: _matches_map_response(response_message, version=version),
        timeout_error=f"B01 map command timed out after {_TIMEOUT}s ({request_message})",
    )

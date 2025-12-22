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
) -> dict[str, Any] | None:
    """Send a command on the MQTT channel and get a decoded response."""
    msg_id = str(get_next_int(100000000000, 999999999999))
    _LOGGER.debug(
        "Sending B01 MQTT command: dps=%s method=%s msg_id=%s params=%s",
        dps,
        command,
        msg_id,
        params,
    )
    roborock_message = encode_mqtt_payload(dps, command, params, msg_id)
    future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()

    def find_response(response_message: RoborockMessage) -> None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 RPC response (expecting method=%s msg_id=%s): %s: %s",
                command,
                msg_id,
                response_message,
                ex,
            )
            return

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

            if isinstance(inner, dict) and inner.get("msgId") == msg_id:
                _LOGGER.debug("Received query response: %s", inner)
                # Check for error code (0 = success, non-zero = error)
                code = inner.get("code", 0)
                if code != 0:
                    error_msg = (
                        f"B01 command failed with code {code} "
                        f"(method={command}, msg_id={msg_id}, dps={dps}, params={params})"
                    )
                    _LOGGER.debug("B01 error response: %s", error_msg)
                    if not future.done():
                        future.set_exception(RoborockException(error_msg))
                    return
                data = inner.get("data")
                # All get commands should be dicts
                if command.endswith(".get") and not isinstance(data, dict):
                    if not future.done():
                        future.set_exception(
                            RoborockException(
                                f"Unexpected data type for response "
                                f"(method={command}, msg_id={msg_id}, dps={dps}, params={params})"
                            )
                        )
                    return
                if not future.done():
                    future.set_result(data)

    unsub = await mqtt_channel.subscribe(find_response)

    _LOGGER.debug("Sending MQTT message: %s", roborock_message)
    try:
        await mqtt_channel.publish(roborock_message)
        return await asyncio.wait_for(future, timeout=_TIMEOUT)
    except TimeoutError as ex:
        raise RoborockException(
            f"B01 command timed out after {_TIMEOUT}s (method={command}, msg_id={msg_id}, dps={dps}, params={params})"
        ) from ex
    except RoborockException as ex:
        _LOGGER.warning(
            "Error sending B01 decoded command (method=%s msg_id=%s dps=%s params=%s): %s",
            command,
            msg_id,
            dps,
            params,
            ex,
        )
        raise

    except Exception as ex:
        _LOGGER.exception(
            "Error sending B01 decoded command (method=%s msg_id=%s dps=%s params=%s): %s",
            command,
            msg_id,
            dps,
            params,
            ex,
        )
        raise
    finally:
        unsub()

"""Thin wrapper around the MQTT channel for Roborock B01 Q7 devices."""

from __future__ import annotations

import asyncio
import json
import logging
import weakref
from typing import Any

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
_map_command_locks: weakref.WeakKeyDictionary[MqttChannel, asyncio.Lock] = weakref.WeakKeyDictionary()


def _get_map_command_lock(mqtt_channel: MqttChannel) -> asyncio.Lock:
    lock = _map_command_locks.get(mqtt_channel)
    if lock is None:
        lock = asyncio.Lock()
        _map_command_locks[mqtt_channel] = lock
    return lock


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    request_message: Q7RequestMessage,
) -> dict[str, Any] | None:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending B01 MQTT command: %s", request_message)
    roborock_message = encode_mqtt_payload(request_message)
    future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()

    def find_response(response_message: RoborockMessage) -> None:
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
            if isinstance(inner, dict) and inner.get("msgId") == str(request_message.msg_id):
                _LOGGER.debug("Received query response: %s", inner)
                # Check for error code (0 = success, non-zero = error)
                code = inner.get("code", 0)
                if code != 0:
                    error_msg = f"B01 command failed with code {code} ({request_message})"
                    _LOGGER.debug("B01 error response: %s", error_msg)
                    if not future.done():
                        future.set_exception(RoborockException(error_msg))
                    return
                data = inner.get("data")
                # All get commands should be dicts
                if request_message.command.endswith(".get") and not isinstance(data, dict):
                    if not future.done():
                        future.set_exception(
                            RoborockException(f"Unexpected data type for response {data} ({request_message})")
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
        raise RoborockException(f"B01 command timed out after {_TIMEOUT}s ({request_message})") from ex
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
    finally:
        unsub()


async def send_map_command(mqtt_channel: MqttChannel, request_message: Q7RequestMessage) -> bytes:
    """Send map upload command and wait for MAP_RESPONSE payload bytes.

    Map requests are serialized per channel so concurrent map calls cannot
    cross-wire responses between callers.
    """

    async with _get_map_command_lock(mqtt_channel):
        roborock_message = encode_mqtt_payload(request_message)
        future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

        def find_response(response_message: RoborockMessage) -> None:
            if future.done():
                return

            if response_message.protocol == RoborockMessageProtocol.MAP_RESPONSE and response_message.payload:
                if not future.done():
                    future.set_result(response_message.payload)
                return

            try:
                decoded_dps = decode_rpc_response(response_message)
            except RoborockException:
                return

            for dps_value in decoded_dps.values():
                if not isinstance(dps_value, str):
                    continue
                try:
                    inner = json.loads(dps_value)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(inner, dict) or inner.get("msgId") != str(request_message.msg_id):
                    continue
                code = inner.get("code", 0)
                if code != 0:
                    if not future.done():
                        future.set_exception(
                            RoborockException(f"B01 command failed with code {code} ({request_message})")
                        )
                    return
                data = inner.get("data")
                if isinstance(data, dict) and isinstance(data.get("payload"), str):
                    try:
                        if not future.done():
                            future.set_result(bytes.fromhex(data["payload"]))
                    except ValueError:
                        pass

        unsub = await mqtt_channel.subscribe(find_response)
        try:
            await mqtt_channel.publish(roborock_message)
            return await asyncio.wait_for(future, timeout=_TIMEOUT)
        except TimeoutError as ex:
            raise RoborockException(f"B01 map command timed out after {_TIMEOUT}s ({request_message})") from ex
        finally:
            unsub()

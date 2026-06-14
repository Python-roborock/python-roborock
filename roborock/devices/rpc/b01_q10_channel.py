"""Thin wrapper around the MQTT channel for Roborock B01 Q10 devices."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import (
    ParamsType,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)

# Requesting the device state (dpRequestDps) also makes the robot push its current
# map as a separate MAP_RESPONSE message a few seconds later. Q10 firmware throttles
# these pushes (~60-70s between maps), so callers should not poll tightly.
_MAP_TIMEOUT = 20.0


async def stream_decoded_responses(
    mqtt_channel: MqttChannel,
) -> AsyncGenerator[dict[B01_Q10_DP, Any], None]:
    """Stream decoded DPS messages received via MQTT."""

    async for response_message in mqtt_channel.subscribe_stream():
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 Q10 RPC response: %s: %s",
                response_message,
                ex,
            )
            continue
        yield decoded_dps


# MAP_RESPONSE (protocol 301) payloads start with a 2-byte marker identifying the
# packet kind: a full map (``01 01``) or a live trace/path (``02 01``).
_MAP_PACKET_MARKER = b"\x01\x01"
_TRACE_PACKET_MARKER = b"\x02\x01"


async def _request_map_response(mqtt_channel: MqttChannel, marker: bytes, what: str, timeout: float | None) -> bytes:
    """Trigger a map push and resolve on the first ``MAP_RESPONSE`` with ``marker``."""
    if timeout is None:
        timeout = _MAP_TIMEOUT
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()

    def on_message(message: RoborockMessage) -> None:
        if future.done():
            return
        if (
            message.protocol == RoborockMessageProtocol.MAP_RESPONSE
            and message.payload
            and message.payload[:2] == marker
        ):
            future.set_result(message.payload)

    unsub = await mqtt_channel.subscribe(on_message)
    try:
        await send_command(mqtt_channel, B01_Q10_DP.REQUEST_DPS, {})
        return await asyncio.wait_for(future, timeout=timeout)
    except TimeoutError as ex:
        raise RoborockException(f"Timed out waiting for Q10 {what} after {timeout}s") from ex
    finally:
        unsub()


async def request_map(mqtt_channel: MqttChannel, *, timeout: float | None = None) -> bytes:
    """Request the current map and return the raw ``01 01`` ``MAP_RESPONSE`` payload.

    The Q10 does not have a dedicated "get map" command. Instead, requesting the
    device state (``dpRequestDps``) triggers the robot to push its current map as
    a ``MAP_RESPONSE`` (protocol 301) message shortly afterwards.
    """
    return await _request_map_response(mqtt_channel, _MAP_PACKET_MARKER, "map", timeout)


async def request_trace(mqtt_channel: MqttChannel, *, timeout: float | None = None) -> bytes:
    """Request the live trace/path and return the raw ``02 01`` ``MAP_RESPONSE`` payload.

    The robot only emits trace packets while it is actively moving (cleaning), so
    this will time out for an idle/docked robot.
    """
    return await _request_map_response(mqtt_channel, _TRACE_PACKET_MARKER, "trace", timeout)


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

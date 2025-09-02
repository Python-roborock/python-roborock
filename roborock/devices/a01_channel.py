"""Thin wrapper around the MQTT channel for Roborock A01 devices."""

import asyncio
import logging
from typing import Any, overload

from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockZeoProtocol,
)

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0

# Both RoborockDyadDataProtocol and RoborockZeoProtocol have the same
# value for ID_QUERY
_ID_QUERY = int(RoborockDyadDataProtocol.ID_QUERY)


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

    # For commands that set values: send the command and do not
    # block waiting for a response. Queries are handled below.
    param_values = {int(k): v for k, v in params.items()}
    if not (query_values := param_values.get(_ID_QUERY)):
        await mqtt_channel.publish(roborock_message)
        return {}

    # Merge any results together than contain the requested data. This
    # does not use a future since it needs to merge results across responses.
    # This could be simplified if we can assume there is a single response.
    finished = asyncio.Event()
    result: dict[int, Any] = {}

    def find_response(response_message: RoborockMessage) -> None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.info("Failed to decode a01 message: %s: %s", response_message, ex)
            return
        for key, value in decoded.items():
            if key in query_values:
                result[key] = value
        if len(result) != len(query_values):
            _LOGGER.debug("Incomplete query response: %s != %s", result, query_values)
            return
        _LOGGER.debug("Received query response: %s", result)
        if not finished.is_set():
            finished.set()

    unsub = await mqtt_channel.subscribe(find_response)

    try:
        await mqtt_channel.publish(roborock_message)
        try:
            await asyncio.wait_for(finished.wait(), timeout=_TIMEOUT)
        except TimeoutError as ex:
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
    finally:
        unsub()

    return result  # type: ignore[return-value]

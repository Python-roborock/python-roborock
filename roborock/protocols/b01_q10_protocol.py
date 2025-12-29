"""Roborock B01 Protocol encoding and decoding."""

import json
import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
ParamsType = list | dict | int | None


def encode_mqtt_payload(command: B01_Q10_DP, params: ParamsType) -> RoborockMessage:
    """Encode payload for B01 commands over MQTT."""
    dps_data = {
        "dps": {
            command.code: params,
        }
    }
    # payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(dps_data).encode("utf-8"),
    )


def _convert_datapoints(datapoints: dict[str, Any], message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Convert the 'dps' dictionary keys from strings to B01_Q10_DP enums."""
    result = {}
    for key, value in datapoints.items():
        try:
            code = int(key)
        except ValueError as e:
            raise ValueError(f"dps key is not a valid integer: {e} for {message.payload!r}") from e
        try:
            dps = B01_Q10_DP.from_code(code)
        except ValueError as e:
            raise ValueError(f"dps key is not a valid B01_Q10_DP: {e} for {message.payload!r}") from e
        result[dps] = value
    return result


def decode_rpc_response(message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Decode a B01 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid B01 message format: missing payload")
    try:
        payload = json.loads(message.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RoborockException(f"Invalid B01 json payload: {e} for {message.payload!r}") from e

    if (datapoints := payload.get("dps")) is None:
        raise RoborockException(f"Invalid B01 json payload: missing 'dps' for {message.payload!r}")
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid B01 message format: 'dps' should be a dictionary for {message.payload!r}")

    try:
        result = _convert_datapoints(datapoints, message)
    except ValueError as e:
        raise RoborockException(f"Invalid B01 message format: {e}") from e

    # The COMMON response contains nested datapoints that also need conversion.
    # We will parse that here for now, but may move elsewhere as we add more
    # complex response parsing.
    if common_result := result.get(B01_Q10_DP.COMMON):
        if not isinstance(common_result, dict):
            raise RoborockException(f"Invalid dpCommon format: expected dict, got {type(common_result).__name__}")
        try:
            common_dps_result = _convert_datapoints(common_result, message)
        except ValueError as e:
            raise RoborockException(f"Invalid dpCommon format: {e}") from e
        result[B01_Q10_DP.COMMON] = common_dps_result

    return result

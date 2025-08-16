"""Roborock B01 Protocol encoding and decoding."""

import json
import logging
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock import RoborockB01Methods
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)
from roborock.util import get_next_int

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
CommandType = RoborockB01Methods | str
ParamsType = list | dict | int | None


def encode_mqtt_payload(dps: int, command: CommandType, params: ParamsType) -> RoborockMessage:
    """Encode payload for B01 commands over MQTT."""
    dps_data = {
        "dps": {
            dps: {
                "method": str(command),
                "msgId": str(get_next_int(100000000000, 999999999999)),
                "params": params or [],
            }
        }
    }
    payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=payload,
    )


def decode_rpc_response(message: RoborockMessage) -> dict[int, Any]:
    """Decode a B01 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid B01 message format: missing payload")
    try:
        unpadded = unpad(message.payload, AES.block_size)
    except ValueError as err:
        raise RoborockException(f"Unable to unpad B01 payload: {err}")

    try:
        payload = json.loads(unpadded.decode())
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(f"Invalid B01 message payload: {e} for {message.payload!r}") from e

    datapoints = payload.get("dps", {})
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid B01 message format: 'dps' should be a dictionary for {message.payload!r}")
    try:
        return {int(key): value for key, value in datapoints.items()}
    except ValueError:
        raise RoborockException(f"Invalid B01 message format: 'dps' key should be an integer for {message.payload!r}")

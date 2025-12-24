"""Roborock B01 Protocol encoding and decoding."""

import json
import logging
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock import RoborockB01Q7Methods
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
CommandType = RoborockB01Q7Methods | str
ParamsType = list | dict | int | None


def encode_b01_mqtt_payload(dps: dict[int, Any]) -> RoborockMessage:
    """Encode payload for B01 commands over MQTT with arbitrary DPs."""
    dps_data = {"dps": dps}
    payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=payload,
    )


def encode_q7_payload(dps: int, command: CommandType, params: ParamsType, msg_id: str) -> RoborockMessage:
    """Encode payload for Q7 commands over MQTT."""
    return encode_b01_mqtt_payload(
        {
            dps: {
                "method": str(command),
                "msgId": msg_id,
                # Important: some B01 methods use an empty object `{}` (not `[]`) for
                # "no params", and some setters legitimately send `0` which is falsy.
                # Only default to `[]` when params is actually None.
                "params": params if params is not None else [],
            }
        }
    )


def decode_rpc_response(message: RoborockMessage) -> dict[int, Any]:
    """Decode a B01 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid B01 message format: missing payload")
    try:
        unpadded = unpad(message.payload, AES.block_size)
    except ValueError:
        # It would be better to fail down the line.
        unpadded = message.payload

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

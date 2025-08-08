"""Roborock A01 Protocol encoding and decoding."""

import json
import logging
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)

A01_VERSION = b"A01"


def encode_mqtt_payload(
    data: dict[RoborockDyadDataProtocol, Any]
    | dict[RoborockZeoProtocol, Any]
    | dict[RoborockDyadDataProtocol | RoborockZeoProtocol, Any],
) -> RoborockMessage:
    """Encode payload for A01 commands over MQTT."""
    dps_data = {"dps": data}
    payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=A01_VERSION,
        payload=payload,
    )


def decode_rpc_response(message: RoborockMessage) -> dict[int, Any]:
    """Decode a V1 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid A01 message format: missing payload")
    try:
        unpadded = unpad(message.payload, AES.block_size)
    except ValueError as err:
        raise RoborockException(f"Unable to unpad A01 payload: {err}")

    try:
        payload = json.loads(unpadded.decode())
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(f"Invalid A01 message payload: {e} for {message.payload!r}") from e

    datapoints = payload.get("dps", {})
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid A01 message format: 'dps' should be a dictionary for {message.payload!r}")
    try:
        return {int(key): value for key, value in datapoints.items()}
    except ValueError:
        raise RoborockException(f"Invalid A01 message format: 'dps' key should be an integer for {message.payload!r}")

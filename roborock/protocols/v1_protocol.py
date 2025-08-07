"""Roborock V1 Protocol Encoder."""

from __future__ import annotations

import base64
import json
import logging
import math
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.containers import RRiot
from roborock.exceptions import RoborockException
from roborock.protocol import Utils
from roborock.roborock_message import MessageRetry, RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand
from roborock.util import get_next_int

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "SecurityData",
    "create_security_data",
    "create_mqtt_payload_encoder",
    "encode_local_payload",
    "decode_rpc_response",
]

CommandType = RoborockCommand | str
ParamsType = list | dict | int | None


@dataclass(frozen=True, kw_only=True)
class SecurityData:
    """Security data included in the request for some V1 commands."""

    endpoint: str
    nonce: bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert security data to a dictionary for sending in the payload."""
        return {"security": {"endpoint": self.endpoint, "nonce": self.nonce.hex().lower()}}


def create_security_data(rriot: RRiot) -> SecurityData:
    """Create a SecurityData instance for the given endpoint and nonce."""
    nonce = secrets.token_bytes(16)
    endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
    return SecurityData(endpoint=endpoint, nonce=nonce)


@dataclass
class RequestMessage:
    """Data structure for v1 RoborockMessage payloads."""

    method: RoborockCommand | str
    params: ParamsType
    timestamp: int = field(default_factory=lambda: math.floor(time.time()))
    request_id: int = field(default_factory=lambda: get_next_int(10000, 32767))

    def as_payload(self, security_data: SecurityData | None) -> bytes:
        """Convert the request arguments to a dictionary."""
        inner = {
            "id": self.request_id,
            "method": self.method,
            "params": self.params or [],
            **(security_data.to_dict() if security_data else {}),
        }
        return bytes(
            json.dumps(
                {
                    "dps": {"101": json.dumps(inner, separators=(",", ":"))},
                    "t": self.timestamp,
                },
                separators=(",", ":"),
            ).encode()
        )


def create_mqtt_payload_encoder(security_data: SecurityData) -> Callable[[CommandType, ParamsType], RoborockMessage]:
    """Create a payload encoder for V1 commands over MQTT."""

    def _get_payload(method: CommandType, params: ParamsType) -> RoborockMessage:
        """Build the payload for a V1 command."""
        request = RequestMessage(method=method, params=params)
        payload = request.as_payload(security_data)  # always secure
        return RoborockMessage(
            timestamp=request.timestamp,
            protocol=RoborockMessageProtocol.RPC_REQUEST,
            payload=payload,
        )

    return _get_payload


def encode_local_payload(method: CommandType, params: ParamsType) -> RoborockMessage:
    """Encode payload for V1 commands over local connection."""

    request = RequestMessage(method=method, params=params)
    payload = request.as_payload(security_data=None)

    message_retry: MessageRetry | None = None
    if method == RoborockCommand.RETRY_REQUEST and isinstance(params, dict):
        message_retry = MessageRetry(method=method, retry_id=params["retry_id"])

    return RoborockMessage(
        timestamp=request.timestamp,
        protocol=RoborockMessageProtocol.GENERAL_REQUEST,
        payload=payload,
        message_retry=message_retry,
    )


def decode_rpc_response(message: RoborockMessage) -> dict[str, Any]:
    """Decode a V1 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid V1 message format: missing payload")
    try:
        payload = json.loads(message.payload.decode())
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(f"Invalid V1 message payload: {e} for {message.payload!r}") from e

    _LOGGER.debug("Decoded V1 message payload: %s", payload)
    datapoints = payload.get("dps", {})
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid V1 message format: 'dps' should be a dictionary for {message.payload!r}")

    if not (data_point := datapoints.get("102")):
        raise RoborockException("Invalid V1 message format: missing '102' data point")

    try:
        data_point_response = json.loads(data_point)
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(f"Invalid V1 message data point '102': {e} for {message.payload!r}") from e

    if error := data_point_response.get("error"):
        raise RoborockException(f"Error in message: {error}")

    if not (result := data_point_response.get("result")):
        raise RoborockException(f"Invalid V1 message format: missing 'result' in data point for {message.payload!r}")
    _LOGGER.debug("Decoded V1 message result: %s", result)
    if isinstance(result, list) and result:
        result = result[0]
    if not isinstance(result, dict):
        raise RoborockException(f"Invalid V1 message format: 'result' should be a dictionary for {message.payload!r}")
    return result

"""Roborock V1 Protocol Encoder."""

from __future__ import annotations

import base64
import json
import logging
import math
import secrets
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.containers import RRiot
from roborock.exceptions import RoborockException
from roborock.protocol import Utils
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand
from roborock.util import get_next_int

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "SecurityData",
    "create_security_data",
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

    def to_diagnostic_data(self) -> dict[str, Any]:
        """Convert security data to a dictionary for debugging purposes."""
        return {"nonce": self.nonce.hex().lower()}


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

    def encode_message(
        self,
        protocol: RoborockMessageProtocol,
        security_data: SecurityData | None = None,
    ) -> RoborockMessage:
        """Convert the request message to a RoborockMessage."""
        return RoborockMessage(
            timestamp=self.timestamp,
            protocol=protocol,
            payload=self._as_payload(security_data=security_data),
        )

    def _as_payload(self, security_data: SecurityData | None) -> bytes:
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


@dataclass(kw_only=True, frozen=True)
class ResponseMessage:
    """Data structure for v1 RoborockMessage responses."""

    request_id: int | None
    """The request ID of the response."""

    data: dict[str, Any]
    """The data of the response."""


def decode_rpc_response(message: RoborockMessage) -> ResponseMessage:
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

    if not (data_point := datapoints.get(str(RoborockMessageProtocol.RPC_RESPONSE))):
        raise RoborockException(
            f"Invalid V1 message format: missing '{RoborockMessageProtocol.RPC_RESPONSE}' data point"
        )

    try:
        data_point_response = json.loads(data_point)
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(
            f"Invalid V1 message data point '{RoborockMessageProtocol.RPC_RESPONSE}': {e} for {message.payload!r}"
        ) from e

    request_id: int | None = data_point_response.get("id")
    if error := data_point_response.get("error"):
        raise RoborockException(f"Error in message: {error}")

    if not (result := data_point_response.get("result")):
        raise RoborockException(f"Invalid V1 message format: missing 'result' in data point for {message.payload!r}")
    _LOGGER.debug("Decoded V1 message result: %s", result)
    if isinstance(result, list) and result:
        result = result[0]
    if not isinstance(result, dict):
        raise RoborockException(f"Invalid V1 message format: 'result' should be a dictionary for {message.payload!r}")
    return ResponseMessage(request_id=request_id, data=result)


@dataclass
class MapResponse:
    """Data structure for the V1 Map response."""

    request_id: int
    """The request ID of the map response."""

    data: bytes
    """The map data, decrypted and decompressed."""


def create_map_response_decoder(security_data: SecurityData) -> Callable[[RoborockMessage], MapResponse]:
    """Create a decoder for V1 map response messages."""

    def _decode_map_response(message: RoborockMessage) -> MapResponse:
        """Decode a V1 map response message."""
        if not message.payload or len(message.payload) < 24:
            raise RoborockException("Invalid V1 map response format: missing payload")
        header, body = message.payload[:24], message.payload[24:]
        [endpoint, _, request_id, _] = struct.unpack("<8s8sH6s", header)
        if not endpoint.decode().startswith(security_data.endpoint):
            raise RoborockException(
                f"Invalid V1 map response endpoint: {endpoint!r}, expected {security_data.endpoint!r}"
            )
        try:
            decrypted = Utils.decrypt_cbc(body, security_data.nonce)
        except ValueError as err:
            raise RoborockException("Failed to decode map message payload") from err
        decompressed = Utils.decompress(decrypted)
        return MapResponse(request_id=request_id, data=decompressed)

    return _decode_map_response

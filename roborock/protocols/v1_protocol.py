"""Roborock V1 Protocol Encoder."""

from __future__ import annotations

import base64
import json
import logging
import secrets
import struct
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, TypeVar, overload

from roborock.data import RoborockBase, RRiot
from roborock.exceptions import RoborockException, RoborockInvalidStatus, RoborockUnsupportedFeature
from roborock.protocol import Utils
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand
from roborock.util import get_next_int, get_timestamp

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "SecurityData",
    "create_security_data",
    "decode_rpc_response",
    "V1RpcChannel",
]

CommandType = RoborockCommand | str
ParamsType = list | dict | int | None


class LocalProtocolVersion(StrEnum):
    """Supported local protocol versions. Different from vacuum protocol versions."""

    L01 = "L01"
    V1 = "1.0"


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
    timestamp: int = field(default_factory=lambda: get_timestamp())
    request_id: int = field(default_factory=lambda: get_next_int(10000, 32767))

    def encode_message(
        self,
        protocol: RoborockMessageProtocol,
        security_data: SecurityData | None = None,
        version: LocalProtocolVersion = LocalProtocolVersion.V1,
    ) -> RoborockMessage:
        """Convert the request message to a RoborockMessage."""
        return RoborockMessage(
            timestamp=self.timestamp,
            protocol=protocol,
            payload=self._as_payload(security_data=security_data),
            version=version.value.encode(),
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


ResponseData = dict[str, Any] | list | int

# V1 RPC error code mappings to specific exception types
_V1_ERROR_CODE_EXCEPTIONS: dict[int, type[RoborockException]] = {
    -10007: RoborockInvalidStatus,  # "invalid status" - device action locked
}


def _create_api_error(error: Any) -> RoborockException:
    """Create an appropriate exception for a V1 RPC error response.

    Maps known error codes to specific exception types for easier handling
    at higher levels.
    """
    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, int) and (exc_type := _V1_ERROR_CODE_EXCEPTIONS.get(code)):
            return exc_type(error)
    return RoborockException(error)


@dataclass(kw_only=True, frozen=True)
class ResponseMessage:
    """Data structure for v1 RoborockMessage responses."""

    request_id: int | None
    """The request ID of the response."""

    data: ResponseData
    """The data of the response, where the type depends on the command."""

    api_error: RoborockException | None = None
    """The API error message of the response if any."""


def decode_rpc_response(message: RoborockMessage) -> ResponseMessage:
    """Decode a V1 RPC_RESPONSE message.

    This will raise a RoborockException if the message cannot be parsed. A
    response object will be returned even if there is an error in the
    response, as long as we can extract the request ID. This is so we can
    associate an API response with a request even if there was an error.
    """
    if not message.payload:
        return ResponseMessage(request_id=message.seq, data={})
    try:
        payload = json.loads(message.payload.decode())
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
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
    api_error: RoborockException | None = None
    if error := data_point_response.get("error"):
        api_error = _create_api_error(error)

    if (result := data_point_response.get("result")) is None:
        # Some firmware versions return an error-only response (no "result" key).
        # Preserve that error instead of overwriting it with a parsing exception.
        if api_error is None:
            api_error = RoborockException(
                f"Invalid V1 message format: missing 'result' in data point for {message.payload!r}"
            )
        result = {}
    else:
        _LOGGER.debug("Decoded V1 message result: %s", result)
        if isinstance(result, str):
            if result == "unknown_method":
                api_error = RoborockUnsupportedFeature("The method called is not recognized by the device.")
            elif result != "ok":
                api_error = RoborockException(f"Unexpected API Result: {result}")
            result = {}
        if not isinstance(result, dict | list | int):
            # If we already have an API error, prefer returning a response object
            # rather than failing to decode the message entirely.
            if api_error is None:
                raise RoborockException(
                    f"Invalid V1 message format: 'result' was unexpected type {type(result)}. {message.payload!r}"
                )
            result = {}

    if not request_id and api_error:
        raise api_error
    return ResponseMessage(request_id=request_id, data=result, api_error=api_error)


@dataclass
class MapResponse:
    """Data structure for the V1 Map response."""

    request_id: int
    """The request ID of the map response."""

    data: bytes
    """The map data, decrypted and decompressed."""


def create_map_response_decoder(security_data: SecurityData) -> Callable[[RoborockMessage], MapResponse | None]:
    """Create a decoder for V1 map response messages."""

    def _decode_map_response(message: RoborockMessage) -> MapResponse | None:
        """Decode a V1 map response message."""
        if not message.payload or len(message.payload) < 24:
            raise RoborockException("Invalid V1 map response format: missing payload")
        header, body = message.payload[:24], message.payload[24:]
        [endpoint, _, request_id, _] = struct.unpack("<8s8sH6s", header)
        if not endpoint.decode().startswith(security_data.endpoint):
            _LOGGER.debug("Received map response not requested by this device, ignoring.")
            return None
        try:
            decrypted = Utils.decrypt_cbc(body, security_data.nonce)
        except ValueError as err:
            raise RoborockException("Failed to decode map message payload") from err
        decompressed = Utils.decompress(decrypted)
        return MapResponse(request_id=request_id, data=decompressed)

    return _decode_map_response


_T = TypeVar("_T", bound=RoborockBase)


class V1RpcChannel(Protocol):
    """Protocol for V1 RPC channels.

    This is a wrapper around a raw channel that provides a high-level interface
    for sending commands and receiving responses.
    """

    @overload
    async def send_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a command and return a decoded response."""
        ...

    @overload
    async def send_command(
        self,
        method: CommandType,
        *,
        response_type: type[_T],
        params: ParamsType = None,
    ) -> _T:
        """Send a command and return a parsed response RoborockBase type."""
        ...

"""Roborock V1 Protocol Encoder."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.roborock_message import MessageRetry, RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand
from roborock.util import get_next_int

# All mqtt commands are sent securely. Only local commands in this list are secured.
COMMANDS_SECURED = {
    RoborockCommand.GET_MAP_V1,
    RoborockCommand.GET_MULTI_MAP,
}

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


def create_local_payload_encoder(security_data: SecurityData) -> Callable[[CommandType, ParamsType], RoborockMessage]:
    """Create a payload encoder for V1 commands over local connection."""

    def _get_payload(method: CommandType, params: ParamsType) -> RoborockMessage:
        """Build the payload for a V1 command."""
        request = RequestMessage(method=method, params=params)
        is_secured = request.method in COMMANDS_SECURED
        payload = request.as_payload(security_data if is_secured else None)

        message_retry: MessageRetry | None = None
        if method == RoborockCommand.RETRY_REQUEST and isinstance(params, dict):
            message_retry = MessageRetry(method=method, retry_id=params["retry_id"])

        return RoborockMessage(
            timestamp=request.timestamp,
            protocol=RoborockMessageProtocol.GENERAL_REQUEST,
            payload=payload,
            message_retry=message_retry,
        )

    return _get_payload

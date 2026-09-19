"""Roborock B01 Protocol encoding and decoding."""

import json
import logging
from base64 import b64encode
from dataclasses import dataclass
from struct import pack
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    Q10MapPacket,
    Q10TracePacket,
    is_map_packet,
    is_trace_packet,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
ParamsType = list | dict | int | None
_Q10_ZONE_NAME_FIELD_LENGTH = 19


@dataclass(frozen=True)
class CleanParams:
    """Parameters for one rectangular Q10 zone-clean task."""

    first_corner: Q10RoborockPoint
    second_corner: Q10RoborockPoint
    clean_count: int = 1

    @property
    def points(self) -> tuple[Q10RoborockPoint, ...]:
        """Return rectangle vertices sorted into canonical wire order."""
        min_x, max_x = sorted((self.first_corner.x, self.second_corner.x))
        min_y, max_y = sorted((self.first_corner.y, self.second_corner.y))
        return (
            Q10RoborockPoint(min_x, min_y),
            Q10RoborockPoint(max_x, min_y),
            Q10RoborockPoint(max_x, max_y),
            Q10RoborockPoint(min_x, max_y),
        )


def encode_clean_params(params: CleanParams) -> str:
    """Encode Q10 zone-clean parameters for ``dpStartClean`` task type 3."""
    if not isinstance(params, CleanParams):
        raise ValueError("params must be CleanParams")
    if not isinstance(params.first_corner, Q10RoborockPoint) or not isinstance(params.second_corner, Q10RoborockPoint):
        raise ValueError("zone corners must be Q10RoborockPoint values")
    if isinstance(params.clean_count, bool) or not 1 <= params.clean_count <= 3:
        raise ValueError("clean_count must be between 1 and 3")
    if params.first_corner.x == params.second_corner.x or params.first_corner.y == params.second_corner.y:
        raise ValueError("zone corners must enclose an area")

    points = params.points
    payload = bytearray((1, params.clean_count, 1, len(points)))
    for point in points:
        payload.extend(pack(">hh", *point.to_vector()))

    # The app protocol reserves a fixed 19-byte UTF-8 name field per zone. An
    # unnamed zone is encoded as a zero length followed by zero padding.
    payload.append(0)
    payload.extend(bytes(_Q10_ZONE_NAME_FIELD_LENGTH))
    return b64encode(payload).decode()


def encode_mqtt_payload(command: B01_Q10_DP, params: ParamsType) -> RoborockMessage:
    """Encode payload for B01 Q10 commands over MQTT.

    This does not perform any special encoding for the command parameters and expects
    them to already be in a request specific format.
    """
    dps_data = {
        "dps": {
            # Important: some commands use falsy values so only default to `{}` when params is actually None.
            command.code: params if params is not None else {},
        }
    }
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(dps_data).encode("utf-8"),
    )


def _convert_datapoints(datapoints: dict[str, Any], message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Convert the 'dps' dictionary keys from strings to B01_Q10_DP enums."""
    result: dict[B01_Q10_DP, Any] = {}
    for key, value in datapoints.items():
        try:
            code = int(key)
        except ValueError as e:
            raise ValueError(f"dps key is not a valid integer: {e} for {message.payload!r}") from e
        if (dps := B01_Q10_DP.from_code_optional(code)) is not None:
            result[dps] = value
    return result


def decode_rpc_response(message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Decode a B01 Q10 RPC_RESPONSE message.

    This does not perform any special decoding for the response body, but does
    convert the 'dps' keys from strings to B01_Q10_DP enums.
    """
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

    # The COMMON response contains nested datapoints need conversion. To simplify
    # response handling at higher levels we flatten these into the main result.
    if B01_Q10_DP.COMMON in result:
        common_result = result.pop(B01_Q10_DP.COMMON)
        if not isinstance(common_result, dict):
            raise RoborockException(f"Invalid dpCommon format: expected dict, got {type(common_result).__name__}")
        try:
            common_dps_result = _convert_datapoints(common_result, message)
        except ValueError as e:
            raise RoborockException(f"Invalid dpCommon format: {e}") from e
        result.update(common_dps_result)

    return result


@dataclass
class Q10DpsUpdate:
    """A decoded Q10 DPS status update pushed by the device."""

    dps: dict[B01_Q10_DP, Any]
    """Data points keyed by ``B01_Q10_DP`` code."""


# A single decoded message from a Q10 device: a DPS status update, a full map
# packet, or a live cleaning-path (trace) packet. Map/trace packets arrive as
# protocol-301 ``MAP_RESPONSE`` pushes; everything else is a DPS update.
Q10Message = Q10DpsUpdate | Q10MapPacket | Q10TracePacket


def decode_message(message: RoborockMessage) -> Q10Message | None:
    """Decode a pushed Q10 ``RoborockMessage`` into a typed message.

    ``MAP_RESPONSE`` (protocol 301) payloads carry the binary map (``01 01``) or
    trace (``02 01``) packets, which are parsed by the map parser; any other
    ``MAP_RESPONSE`` marker is unrecognized and yields ``None``. Every other
    protocol is treated as a DPS status update.

    Raises ``RoborockException`` if a recognized payload fails to parse.
    """
    if message.protocol == RoborockMessageProtocol.MAP_RESPONSE:
        payload = message.payload or b""
        if is_map_packet(payload):
            return parse_map_packet(payload)
        if is_trace_packet(payload):
            return parse_trace_packet(payload)
        return None
    return Q10DpsUpdate(dps=decode_rpc_response(message))

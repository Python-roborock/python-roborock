"""Roborock B01 Protocol encoding and decoding."""

import base64
import binascii
import json
import logging
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    Q10CleanCount,
    Q10RoomCleanType,
    Q10RoomFanLevel,
    YXCleanLine,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10ReportedRoomCleanSettings, Q10RoomCleanSettings
from roborock.data.code_mappings import RoborockModeEnum
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    Q10MapPacket,
    Q10TracePacket,
    is_trace_packet,
    map_packet_kind,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.map.b01_q10_overlays import Q10RestrictedZone, Q10VirtualWall
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
ParamsType = list | dict | int | None
_Q10_ZONE_RECORD_SIZE = 38
_Q10_ROOM_NAME_FIELD_SIZE = 19
_Q10_CUSTOM_ROOM_COMPACT_SIZE = 6
_Q10_CUSTOM_ROOM_PROPERTIES_SIZE = 26
_Q10_CUSTOM_ROOM_NAME_SIZE = 20

_ModeT = TypeVar("_ModeT", bound=RoborockModeEnum)


def _orientation(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: tuple[int, int], b: tuple[int, int], point: tuple[int, int]) -> bool:
    return min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])


def _segments_cross(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], d: tuple[int, int]) -> bool:
    orientations = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if orientations[0] * orientations[1] < 0 and orientations[2] * orientations[3] < 0:
        return True
    return any(
        orientation == 0 and _on_segment(start, end, point)
        for orientation, start, end, point in (
            (orientations[0], a, b, c),
            (orientations[1], a, b, d),
            (orientations[2], c, d, a),
            (orientations[3], c, d, b),
        )
    )


def _validate_quadrilateral(vertices: list[tuple[int, int]]) -> None:
    area_twice = sum(
        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(vertices, (*vertices[1:], vertices[0]), strict=True)
    )
    if area_twice == 0:
        raise ValueError("restricted-zone vertices must enclose an area")
    if _segments_cross(vertices[0], vertices[1], vertices[2], vertices[3]) or _segments_cross(
        vertices[1], vertices[2], vertices[3], vertices[0]
    ):
        raise ValueError("restricted-zone edges must not cross")


def encode_restricted_zones(zones: Sequence[Q10RestrictedZone]) -> str:
    """Encode the complete Q10 restricted-zone collection."""
    if isinstance(zones, (str, bytes)) or len(zones) > 255:
        raise ValueError("zones must be a sequence of at most 255 restrictions")
    if not zones:
        return base64.b64encode(b"\x01\x00").decode()

    payload = bytearray((1, len(zones)))
    for zone in zones:
        if not isinstance(zone, Q10RestrictedZone):
            raise ValueError("zones must contain Q10RestrictedZone values")
        if isinstance(zone.type, bool) or not isinstance(zone.type, int) or not 0 <= zone.type <= 255:
            raise ValueError("restricted-zone type must be an integer between 0 and 255")
        if len(zone.vertices) != 4:
            raise ValueError("restricted zones must contain exactly four vertices")
        if len(set(zone.vertices)) != 4:
            raise ValueError("restricted-zone vertices must be distinct")
        record = bytearray((zone.type, len(zone.vertices)))
        vector_vertices = [point.to_vector() for point in zone.vertices]
        _validate_quadrilateral(vector_vertices)
        for x, y in vector_vertices:
            record.extend(
                struct.pack(
                    ">hh",
                    x,
                    y,
                )
            )
        record.extend(bytes(_Q10_ZONE_RECORD_SIZE - len(record)))
        payload.extend(record)
    return base64.b64encode(payload).decode()


def encode_virtual_walls(walls: Sequence[Q10VirtualWall]) -> str:
    """Encode the complete Q10 virtual-wall collection."""
    if isinstance(walls, (str, bytes)) or len(walls) > 255:
        raise ValueError("walls must be a sequence of at most 255 virtual walls")

    payload = bytearray((len(walls),))
    for wall in walls:
        if not isinstance(wall, Q10VirtualWall):
            raise ValueError("walls must contain Q10VirtualWall values")
        if wall.start == wall.end:
            raise ValueError("virtual-wall endpoints must be distinct")
        for point in (wall.start, wall.end):
            x, y = point.to_vector()
            payload.extend(
                struct.pack(
                    ">hh",
                    x,
                    y,
                )
            )
    return base64.b64encode(payload).decode()


def encode_room_name(room_id: int, name: str) -> str:
    """Encode a Q10 room-name update."""
    if isinstance(room_id, bool) or not isinstance(room_id, int) or not 0 <= room_id <= 255:
        raise ValueError("room_id must be an integer between 0 and 255")
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("name must be a non-empty string without null bytes")
    encoded_name = name.encode("utf-8")
    if len(encoded_name) > _Q10_ROOM_NAME_FIELD_SIZE:
        raise ValueError("name must be at most 19 UTF-8 bytes")

    payload = bytearray((1, room_id, 0, len(encoded_name)))
    payload.extend(encoded_name)
    payload.extend(bytes(_Q10_ROOM_NAME_FIELD_SIZE - len(encoded_name)))
    return base64.b64encode(payload).decode()


@dataclass(frozen=True)
class Q10RoomCleanUpdate:
    """Decoded Q10 customized-room settings push."""

    settings: tuple[Q10ReportedRoomCleanSettings, ...]
    complete: bool


def _known_mode_or_code(mode_type: type[_ModeT], code: int) -> _ModeT | int:
    mode = mode_type.from_code_optional(code)
    return mode if mode is not None else code


def encode_room_clean_settings(settings: Sequence[Q10RoomCleanSettings]) -> str:
    """Encode the compact six-byte-per-room ``dpCustomerClean`` write."""
    if isinstance(settings, (str, bytes)):
        raise ValueError("settings must contain between 1 and 255 rooms")
    selected = tuple(settings)
    if not selected or len(selected) > 255:
        raise ValueError("settings must contain between 1 and 255 rooms")

    payload = bytearray((len(selected),))
    room_ids: set[int] = set()
    fields = (
        ("fan_level", Q10RoomFanLevel),
        ("water_level", YXWaterLevel),
        ("clean_type", Q10RoomCleanType),
        ("clean_count", Q10CleanCount),
        ("clean_line", YXCleanLine),
    )
    for room in selected:
        if not isinstance(room, Q10RoomCleanSettings):
            raise ValueError("settings must contain Q10RoomCleanSettings values")
        if isinstance(room.room_id, bool) or not isinstance(room.room_id, int) or not 0 <= room.room_id <= 255:
            raise ValueError("room_id must be an integer between 0 and 255")
        if room.room_id in room_ids:
            raise ValueError(f"duplicate room_id: {room.room_id}")
        room_ids.add(room.room_id)
        values = [room.room_id]
        for field_name, mode_type in fields:
            value = getattr(room, field_name)
            if not isinstance(value, mode_type) or value.code < 0:
                raise ValueError(f"{field_name} must be a supported {mode_type.__name__}")
            values.append(value.code)
        payload.extend(values)
    return base64.b64encode(payload).decode()


def decode_room_clean_settings(payload: str) -> Q10RoomCleanUpdate:
    """Decode a compact echo or complete ``dpCustomerClean`` response.

    Complete records contain 26 property bytes, a 20-byte name block, one
    vertex-count byte, then four bytes per vertex. Relevant property offsets
    are room id 0, count 5, type 7, fan 8, water 9, and route 11.
    """
    if not isinstance(payload, str):
        raise RoborockException("Invalid Q10 customized-room payload: expected base64 string")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as ex:
        raise RoborockException("Invalid Q10 customized-room payload: malformed base64") from ex
    if not raw:
        raise RoborockException("Invalid Q10 customized-room payload: empty data")

    count = raw[0]
    if count == 0 and len(raw) == 1:
        return Q10RoomCleanUpdate((), complete=True)
    if len(raw) == 1 + count * _Q10_CUSTOM_ROOM_COMPACT_SIZE:
        offset = 1
        rooms = []
        room_ids: set[int] = set()
        for _ in range(count):
            room_id = raw[offset]
            if room_id in room_ids:
                raise RoborockException("Invalid Q10 customized-room payload: duplicate room id")
            room_ids.add(room_id)
            rooms.append(
                Q10ReportedRoomCleanSettings(
                    room_id=room_id,
                    fan_level=_known_mode_or_code(Q10RoomFanLevel, raw[offset + 1]),
                    water_level=_known_mode_or_code(YXWaterLevel, raw[offset + 2]),
                    clean_type=_known_mode_or_code(Q10RoomCleanType, raw[offset + 3]),
                    clean_count=_known_mode_or_code(Q10CleanCount, raw[offset + 4]),
                    clean_line=_known_mode_or_code(YXCleanLine, raw[offset + 5]),
                )
            )
            offset += _Q10_CUSTOM_ROOM_COMPACT_SIZE
        return Q10RoomCleanUpdate(tuple(rooms), complete=False)

    offset = 1
    rooms = []
    room_ids = set()
    for _ in range(count):
        minimum_end = offset + _Q10_CUSTOM_ROOM_PROPERTIES_SIZE + _Q10_CUSTOM_ROOM_NAME_SIZE + 1
        if minimum_end > len(raw):
            raise RoborockException("Invalid Q10 customized-room payload: truncated room record")
        room_id = int.from_bytes(raw[offset : offset + 2], "big")
        if room_id in room_ids:
            raise RoborockException("Invalid Q10 customized-room payload: duplicate room id")
        room_ids.add(room_id)
        clean_count = int.from_bytes(raw[offset + 5 : offset + 7], "big")
        rooms.append(
            Q10ReportedRoomCleanSettings(
                room_id=room_id,
                fan_level=_known_mode_or_code(Q10RoomFanLevel, raw[offset + 8]),
                water_level=_known_mode_or_code(YXWaterLevel, raw[offset + 9]),
                clean_type=_known_mode_or_code(Q10RoomCleanType, raw[offset + 7]),
                clean_count=_known_mode_or_code(Q10CleanCount, clean_count),
                clean_line=_known_mode_or_code(YXCleanLine, raw[offset + 11]),
            )
        )
        vertex_count = raw[offset + _Q10_CUSTOM_ROOM_PROPERTIES_SIZE + _Q10_CUSTOM_ROOM_NAME_SIZE]
        offset = minimum_end + vertex_count * 4
        if offset > len(raw):
            raise RoborockException("Invalid Q10 customized-room payload: truncated vertices")
    if offset != len(raw):
        raise RoborockException("Invalid Q10 customized-room payload: trailing data")
    return Q10RoomCleanUpdate(tuple(rooms), complete=True)


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

    ``MAP_RESPONSE`` (protocol 301) payloads carry binary current-map (``01
    01``), trace (``02 01``), clean-record detail (``03 01``), or saved-map
    detail (``04 01``) packets. Any other marker is unrecognized and yields
    ``None``. Every other protocol is treated as a DPS status update.

    Raises ``RoborockException`` if a recognized payload fails to parse.
    """
    if message.protocol == RoborockMessageProtocol.MAP_RESPONSE:
        payload = message.payload or b""
        if map_packet_kind(payload) is not None:
            return parse_map_packet(payload)
        if is_trace_packet(payload):
            return parse_trace_packet(payload)
        return None
    return Q10DpsUpdate(dps=decode_rpc_response(message))

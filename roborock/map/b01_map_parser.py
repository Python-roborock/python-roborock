"""Module for parsing B01/Q7 map content.

Observed Q7 `MAP_RESPONSE` payloads follow the mobile app's decode pipeline:
- base64-encoded ASCII
- AES-ECB encrypted with the derived map key
- PKCS7 padded
- ASCII hex for a zlib-compressed SCMap payload

The inner SCMap blob is a protobuf-wire message. We know the app's field layout
well enough to describe the fields we care about declaratively, but we still
avoid shipping generated protobuf classes from a reverse-engineered schema.
That keeps the runtime parser narrow without overstating certainty about the
full message definition.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import struct
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException

from .map_parser import ParsedMapData

_B64_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_MAP_FILE_FORMAT = "PNG"
_WIRE_VARINT = 0
_WIRE_FIXED64 = 1
_WIRE_LEN = 2
_WIRE_FIXED32 = 5


@dataclass(frozen=True)
class _ProtoField:
    """Declarative description of a protobuf-wire field we care about."""

    name: str
    wire_type: int
    repeated: bool = False
    parser: Callable[[object], object] | None = None


@dataclass(frozen=True)
class _ScPoint:
    x: float | None = None
    y: float | None = None


@dataclass(frozen=True)
class _ScMapBoundaryInfo:
    map_md5: str | None = None
    v_min_x: int | None = None
    v_max_x: int | None = None
    v_min_y: int | None = None
    v_max_y: int | None = None


@dataclass(frozen=True)
class _ScMapExtInfo:
    task_begin_date: int | None = None
    map_upload_date: int | None = None
    map_valid: int | None = None
    radian: int | None = None
    force: int | None = None
    clean_path: int | None = None
    boundary_info: _ScMapBoundaryInfo | None = None
    map_version: int | None = None
    map_value_type: int | None = None


@dataclass(frozen=True)
class _ScMapHead:
    map_head_id: int | None = None
    size_x: int | None = None
    size_y: int | None = None
    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None
    resolution: float | None = None


@dataclass(frozen=True)
class _ScRoomData:
    room_id: int | None = None
    room_name: str | None = None
    room_type_id: int | None = None
    material_id: int | None = None
    clean_state: int | None = None
    room_clean: int | None = None
    room_clean_index: int | None = None
    room_name_post: _ScPoint | None = None
    color_id: int | None = None
    floor_direction: int | None = None
    global_seq: int | None = None


@dataclass(frozen=True)
class _ScMapPayload:
    map_type: int | None = None
    map_ext_info: _ScMapExtInfo | None = None
    map_head: _ScMapHead | None = None
    map_data: bytes | None = None
    room_data_info: tuple[_ScRoomData, ...] = field(default_factory=tuple)


@dataclass
class B01MapParserConfig:
    """Configuration for the B01/Q7 map parser."""

    map_scale: int = 4
    """Scale factor for the rendered map image."""


class B01MapParser:
    """Decoder/parser for B01/Q7 SCMap payloads."""

    def __init__(self, config: B01MapParserConfig | None = None) -> None:
        self._config = config or B01MapParserConfig()

    def parse(self, raw_payload: bytes, *, serial: str, model: str) -> ParsedMapData:
        """Parse a raw MAP_RESPONSE payload and return a PNG + MapData."""
        inflated = _decode_b01_map_payload(raw_payload, serial=serial, model=model)
        scmap = _parse_scmap_payload(inflated)
        size_x, size_y, grid = _extract_grid(scmap)
        room_names = _extract_room_names(scmap.room_data_info)

        image = _render_occupancy_image(grid, size_x=size_x, size_y=size_y, scale=self._config.map_scale)

        map_data = MapData()
        map_data.image = ImageData(
            size=size_x * size_y,
            top=0,
            left=0,
            height=size_y,
            width=size_x,
            image_config=ImageConfig(scale=self._config.map_scale),
            data=image,
            img_transformation=lambda p: p,
        )
        if room_names:
            map_data.additional_parameters["room_names"] = room_names

        image_bytes = io.BytesIO()
        image.save(image_bytes, format=_MAP_FILE_FORMAT)

        return ParsedMapData(
            image_content=image_bytes.getvalue(),
            map_data=map_data,
        )


def _derive_map_key(serial: str, model: str) -> bytes:
    """Derive the B01/Q7 map decrypt key from serial + model."""
    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = AES.new(model_key, AES.MODE_ECB).encrypt(pad(material, AES.block_size))
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


def _decode_base64_payload(raw_payload: bytes) -> bytes:
    blob = raw_payload.strip()
    if len(blob) < 32 or any(b not in _B64_CHARS for b in blob):
        raise RoborockException("Failed to decode B01 map payload")

    padded = blob + b"=" * (-len(blob) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except binascii.Error as err:
        raise RoborockException("Failed to decode B01 map payload") from err


def _decode_b01_map_payload(raw_payload: bytes, *, serial: str, model: str) -> bytes:
    """Decode raw B01 `MAP_RESPONSE` payload into inflated SCMap bytes."""
    encrypted_payload = _decode_base64_payload(raw_payload)
    if len(encrypted_payload) % AES.block_size != 0:
        raise RoborockException("Unexpected encrypted B01 map payload length")

    map_key = _derive_map_key(serial, model)
    decrypted_hex = AES.new(map_key, AES.MODE_ECB).decrypt(encrypted_payload)

    try:
        compressed_hex = unpad(decrypted_hex, AES.block_size).decode("ascii")
        compressed_payload = bytes.fromhex(compressed_hex)
        return zlib.decompress(compressed_payload)
    except (ValueError, UnicodeDecodeError, zlib.error) as err:
        raise RoborockException("Failed to decode B01 map payload") from err


def _read_varint(buf: bytes, idx: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if idx >= len(buf):
            raise RoborockException("Truncated varint in B01 map payload")
        byte = buf[idx]
        idx += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, idx
        shift += 7
        if shift > 63:
            raise RoborockException("Invalid varint in B01 map payload")


def _read_fixed32(buf: bytes, idx: int, *, context: str) -> tuple[bytes, int]:
    end = idx + 4
    if end > len(buf):
        raise RoborockException(f"Truncated fixed32 in {context}")
    return buf[idx:end], end


def _read_fixed64(buf: bytes, idx: int, *, context: str) -> tuple[bytes, int]:
    end = idx + 8
    if end > len(buf):
        raise RoborockException(f"Truncated fixed64 in {context}")
    return buf[idx:end], end


def _read_len_delimited(buf: bytes, idx: int) -> tuple[bytes, int]:
    length, idx = _read_varint(buf, idx)
    end = idx + length
    if end > len(buf):
        raise RoborockException("Invalid length-delimited field in B01 map payload")
    return buf[idx:end], end


def _decode_uint32(value: int) -> int:
    return int(value)


def _decode_utf8(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _decode_float32(value: bytes) -> float:
    return struct.unpack("<f", value)[0]


def _decode_map_data_bytes(value: bytes) -> bytes:
    try:
        return zlib.decompress(value)
    except zlib.error:
        return value


def _parse_proto_message(blob: bytes, schema: dict[int, _ProtoField], *, context: str) -> dict[str, object]:
    parsed: dict[str, object] = {}
    idx = 0
    while idx < len(blob):
        key, idx = _read_varint(blob, idx)
        wire = key & 0x07
        field_no = key >> 3

        if wire == _WIRE_VARINT:
            raw_value, idx = _read_varint(blob, idx)
        elif wire == _WIRE_FIXED64:
            raw_value, idx = _read_fixed64(blob, idx, context=context)
        elif wire == _WIRE_LEN:
            raw_value, idx = _read_len_delimited(blob, idx)
        elif wire == _WIRE_FIXED32:
            raw_value, idx = _read_fixed32(blob, idx, context=context)
        else:
            raise RoborockException(f"Unsupported wire type {wire} in {context}")

        if (field_def := schema.get(field_no)) is None:
            continue
        if wire != field_def.wire_type:
            raise RoborockException(f"Unexpected wire type {wire} for field {field_no} in {context}")

        value = field_def.parser(raw_value) if field_def.parser is not None else raw_value
        if field_def.repeated:
            parsed.setdefault(field_def.name, []).append(value)
        else:
            parsed[field_def.name] = value

    return parsed


def _parse_sc_point(blob: bytes) -> _ScPoint:
    parsed = _parse_proto_message(blob, _DEVICE_POINT_INFO_SCHEMA, context="B01 DevicePointInfo")
    return _ScPoint(x=parsed.get("x"), y=parsed.get("y"))


def _parse_sc_map_boundary_info(blob: bytes) -> _ScMapBoundaryInfo:
    parsed = _parse_proto_message(blob, _MAP_BOUNDARY_INFO_SCHEMA, context="B01 MapBoundaryInfo")
    return _ScMapBoundaryInfo(
        map_md5=parsed.get("map_md5"),
        v_min_x=parsed.get("v_min_x"),
        v_max_x=parsed.get("v_max_x"),
        v_min_y=parsed.get("v_min_y"),
        v_max_y=parsed.get("v_max_y"),
    )


def _parse_sc_map_ext_info(blob: bytes) -> _ScMapExtInfo:
    parsed = _parse_proto_message(blob, _MAP_EXT_INFO_SCHEMA, context="B01 MapExtInfo")
    return _ScMapExtInfo(
        task_begin_date=parsed.get("task_begin_date"),
        map_upload_date=parsed.get("map_upload_date"),
        map_valid=parsed.get("map_valid"),
        radian=parsed.get("radian"),
        force=parsed.get("force"),
        clean_path=parsed.get("clean_path"),
        boundary_info=parsed.get("boundary_info"),
        map_version=parsed.get("map_version"),
        map_value_type=parsed.get("map_value_type"),
    )


def _parse_sc_map_head(blob: bytes) -> _ScMapHead:
    parsed = _parse_proto_message(blob, _MAP_HEAD_INFO_SCHEMA, context="B01 MapHeadInfo")
    return _ScMapHead(
        map_head_id=parsed.get("map_head_id"),
        size_x=parsed.get("size_x"),
        size_y=parsed.get("size_y"),
        min_x=parsed.get("min_x"),
        min_y=parsed.get("min_y"),
        max_x=parsed.get("max_x"),
        max_y=parsed.get("max_y"),
        resolution=parsed.get("resolution"),
    )


def _parse_sc_map_data_info(blob: bytes) -> bytes:
    parsed = _parse_proto_message(blob, _MAP_DATA_INFO_SCHEMA, context="B01 MapDataInfo")
    if (map_data := parsed.get("map_data")) is None:
        raise RoborockException("B01 map payload missing mapData")
    return map_data


def _parse_sc_room_data(blob: bytes) -> _ScRoomData:
    parsed = _parse_proto_message(blob, _ROOM_DATA_INFO_SCHEMA, context="B01 RoomDataInfo")
    return _ScRoomData(
        room_id=parsed.get("room_id"),
        room_name=parsed.get("room_name"),
        room_type_id=parsed.get("room_type_id"),
        material_id=parsed.get("material_id"),
        clean_state=parsed.get("clean_state"),
        room_clean=parsed.get("room_clean"),
        room_clean_index=parsed.get("room_clean_index"),
        room_name_post=parsed.get("room_name_post"),
        color_id=parsed.get("color_id"),
        floor_direction=parsed.get("floor_direction"),
        global_seq=parsed.get("global_seq"),
    )


def _parse_scmap_payload(payload: bytes) -> _ScMapPayload:
    """Parse inflated SCMap bytes using the reverse-engineered app field layout."""
    parsed = _parse_proto_message(payload, _ROBOT_MAP_SCHEMA, context="B01 SCMap")
    return _ScMapPayload(
        map_type=parsed.get("map_type"),
        map_ext_info=parsed.get("map_ext_info"),
        map_head=parsed.get("map_head"),
        map_data=parsed.get("map_data"),
        room_data_info=tuple(parsed.get("room_data_info", [])),
    )


def _extract_grid(scmap: _ScMapPayload) -> tuple[int, int, bytes]:
    if scmap.map_head is None or scmap.map_data is None:
        raise RoborockException("Failed to parse B01 map header/grid")

    size_x = scmap.map_head.size_x or 0
    size_y = scmap.map_head.size_y or 0
    if not size_x or not size_y or not scmap.map_data:
        raise RoborockException("Failed to parse B01 map header/grid")

    expected_len = size_x * size_y
    if len(scmap.map_data) < expected_len:
        raise RoborockException("B01 map data shorter than expected dimensions")

    return size_x, size_y, scmap.map_data[:expected_len]


def _extract_room_names(rooms: tuple[_ScRoomData, ...]) -> dict[int, str]:
    room_names: dict[int, str] = {}
    for room in rooms:
        if room.room_id is not None:
            room_names[room.room_id] = room.room_name or f"Room {room.room_id}"
    return room_names


_DEVICE_POINT_INFO_SCHEMA = {
    1: _ProtoField("x", _WIRE_FIXED32, parser=_decode_float32),
    2: _ProtoField("y", _WIRE_FIXED32, parser=_decode_float32),
}

_MAP_BOUNDARY_INFO_SCHEMA = {
    1: _ProtoField("map_md5", _WIRE_LEN, parser=_decode_utf8),
    2: _ProtoField("v_min_x", _WIRE_VARINT, parser=_decode_uint32),
    3: _ProtoField("v_max_x", _WIRE_VARINT, parser=_decode_uint32),
    4: _ProtoField("v_min_y", _WIRE_VARINT, parser=_decode_uint32),
    5: _ProtoField("v_max_y", _WIRE_VARINT, parser=_decode_uint32),
}

_MAP_EXT_INFO_SCHEMA = {
    1: _ProtoField("task_begin_date", _WIRE_VARINT, parser=_decode_uint32),
    2: _ProtoField("map_upload_date", _WIRE_VARINT, parser=_decode_uint32),
    3: _ProtoField("map_valid", _WIRE_VARINT, parser=_decode_uint32),
    4: _ProtoField("radian", _WIRE_VARINT, parser=_decode_uint32),
    5: _ProtoField("force", _WIRE_VARINT, parser=_decode_uint32),
    6: _ProtoField("clean_path", _WIRE_VARINT, parser=_decode_uint32),
    7: _ProtoField("boundary_info", _WIRE_LEN, parser=_parse_sc_map_boundary_info),
    8: _ProtoField("map_version", _WIRE_VARINT, parser=_decode_uint32),
    9: _ProtoField("map_value_type", _WIRE_VARINT, parser=_decode_uint32),
}

_MAP_HEAD_INFO_SCHEMA = {
    1: _ProtoField("map_head_id", _WIRE_VARINT, parser=_decode_uint32),
    2: _ProtoField("size_x", _WIRE_VARINT, parser=_decode_uint32),
    3: _ProtoField("size_y", _WIRE_VARINT, parser=_decode_uint32),
    4: _ProtoField("min_x", _WIRE_FIXED32, parser=_decode_float32),
    5: _ProtoField("min_y", _WIRE_FIXED32, parser=_decode_float32),
    6: _ProtoField("max_x", _WIRE_FIXED32, parser=_decode_float32),
    7: _ProtoField("max_y", _WIRE_FIXED32, parser=_decode_float32),
    8: _ProtoField("resolution", _WIRE_FIXED32, parser=_decode_float32),
}

_MAP_DATA_INFO_SCHEMA = {
    1: _ProtoField("map_data", _WIRE_LEN, parser=_decode_map_data_bytes),
}

_ROOM_DATA_INFO_SCHEMA = {
    1: _ProtoField("room_id", _WIRE_VARINT, parser=_decode_uint32),
    2: _ProtoField("room_name", _WIRE_LEN, parser=_decode_utf8),
    3: _ProtoField("room_type_id", _WIRE_VARINT, parser=_decode_uint32),
    4: _ProtoField("material_id", _WIRE_VARINT, parser=_decode_uint32),
    5: _ProtoField("clean_state", _WIRE_VARINT, parser=_decode_uint32),
    6: _ProtoField("room_clean", _WIRE_VARINT, parser=_decode_uint32),
    7: _ProtoField("room_clean_index", _WIRE_VARINT, parser=_decode_uint32),
    8: _ProtoField("room_name_post", _WIRE_LEN, parser=_parse_sc_point),
    10: _ProtoField("color_id", _WIRE_VARINT, parser=_decode_uint32),
    11: _ProtoField("floor_direction", _WIRE_VARINT, parser=_decode_uint32),
    12: _ProtoField("global_seq", _WIRE_VARINT, parser=_decode_uint32),
}

_ROBOT_MAP_SCHEMA = {
    1: _ProtoField("map_type", _WIRE_VARINT, parser=_decode_uint32),
    2: _ProtoField("map_ext_info", _WIRE_LEN, parser=_parse_sc_map_ext_info),
    3: _ProtoField("map_head", _WIRE_LEN, parser=_parse_sc_map_head),
    4: _ProtoField("map_data", _WIRE_LEN, parser=_parse_sc_map_data_info),
    12: _ProtoField("room_data_info", _WIRE_LEN, repeated=True, parser=_parse_sc_room_data),
}


def _render_occupancy_image(grid: bytes, *, size_x: int, size_y: int, scale: int) -> Image.Image:
    """Render the B01 occupancy grid into a simple image."""

    # The observed occupancy grid contains only:
    # - 0: outside/unknown
    # - 127: wall/obstacle
    # - 128: floor/free
    table = bytearray(range(256))
    table[0] = 0
    table[127] = 180
    table[128] = 255

    mapped = grid.translate(bytes(table))
    img = Image.frombytes("L", (size_x, size_y), mapped)
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert("RGB")

    if scale > 1:
        img = img.resize((size_x * scale, size_y * scale), resample=Image.Resampling.NEAREST)

    return img

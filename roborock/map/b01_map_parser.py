"""Module for parsing B01/Q7 map content.

Observed Q7 `MAP_RESPONSE` payloads follow this decode pipeline:
- base64-encoded ASCII
- AES-ECB encrypted with the derived map key
- PKCS7 padded
- ASCII hex for a zlib-compressed SCMap payload

The inner SCMap blob is parsed with the official protobuf runtime using a small
runtime descriptor for the message fields this parser needs.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import zlib
from dataclasses import dataclass, field
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from google.protobuf import descriptor_pool
from google.protobuf.descriptor_pb2 import DescriptorProto, FieldDescriptorProto, FileDescriptorProto
from google.protobuf.message import DecodeError, Message
from google.protobuf.message_factory import GetMessageClass
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException

from .map_parser import ParsedMapData

_B64_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_MAP_FILE_FORMAT = "PNG"
_PROTO_PACKAGE = "b01.scmap"


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


def _message_descriptor(name: str, fields: list[dict[str, object]]) -> DescriptorProto:
    descriptor = DescriptorProto(name=name)
    for field_def in fields:
        descriptor.field.add(
            name=field_def["name"],
            number=field_def["number"],
            label=field_def.get("label", FieldDescriptorProto.LABEL_OPTIONAL),
            type=field_def["type"],
            type_name=field_def.get("type_name"),
        )
    return descriptor


_FILE_DESCRIPTOR = FileDescriptorProto(name="b01_scmap.proto", package=_PROTO_PACKAGE, syntax="proto2")
_FILE_DESCRIPTOR.message_type.extend(
    [
        _message_descriptor(
            "DevicePointInfo",
            [
                {"name": "x", "number": 1, "type": FieldDescriptorProto.TYPE_FLOAT},
                {"name": "y", "number": 2, "type": FieldDescriptorProto.TYPE_FLOAT},
            ],
        ),
        _message_descriptor(
            "MapBoundaryInfo",
            [
                {"name": "mapMd5", "number": 1, "type": FieldDescriptorProto.TYPE_STRING},
                {"name": "vMinX", "number": 2, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "vMaxX", "number": 3, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "vMinY", "number": 4, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "vMaxY", "number": 5, "type": FieldDescriptorProto.TYPE_UINT32},
            ],
        ),
        _message_descriptor(
            "MapExtInfo",
            [
                {"name": "taskBeginDate", "number": 1, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "mapUploadDate", "number": 2, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "mapValid", "number": 3, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "radian", "number": 4, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "force", "number": 5, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "cleanPath", "number": 6, "type": FieldDescriptorProto.TYPE_UINT32},
                {
                    "name": "boudaryInfo",
                    "number": 7,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.MapBoundaryInfo",
                },
                {"name": "mapVersion", "number": 8, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "mapValueType", "number": 9, "type": FieldDescriptorProto.TYPE_UINT32},
            ],
        ),
        _message_descriptor(
            "MapHeadInfo",
            [
                {"name": "mapHeadId", "number": 1, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "sizeX", "number": 2, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "sizeY", "number": 3, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "minX", "number": 4, "type": FieldDescriptorProto.TYPE_FLOAT},
                {"name": "minY", "number": 5, "type": FieldDescriptorProto.TYPE_FLOAT},
                {"name": "maxX", "number": 6, "type": FieldDescriptorProto.TYPE_FLOAT},
                {"name": "maxY", "number": 7, "type": FieldDescriptorProto.TYPE_FLOAT},
                {"name": "resolution", "number": 8, "type": FieldDescriptorProto.TYPE_FLOAT},
            ],
        ),
        _message_descriptor(
            "MapDataInfo",
            [{"name": "mapData", "number": 1, "type": FieldDescriptorProto.TYPE_BYTES}],
        ),
        _message_descriptor(
            "RoomDataInfo",
            [
                {"name": "roomId", "number": 1, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "roomName", "number": 2, "type": FieldDescriptorProto.TYPE_STRING},
                {"name": "roomTypeId", "number": 3, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "meterialId", "number": 4, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "cleanState", "number": 5, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "roomClean", "number": 6, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "roomCleanIndex", "number": 7, "type": FieldDescriptorProto.TYPE_UINT32},
                {
                    "name": "roomNamePost",
                    "number": 8,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.DevicePointInfo",
                },
                {"name": "colorId", "number": 10, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "floor_direction", "number": 11, "type": FieldDescriptorProto.TYPE_UINT32},
                {"name": "global_seq", "number": 12, "type": FieldDescriptorProto.TYPE_UINT32},
            ],
        ),
        _message_descriptor(
            "RobotMap",
            [
                {"name": "mapType", "number": 1, "type": FieldDescriptorProto.TYPE_UINT32},
                {
                    "name": "mapExtInfo",
                    "number": 2,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.MapExtInfo",
                },
                {
                    "name": "mapHead",
                    "number": 3,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.MapHeadInfo",
                },
                {
                    "name": "mapData",
                    "number": 4,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.MapDataInfo",
                },
                {
                    "name": "roomDataInfo",
                    "number": 12,
                    "label": FieldDescriptorProto.LABEL_REPEATED,
                    "type": FieldDescriptorProto.TYPE_MESSAGE,
                    "type_name": f".{_PROTO_PACKAGE}.RoomDataInfo",
                },
            ],
        ),
    ]
)

_SC_MAP_FILE_DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(_FILE_DESCRIPTOR.SerializeToString())
_DEVICE_POINT_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["DevicePointInfo"])
_MAP_BOUNDARY_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["MapBoundaryInfo"])
_MAP_EXT_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["MapExtInfo"])
_MAP_HEAD_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["MapHeadInfo"])
_MAP_DATA_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["MapDataInfo"])
_ROOM_DATA_INFO = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["RoomDataInfo"])
_ROBOT_MAP = GetMessageClass(_SC_MAP_FILE_DESCRIPTOR.message_types_by_name["RobotMap"])


def _has_field(message: Any, field_name: str) -> bool:
    return message.HasField(field_name)


def _parse_proto(blob: bytes, message_class: type[Message], *, context: str) -> Any:
    message = message_class()
    try:
        message.ParseFromString(blob)
    except DecodeError as err:
        raise RoborockException(f"Failed to parse {context}") from err
    return message


def _decode_map_data_bytes(value: bytes) -> bytes:
    try:
        return zlib.decompress(value)
    except zlib.error:
        return value


def _parse_sc_point(blob: bytes) -> _ScPoint:
    parsed = _parse_proto(blob, _DEVICE_POINT_INFO, context="B01 DevicePointInfo")
    return _ScPoint(
        x=parsed.x if _has_field(parsed, "x") else None,
        y=parsed.y if _has_field(parsed, "y") else None,
    )


def _parse_sc_map_boundary_info(blob: bytes) -> _ScMapBoundaryInfo:
    parsed = _parse_proto(blob, _MAP_BOUNDARY_INFO, context="B01 MapBoundaryInfo")
    return _ScMapBoundaryInfo(
        map_md5=parsed.mapMd5 if _has_field(parsed, "mapMd5") else None,
        v_min_x=parsed.vMinX if _has_field(parsed, "vMinX") else None,
        v_max_x=parsed.vMaxX if _has_field(parsed, "vMaxX") else None,
        v_min_y=parsed.vMinY if _has_field(parsed, "vMinY") else None,
        v_max_y=parsed.vMaxY if _has_field(parsed, "vMaxY") else None,
    )


def _parse_sc_map_ext_info(blob: bytes) -> _ScMapExtInfo:
    parsed = _parse_proto(blob, _MAP_EXT_INFO, context="B01 MapExtInfo")
    return _ScMapExtInfo(
        task_begin_date=parsed.taskBeginDate if _has_field(parsed, "taskBeginDate") else None,
        map_upload_date=parsed.mapUploadDate if _has_field(parsed, "mapUploadDate") else None,
        map_valid=parsed.mapValid if _has_field(parsed, "mapValid") else None,
        radian=parsed.radian if _has_field(parsed, "radian") else None,
        force=parsed.force if _has_field(parsed, "force") else None,
        clean_path=parsed.cleanPath if _has_field(parsed, "cleanPath") else None,
        boundary_info=(
            _parse_sc_map_boundary_info(parsed.boudaryInfo.SerializeToString())
            if _has_field(parsed, "boudaryInfo")
            else None
        ),
        map_version=parsed.mapVersion if _has_field(parsed, "mapVersion") else None,
        map_value_type=parsed.mapValueType if _has_field(parsed, "mapValueType") else None,
    )


def _parse_sc_map_head(blob: bytes) -> _ScMapHead:
    parsed = _parse_proto(blob, _MAP_HEAD_INFO, context="B01 MapHeadInfo")
    return _ScMapHead(
        map_head_id=parsed.mapHeadId if _has_field(parsed, "mapHeadId") else None,
        size_x=parsed.sizeX if _has_field(parsed, "sizeX") else None,
        size_y=parsed.sizeY if _has_field(parsed, "sizeY") else None,
        min_x=parsed.minX if _has_field(parsed, "minX") else None,
        min_y=parsed.minY if _has_field(parsed, "minY") else None,
        max_x=parsed.maxX if _has_field(parsed, "maxX") else None,
        max_y=parsed.maxY if _has_field(parsed, "maxY") else None,
        resolution=parsed.resolution if _has_field(parsed, "resolution") else None,
    )


def _parse_sc_map_data_info(blob: bytes) -> bytes:
    parsed = _parse_proto(blob, _MAP_DATA_INFO, context="B01 MapDataInfo")
    if not _has_field(parsed, "mapData"):
        raise RoborockException("B01 map payload missing mapData")
    return _decode_map_data_bytes(parsed.mapData)


def _parse_sc_room_data(blob: bytes) -> _ScRoomData:
    parsed = _parse_proto(blob, _ROOM_DATA_INFO, context="B01 RoomDataInfo")
    return _ScRoomData(
        room_id=parsed.roomId if _has_field(parsed, "roomId") else None,
        room_name=parsed.roomName if _has_field(parsed, "roomName") else None,
        room_type_id=parsed.roomTypeId if _has_field(parsed, "roomTypeId") else None,
        material_id=parsed.meterialId if _has_field(parsed, "meterialId") else None,
        clean_state=parsed.cleanState if _has_field(parsed, "cleanState") else None,
        room_clean=parsed.roomClean if _has_field(parsed, "roomClean") else None,
        room_clean_index=parsed.roomCleanIndex if _has_field(parsed, "roomCleanIndex") else None,
        room_name_post=(
            _parse_sc_point(parsed.roomNamePost.SerializeToString()) if _has_field(parsed, "roomNamePost") else None
        ),
        color_id=parsed.colorId if _has_field(parsed, "colorId") else None,
        floor_direction=parsed.floor_direction if _has_field(parsed, "floor_direction") else None,
        global_seq=parsed.global_seq if _has_field(parsed, "global_seq") else None,
    )


def _parse_scmap_payload(payload: bytes) -> _ScMapPayload:
    """Parse inflated SCMap bytes into typed map metadata."""
    parsed = _parse_proto(payload, _ROBOT_MAP, context="B01 SCMap")
    return _ScMapPayload(
        map_type=parsed.mapType if _has_field(parsed, "mapType") else None,
        map_ext_info=(
            _parse_sc_map_ext_info(parsed.mapExtInfo.SerializeToString()) if _has_field(parsed, "mapExtInfo") else None
        ),
        map_head=_parse_sc_map_head(parsed.mapHead.SerializeToString()) if _has_field(parsed, "mapHead") else None,
        map_data=_parse_sc_map_data_info(parsed.mapData.SerializeToString()) if _has_field(parsed, "mapData") else None,
        room_data_info=tuple(_parse_sc_room_data(room.SerializeToString()) for room in parsed.roomDataInfo),
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
    # Expose room id/name mapping without inventing room geometry/polygons.
    room_names: dict[int, str] = {}
    for room in rooms:
        if room.room_id is not None:
            room_names[room.room_id] = room.room_name or f"Room {room.room_id}"
    return room_names


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

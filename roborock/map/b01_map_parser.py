"""Module for parsing B01/Q7 map content.

Observed Q7 `MAP_RESPONSE` payloads follow this decode pipeline:
- base64-encoded ASCII
- AES-ECB encrypted with the derived map key
- PKCS7 padded
- ASCII hex for a zlib-compressed SCMap payload

The inner SCMap blob is parsed with protobuf messages generated from
`roborock/map/proto/b01_scmap.proto`.
"""

import base64
import binascii
import hashlib
import io
import zlib
from dataclasses import dataclass, field

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from google.protobuf.message import DecodeError, Message
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException
from roborock.map.proto.b01_scmap_pb2 import (  # type: ignore[attr-defined]
    DevicePointInfo,
    MapBoundaryInfo,
    MapExtInfo,
    MapHeadInfo,
    RobotMap,
    RoomDataInfo,
)

from .map_parser import ParsedMapData

_B64_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_MAP_FILE_FORMAT = "PNG"


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


def _parse_proto(blob: bytes, message: Message, *, context: str) -> None:
    try:
        message.ParseFromString(blob)
    except DecodeError as err:
        raise RoborockException(f"Failed to parse {context}") from err


def _decode_map_data_bytes(value: bytes) -> bytes:
    try:
        return zlib.decompress(value)
    except zlib.error:
        return value


def _parse_sc_point(parsed: DevicePointInfo) -> _ScPoint:
    return _ScPoint(
        x=parsed.x if parsed.HasField("x") else None,
        y=parsed.y if parsed.HasField("y") else None,
    )


def _parse_sc_map_boundary_info(parsed: MapBoundaryInfo) -> _ScMapBoundaryInfo:
    return _ScMapBoundaryInfo(
        map_md5=parsed.mapMd5 if parsed.HasField("mapMd5") else None,
        v_min_x=parsed.vMinX if parsed.HasField("vMinX") else None,
        v_max_x=parsed.vMaxX if parsed.HasField("vMaxX") else None,
        v_min_y=parsed.vMinY if parsed.HasField("vMinY") else None,
        v_max_y=parsed.vMaxY if parsed.HasField("vMaxY") else None,
    )


def _parse_sc_map_ext_info(parsed: MapExtInfo) -> _ScMapExtInfo:
    return _ScMapExtInfo(
        task_begin_date=parsed.taskBeginDate if parsed.HasField("taskBeginDate") else None,
        map_upload_date=parsed.mapUploadDate if parsed.HasField("mapUploadDate") else None,
        map_valid=parsed.mapValid if parsed.HasField("mapValid") else None,
        radian=parsed.radian if parsed.HasField("radian") else None,
        force=parsed.force if parsed.HasField("force") else None,
        clean_path=parsed.cleanPath if parsed.HasField("cleanPath") else None,
        boundary_info=_parse_sc_map_boundary_info(parsed.boudaryInfo) if parsed.HasField("boudaryInfo") else None,
        map_version=parsed.mapVersion if parsed.HasField("mapVersion") else None,
        map_value_type=parsed.mapValueType if parsed.HasField("mapValueType") else None,
    )


def _parse_sc_map_head(parsed: MapHeadInfo) -> _ScMapHead:
    return _ScMapHead(
        map_head_id=parsed.mapHeadId if parsed.HasField("mapHeadId") else None,
        size_x=parsed.sizeX if parsed.HasField("sizeX") else None,
        size_y=parsed.sizeY if parsed.HasField("sizeY") else None,
        min_x=parsed.minX if parsed.HasField("minX") else None,
        min_y=parsed.minY if parsed.HasField("minY") else None,
        max_x=parsed.maxX if parsed.HasField("maxX") else None,
        max_y=parsed.maxY if parsed.HasField("maxY") else None,
        resolution=parsed.resolution if parsed.HasField("resolution") else None,
    )


def _parse_sc_room_data(parsed: RoomDataInfo) -> _ScRoomData:
    return _ScRoomData(
        room_id=parsed.roomId if parsed.HasField("roomId") else None,
        room_name=parsed.roomName if parsed.HasField("roomName") else None,
        room_type_id=parsed.roomTypeId if parsed.HasField("roomTypeId") else None,
        material_id=parsed.meterialId if parsed.HasField("meterialId") else None,
        clean_state=parsed.cleanState if parsed.HasField("cleanState") else None,
        room_clean=parsed.roomClean if parsed.HasField("roomClean") else None,
        room_clean_index=parsed.roomCleanIndex if parsed.HasField("roomCleanIndex") else None,
        room_name_post=_parse_sc_point(parsed.roomNamePost) if parsed.HasField("roomNamePost") else None,
        color_id=parsed.colorId if parsed.HasField("colorId") else None,
        floor_direction=parsed.floor_direction if parsed.HasField("floor_direction") else None,
        global_seq=parsed.global_seq if parsed.HasField("global_seq") else None,
    )


def _parse_scmap_payload(payload: bytes) -> _ScMapPayload:
    """Parse inflated SCMap bytes into typed map metadata."""
    parsed = RobotMap()
    _parse_proto(payload, parsed, context="B01 SCMap")

    map_data = None
    if parsed.HasField("mapData"):
        if not parsed.mapData.HasField("mapData"):
            raise RoborockException("B01 map payload missing mapData")
        map_data = _decode_map_data_bytes(parsed.mapData.mapData)

    return _ScMapPayload(
        map_type=parsed.mapType if parsed.HasField("mapType") else None,
        map_ext_info=_parse_sc_map_ext_info(parsed.mapExtInfo) if parsed.HasField("mapExtInfo") else None,
        map_head=_parse_sc_map_head(parsed.mapHead) if parsed.HasField("mapHead") else None,
        map_data=map_data,
        room_data_info=tuple(_parse_sc_room_data(room) for room in parsed.roomDataInfo),
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

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
from dataclasses import dataclass

from Crypto.Cipher import AES
from google.protobuf.message import DecodeError, Message
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException
from roborock.map.proto.b01_scmap_pb2 import RobotMap  # type: ignore[attr-defined]
from roborock.protocol import Utils

from .map_parser import ParsedMapData

_MAP_FILE_FORMAT = "PNG"


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
        parsed = _parse_scmap_payload(inflated)
        size_x, size_y, grid = _extract_grid(parsed)
        room_names = _extract_room_names(parsed)

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
    encrypted = Utils.encrypt_ecb(material, model_key)
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


def _decode_base64_payload(raw_payload: bytes) -> bytes:
    blob = raw_payload.strip()
    padded = blob + b"=" * (-len(blob) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except binascii.Error as err:
        raise RoborockException("Failed to decode B01 map payload") from err


def _decode_b01_map_payload(raw_payload: bytes, *, serial: str, model: str) -> bytes:
    """Decode raw B01 `MAP_RESPONSE` payload into inflated SCMap bytes."""
    # TODO: Move this lower-level B01 transport decode under `roborock.protocols`
    # so this module only handles SCMap parsing/rendering.
    encrypted_payload = _decode_base64_payload(raw_payload)
    if len(encrypted_payload) % AES.block_size != 0:
        raise RoborockException("Unexpected encrypted B01 map payload length")

    map_key = _derive_map_key(serial, model)

    try:
        compressed_hex = Utils.decrypt_ecb(encrypted_payload, map_key).decode("ascii")
        compressed_payload = bytes.fromhex(compressed_hex)
        return zlib.decompress(compressed_payload)
    except (ValueError, UnicodeDecodeError, zlib.error) as err:
        raise RoborockException("Failed to decode B01 map payload") from err


def _parse_proto(blob: bytes, message: Message, *, context: str) -> None:
    try:
        message.ParseFromString(blob)
    except DecodeError as err:
        raise RoborockException(f"Failed to parse {context}") from err


def _parse_scmap_payload(payload: bytes) -> RobotMap:
    """Parse inflated SCMap bytes into a generated protobuf message."""
    parsed = RobotMap()
    _parse_proto(payload, parsed, context="B01 SCMap")
    return parsed


def _extract_grid(parsed: RobotMap) -> tuple[int, int, bytes]:
    if not parsed.HasField("mapHead") or not parsed.HasField("mapData"):
        raise RoborockException("Failed to parse B01 map header/grid")

    size_x = parsed.mapHead.sizeX if parsed.mapHead.HasField("sizeX") else 0
    size_y = parsed.mapHead.sizeY if parsed.mapHead.HasField("sizeY") else 0
    if not size_x or not size_y or not parsed.mapData.HasField("mapData"):
        raise RoborockException("Failed to parse B01 map header/grid")

    map_data = parsed.mapData.mapData
    expected_len = size_x * size_y
    if len(map_data) < expected_len:
        raise RoborockException("B01 map data shorter than expected dimensions")

    return size_x, size_y, map_data[:expected_len]


def _extract_room_names(parsed: RobotMap) -> dict[int, str]:
    # Expose room id/name mapping without inventing room geometry/polygons.
    room_names: dict[int, str] = {}
    for room in parsed.roomDataInfo:
        if room.HasField("roomId"):
            room_id = room.roomId
            room_names[room_id] = room.roomName if room.HasField("roomName") else f"Room {room_id}"
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

"""Module for parsing B01/Q7 map content.

Observed Q7 MAP_RESPONSE payloads are:
- base64-encoded ASCII
- AES-ECB encrypted with the derived map key
- PKCS7 padded
- ASCII hex for a zlib-compressed SCMap payload

The inner SCMap blob appears to use protobuf wire encoding, but we do not have
an upstream `.proto` schema for it. We intentionally keep a tiny schema-free
wire parser here instead of introducing generated protobuf classes from a
reverse-engineered schema, because that would add maintenance/guesswork without
meaningfully reducing complexity for the small set of fields we actually use.

This module keeps the decode path narrow and explicit to match the observed
payload shape as closely as possible.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import zlib
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException

from .map_parser import ParsedMapData

_B64_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
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
        size_x, size_y, grid, room_names = _parse_scmap_payload(inflated)

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
    """Decode raw B01 MAP_RESPONSE payload into inflated SCMap bytes."""
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


def _read_len_delimited(buf: bytes, idx: int) -> tuple[bytes, int]:
    length, idx = _read_varint(buf, idx)
    end = idx + length
    if end > len(buf):
        raise RoborockException("Invalid length-delimited field in B01 map payload")
    return buf[idx:end], end


def _parse_map_data_info(blob: bytes) -> bytes:
    """Extract and inflate occupancy raster bytes from SCMap mapDataInfo."""
    idx = 0
    while idx < len(blob):
        key, idx = _read_varint(blob, idx)
        field_no = key >> 3
        wire = key & 0x07
        if wire == 0:
            _, idx = _read_varint(blob, idx)
        elif wire == 2:
            value, idx = _read_len_delimited(blob, idx)
            if field_no == 1:
                try:
                    return zlib.decompress(value)
                except zlib.error:
                    return value
        elif wire == 5:
            idx += 4
        else:
            raise RoborockException(f"Unsupported wire type {wire} in B01 mapDataInfo")
    raise RoborockException("B01 map payload missing mapData")


def _parse_room_data_info(blob: bytes) -> tuple[int | None, str | None]:
    room_id: int | None = None
    room_name: str | None = None

    idx = 0
    while idx < len(blob):
        key, idx = _read_varint(blob, idx)
        field_no = key >> 3
        wire = key & 0x07
        if wire == 0:
            int_value, idx = _read_varint(blob, idx)
            if field_no == 1:
                room_id = int(int_value)
        elif wire == 2:
            bytes_value, idx = _read_len_delimited(blob, idx)
            if field_no == 2:
                room_name = bytes_value.decode("utf-8", errors="replace")
        elif wire == 5:
            idx += 4
        else:
            raise RoborockException(f"Unsupported wire type {wire} in B01 roomDataInfo")

    return room_id, room_name


def _parse_scmap_payload(payload: bytes) -> tuple[int, int, bytes, dict[int, str]]:
    """Parse inflated SCMap bytes."""

    size_x = 0
    size_y = 0
    grid = b""
    room_names: dict[int, str] = {}

    idx = 0
    while idx < len(payload):
        key, idx = _read_varint(payload, idx)
        field_no = key >> 3
        wire = key & 0x07

        if wire == 0:
            _, idx = _read_varint(payload, idx)
            continue

        if wire != 2:
            if wire == 5:
                idx += 4
                continue
            raise RoborockException(f"Unsupported wire type {wire} in B01 map payload")

        value, idx = _read_len_delimited(payload, idx)

        if field_no == 3:  # mapHead
            hidx = 0
            while hidx < len(value):
                hkey, hidx = _read_varint(value, hidx)
                hfield = hkey >> 3
                hwire = hkey & 0x07
                if hwire == 0:
                    hvalue, hidx = _read_varint(value, hidx)
                    if hfield == 2:
                        size_x = int(hvalue)
                    elif hfield == 3:
                        size_y = int(hvalue)
                elif hwire == 5:
                    hidx += 4
                elif hwire == 2:
                    _, hidx = _read_len_delimited(value, hidx)
                else:
                    raise RoborockException(f"Unsupported wire type {hwire} in B01 map header")
        elif field_no == 4:  # mapDataInfo
            grid = _parse_map_data_info(value)
        elif field_no == 12:  # roomDataInfo (repeated)
            room_id, room_name = _parse_room_data_info(value)
            if room_id is not None:
                room_names[room_id] = room_name or f"Room {room_id}"

    if not size_x or not size_y or not grid:
        raise RoborockException("Failed to parse B01 map header/grid")

    expected_len = size_x * size_y
    if len(grid) < expected_len:
        raise RoborockException("B01 map data shorter than expected dimensions")

    return size_x, size_y, grid[:expected_len], room_names


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

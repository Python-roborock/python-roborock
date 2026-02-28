"""B01/Q7 SCMap decoding and rendering support."""

from __future__ import annotations

import base64
import hashlib
import io
import math
import zlib
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image

from roborock.exceptions import RoborockException

_B01_HASH = "5wwh9ikChRjASpMU8cxg7o1d2E"


@dataclass
class B01MapData:
    """Parsed B01 map payload."""

    size_x: int
    size_y: int
    map_data: bytes


def _read_varint(buf: bytes, idx: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if idx >= len(buf):
            raise RoborockException("Truncated varint in B01 map payload")
        b = buf[idx]
        idx += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
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
            raise RoborockException(f"Unsupported wire type {wire} in B01 map data info")
    raise RoborockException("B01 map payload missing mapData")


def parse_scmap_payload(payload: bytes) -> B01MapData:
    """Parse SCMap protobuf payload and extract occupancy grid bytes."""

    size_x = 0
    size_y = 0
    grid = b""
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

    if not size_x or not size_y or not grid:
        raise RoborockException("Failed to parse B01 map header/grid")
    if len(grid) < size_x * size_y:
        raise RoborockException("B01 map data shorter than expected dimensions")
    return B01MapData(size_x=size_x, size_y=size_y, map_data=grid)


def _derive_b01_iv(iv_seed: int) -> bytes:
    random_hex = iv_seed.to_bytes(4, "big").hex().lower()
    md5 = hashlib.md5((random_hex + _B01_HASH).encode(), usedforsecurity=False).hexdigest()
    return md5[9:25].encode()


def derive_map_key(serial: str, model: str) -> bytes:
    """Derive map decrypt key for B01/Q7 map payloads."""

    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = AES.new(model_key, AES.MODE_ECB).encrypt(pad(material, AES.block_size))
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


def _maybe_b64(data: bytes) -> bytes | None:
    try:
        return base64.b64decode(data, validate=False)
    except Exception:
        return None


def decode_b01_map_payload(raw_payload: bytes, *, local_key: str, serial: str, model: str) -> bytes:
    """Decode raw B01 MAP_RESPONSE payload into inflated SCMap protobuf bytes."""

    layers: list[bytes] = []
    l0 = _maybe_b64(raw_payload)
    if l0 is not None:
        layers.append(l0)
        l1 = _maybe_b64(l0)
        if l1 is not None:
            layers.append(l1)
    else:
        layers.append(raw_payload)

    map_key = derive_map_key(serial, model)
    for layer in layers:
        candidates: list[bytes] = [layer]
        if len(layer) > 19 and layer[:3] == b"B01":
            iv_seed = int.from_bytes(layer[7:11], "big")
            payload_len = int.from_bytes(layer[17:19], "big")
            encrypted = layer[19 : 19 + payload_len]
            try:
                decrypted = AES.new(local_key.encode(), AES.MODE_CBC, _derive_b01_iv(iv_seed)).decrypt(encrypted)
                candidates.append(unpad(decrypted, 16))
            except Exception:
                pass

        for candidate in list(candidates):
            if len(candidate) % 16 == 0:
                try:
                    decrypted = AES.new(map_key, AES.MODE_ECB).decrypt(candidate)
                    candidates.append(decrypted)
                    candidates.append(unpad(decrypted, 16))
                except Exception:
                    pass

        for candidate in candidates:
            variants = [candidate]
            try:
                text = candidate.decode("ascii").strip()
                if len(text) > 16 and all(c in "0123456789abcdefABCDEF" for c in text[:32]):
                    variants.append(bytes.fromhex(text))
            except Exception:
                pass
            for variant in variants:
                try:
                    inflated = zlib.decompress(variant)
                except zlib.error:
                    continue
                parse_scmap_payload(inflated)
                return inflated

    raise RoborockException("Failed to decode B01 map payload")


def render_map_png(map_data: B01MapData) -> bytes:
    """Render occupancy map bytes into PNG."""

    img = Image.new("RGB", (map_data.size_x, map_data.size_y), (0, 0, 0))
    px = img.load()
    room_colors = [
        (80, 150, 255),
        (255, 170, 80),
        (120, 220, 130),
        (210, 130, 255),
        (255, 120, 170),
        (100, 220, 220),
    ]

    for i, value in enumerate(map_data.map_data[: map_data.size_x * map_data.size_y]):
        x = i % map_data.size_x
        y = map_data.size_y - 1 - (i // map_data.size_x)
        if value == 0:
            color = (0, 0, 0)
        elif value in (1, 127):
            color = (180, 180, 180)
        elif value >= 128:
            color = (255, 255, 255)
        else:
            color = room_colors[(max(value - 2, 0)) % len(room_colors)]
        px[x, y] = color

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()

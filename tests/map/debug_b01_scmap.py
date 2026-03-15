"""Developer helper for inspecting B01/Q7 SCMap payloads.

This script is intentionally kept outside the runtime package so it stays
non-obtrusive. It is useful when reverse-engineering new payload samples or
validating assumptions about the current parser.

Why not generated protobuf classes here?
- The inflated SCMap payload looks like protobuf wire format.
- We do not have an upstream `.proto` schema.
- For runtime code, reverse-engineering and committing guessed schema files
  would imply more certainty than we actually have.

So the library keeps a tiny schema-free parser for the fields it needs, while
this script provides a convenient place to inspect unknown payloads during
future debugging.

This helper is intentionally standalone and does not import private runtime
helpers. That keeps it useful for debugging without coupling test/dev tooling to
internal implementation details.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import zlib
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_B64_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


def _derive_map_key(serial: str, model: str) -> bytes:
    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = AES.new(model_key, AES.MODE_ECB).encrypt(pad(material, AES.block_size))
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


def _decode_base64_payload(raw_payload: bytes) -> bytes:
    blob = raw_payload.strip()
    if len(blob) < 32 or any(b not in _B64_CHARS for b in blob):
        raise ValueError("Unexpected B01 map payload format")

    padded = blob + b"=" * (-len(blob) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except binascii.Error as err:
        raise ValueError("Failed to decode B01 map payload") from err


def _decode_b01_map_payload(raw_payload: bytes, *, serial: str, model: str) -> bytes:
    encrypted_payload = _decode_base64_payload(raw_payload)
    if len(encrypted_payload) % AES.block_size != 0:
        raise ValueError("Unexpected encrypted B01 map payload length")

    map_key = _derive_map_key(serial, model)
    decrypted_hex = AES.new(map_key, AES.MODE_ECB).decrypt(encrypted_payload)

    try:
        compressed_hex = unpad(decrypted_hex, AES.block_size).decode("ascii")
        compressed_payload = bytes.fromhex(compressed_hex)
        return zlib.decompress(compressed_payload)
    except (ValueError, UnicodeDecodeError, zlib.error) as err:
        raise ValueError("Failed to decode B01 map payload") from err


def _read_varint(buf: bytes, idx: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if idx >= len(buf):
            raise ValueError("Truncated varint")
        byte = buf[idx]
        idx += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, idx
        shift += 7
        if shift > 63:
            raise ValueError("Invalid varint")


def _read_len_delimited(buf: bytes, idx: int) -> tuple[bytes, int]:
    length, idx = _read_varint(buf, idx)
    end = idx + length
    if end > len(buf):
        raise ValueError("Invalid length-delimited field")
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
            raise ValueError(f"Unsupported wire type {wire} in mapDataInfo")
    raise ValueError("SCMap missing mapData")


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
            raise ValueError(f"Unsupported wire type {wire} in roomDataInfo")
    return room_id, room_name


def _parse_scmap_payload(payload: bytes) -> tuple[int, int, bytes, dict[int, str]]:
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
            raise ValueError(f"Unsupported wire type {wire} in SCMap payload")

        value, idx = _read_len_delimited(payload, idx)
        if field_no == 3:
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
                    raise ValueError(f"Unsupported wire type {hwire} in map header")
        elif field_no == 4:
            grid = _parse_map_data_info(value)
        elif field_no == 12:
            room_id, room_name = _parse_room_data_info(value)
            if room_id is not None:
                room_names[room_id] = room_name or f"Room {room_id}"

    return size_x, size_y, grid, room_names


def _looks_like_message(blob: bytes) -> bool:
    if not blob or len(blob) > 4096:
        return False

    idx = 0
    seen = 0
    try:
        while idx < len(blob):
            key, idx = _read_varint(blob, idx)
            wire = key & 0x07
            seen += 1
            if wire == 0:
                _, idx = _read_varint(blob, idx)
            elif wire == 1:
                idx += 8
            elif wire == 2:
                _, idx = _read_len_delimited(blob, idx)
            elif wire == 5:
                idx += 4
            else:
                return False
        return seen > 0 and idx == len(blob)
    except Exception:
        return False


def _preview(blob: bytes, limit: int = 24) -> str:
    text = blob[:limit].hex()
    if len(blob) > limit:
        return f"{text}... ({len(blob)} bytes)"
    return f"{text} ({len(blob)} bytes)"


def _dump_message(blob: bytes, *, indent: str = "", max_depth: int = 2, depth: int = 0) -> None:
    idx = 0
    while idx < len(blob):
        start = idx
        key, idx = _read_varint(blob, idx)
        field_no = key >> 3
        wire = key & 0x07

        if wire == 0:
            int_value, idx = _read_varint(blob, idx)
            print(f"{indent}field {field_no} @ {start}: varint {int_value}")
        elif wire == 1:
            bytes_value = blob[idx : idx + 8]
            idx += 8
            print(f"{indent}field {field_no} @ {start}: fixed64 {_preview(bytes_value, 8)}")
        elif wire == 2:
            bytes_value, idx = _read_len_delimited(blob, idx)
            print(f"{indent}field {field_no} @ {start}: len-delimited {_preview(bytes_value)}")
            if depth < max_depth and _looks_like_message(bytes_value):
                _dump_message(bytes_value, indent=indent + "  ", max_depth=max_depth, depth=depth + 1)
        elif wire == 5:
            bytes_value = blob[idx : idx + 4]
            idx += 4
            print(f"{indent}field {field_no} @ {start}: fixed32 {_preview(bytes_value, 4)}")
        else:
            print(f"{indent}field {field_no} @ {start}: unsupported wire type {wire}")
            return


def _load_payload(args: argparse.Namespace) -> bytes:
    if args.inflated_gzip is not None:
        return gzip.decompress(args.inflated_gzip.read_bytes())
    if args.inflated_bin is not None:
        return args.inflated_bin.read_bytes()
    if args.raw_map_response is not None:
        if not args.serial or not args.model:
            raise SystemExit("--raw-map-response requires --serial and --model")
        return _decode_b01_map_payload(
            args.raw_map_response.read_bytes(),
            serial=args.serial,
            model=args.model,
        )
    raise SystemExit("one of --inflated-gzip, --inflated-bin, or --raw-map-response is required")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inflated-gzip", type=Path, help="Path to gzipped inflated SCMap payload")
    group.add_argument("--inflated-bin", type=Path, help="Path to raw inflated SCMap payload")
    group.add_argument("--raw-map-response", type=Path, help="Path to raw MAP_RESPONSE payload bytes")
    parser.add_argument("--serial", help="Device serial number (required for --raw-map-response)")
    parser.add_argument("--model", help="Device model, e.g. roborock.vacuum.sc05 (required for --raw-map-response)")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum recursive dump depth for protobuf-like messages",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = _load_payload(args)

    size_x, size_y, grid, room_names = _parse_scmap_payload(payload)
    print(f"Inflated payload: {len(payload)} bytes")
    print(f"Map size: {size_x} x {size_y}")
    print(f"Grid bytes: {len(grid)}")
    print(f"Room names: {room_names}")
    print("\nTop-level field dump:")
    _dump_message(payload, max_depth=args.max_depth)


if __name__ == "__main__":
    main()

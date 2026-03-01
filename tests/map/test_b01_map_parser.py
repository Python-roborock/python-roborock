"""Tests for B01/Q7 map decoder/parser/renderer."""

from __future__ import annotations

import base64
import zlib
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock.map.b01_map_parser import decode_b01_map_payload, derive_map_key, parse_scmap_payload, render_map_png

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "b01" / "raw-mqtt-map301.bin.inflated.bin"


def test_parse_scmap_payload_fixture() -> None:
    payload = FIXTURE.read_bytes()
    parsed = parse_scmap_payload(payload)
    assert parsed.size_x == 340
    assert parsed.size_y == 300
    assert len(parsed.map_data) >= parsed.size_x * parsed.size_y
    assert parsed.rooms is not None
    assert parsed.rooms.get(10) == "room1"


def test_render_map_png_fixture() -> None:
    payload = FIXTURE.read_bytes()
    parsed = parse_scmap_payload(payload)
    png = render_map_png(parsed)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1024


def test_decode_b01_map_payload_round_trip() -> None:
    local_key = "abcdefghijklmnop"
    serial = "testsn012345"
    model = "roborock.vacuum.sc05"
    inflated = FIXTURE.read_bytes()

    compressed = zlib.compress(inflated)
    map_key = derive_map_key(serial, model)
    encrypted = AES.new(map_key, AES.MODE_ECB).encrypt(pad(compressed.hex().encode(), 16))
    payload = base64.b64encode(base64.b64encode(encrypted))

    decoded = decode_b01_map_payload(payload, local_key=local_key, serial=serial, model=model)
    assert decoded == inflated

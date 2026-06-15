"""Tests for the Q10 vector-overlay (no-go / no-mop / virtual wall) decoder."""

import base64

from roborock.map.b01_q10_overlays import (
    ZONE_TYPE_NO_GO,
    ZONE_TYPE_NO_MOP,
    parse_zone_blob,
)


def _blob(version: int, records: list[bytes], record_size: int = 18) -> bytes:
    body = b"".join(r.ljust(record_size, b"\x00") for r in records)
    return bytes([version, len(records)]) + body


def _rect(zone_type: int, corners: list[tuple[int, int]]) -> bytes:
    out = bytes([zone_type, len(corners)])
    for x, y in corners:
        out += int.to_bytes(x & 0xFFFF, 2, "big") + int.to_bytes(y & 0xFFFF, 2, "big")
    return out


def test_parse_zone_blob_two_typed_rectangles() -> None:
    rect_a = _rect(ZONE_TYPE_NO_GO, [(0, 0), (10, 0), (10, 10), (0, 10)])
    rect_b = _rect(ZONE_TYPE_NO_MOP, [(-5, -5), (5, -5), (5, 5), (-5, 5)])
    zones = parse_zone_blob(_blob(1, [rect_a, rect_b]))
    assert [z.type for z in zones] == [ZONE_TYPE_NO_GO, ZONE_TYPE_NO_MOP]
    assert zones[0].vertices == [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert zones[1].vertices == [(-5, -5), (5, -5), (5, 5), (-5, 5)]  # signed coords


def test_parse_zone_blob_accepts_base64() -> None:
    blob = _blob(1, [_rect(ZONE_TYPE_NO_GO, [(1, 2), (3, 4), (5, 6), (7, 8)])])
    zones = parse_zone_blob(base64.b64encode(blob).decode())
    assert len(zones) == 1 and zones[0].vertices[2] == (5, 6)


def test_parse_zone_blob_empty_variants() -> None:
    assert parse_zone_blob(None) == []
    assert parse_zone_blob(b"\x00") == []  # device's "no zones" sentinel
    assert parse_zone_blob("AA==") == []  # base64 of 0x00
    assert parse_zone_blob(bytes([1, 0, 0])) == []  # version=1, count=0


def test_parse_zone_blob_skips_malformed_record() -> None:
    # vertex_count claims 9 verts (needs 38 bytes) but record is only 18 -> skipped.
    bad = bytes([ZONE_TYPE_NO_GO, 9]) + b"\x00" * 16
    good = _rect(ZONE_TYPE_NO_GO, [(1, 1), (2, 2), (3, 3), (4, 4)])
    zones = parse_zone_blob(_blob(1, [bad, good]))
    assert len(zones) == 1 and zones[0].vertices[0] == (1, 1)


def test_parse_zone_blob_real_record_size_inferred() -> None:
    """Record size is inferred from total/count (real device uses 38)."""
    rect = _rect(ZONE_TYPE_NO_GO, [(100, 200), (300, 200), (300, 50), (100, 50)])
    zones = parse_zone_blob(_blob(1, [rect], record_size=38))
    assert len(zones) == 1 and zones[0].vertices[0] == (100, 200)

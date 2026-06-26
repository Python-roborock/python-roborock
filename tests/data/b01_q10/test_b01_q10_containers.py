"""Tests for Q10 B01 container parsing helpers."""

import base64

import pytest

from roborock.data.b01_q10.b01_q10_containers import (
    normalize_q10_room_name,
    parse_customer_clean_payload,
)


def _build_payload(
    *,
    room_name_bytes: bytes,
    clean_order: int = 3,
    clean_count: int = 2,
    clean_type: int = 1,
    fan_level: int = 4,
    water_level: int = 2,
    material: int = 0,
    clean_line: int = 1,
) -> str:
    room_block = bytearray(26)
    room_block[0:2] = (42).to_bytes(2, "big")
    room_block[2] = 7
    room_block[3:5] = clean_order.to_bytes(2, "big", signed=False)
    room_block[5:7] = clean_count.to_bytes(2, "big", signed=False)
    room_block[7] = clean_type
    room_block[8] = fan_level
    room_block[9] = water_level
    room_block[10] = material
    room_block[11] = clean_line

    room_name = bytearray(20)
    room_name[: len(room_name_bytes)] = room_name_bytes

    # No vertices for these targeted parser tests.
    raw = bytes([1]) + bytes(room_block) + bytes(room_name) + bytes([0])
    return base64.b64encode(raw).decode("ascii")


def test_parse_customer_clean_payload_converts_sentinel_values() -> None:
    payload_b64 = _build_payload(
        room_name_bytes=bytes([7]) + b"rr_room",
        clean_order=0xFFFF,
        clean_type=0xFF,
        fan_level=0xFF,
        water_level=0xFF,
        material=0xFF,
        clean_line=0xFF,
    )

    parsed = parse_customer_clean_payload(payload_b64)

    assert parsed.declared_count == 1
    assert parsed.parsed_count == 1
    room = parsed.rooms[0]
    assert room.clean_order is None
    assert room.clean_type is None
    assert room.fan_level is None
    assert room.water_level is None
    assert room.material is None
    assert room.clean_line is None


@pytest.mark.parametrize(
    ("name_prefix", "name_data", "expected"),
    [
        (0, b"rr_living_room\x00", "Living Room"),
        (25, b"rr_toilet\x00", "Toilet"),
        (7, b"rr_hall", "Hall"),
    ],
)
def test_parse_customer_clean_payload_handles_name_length_edge_cases(
    name_prefix: int,
    name_data: bytes,
    expected: str,
) -> None:
    payload_b64 = _build_payload(room_name_bytes=bytes([name_prefix]) + name_data)

    parsed = parse_customer_clean_payload(payload_b64)

    assert parsed.parsed_count == 1
    assert parsed.rooms[0].room_name == expected


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("rr_living_room", "Living Room"),
        ("  rr_entrance_hall  ", "Entrance Hall"),
        ("rr_", "rr_"),
        ("Kitchen", "Kitchen"),
    ],
)
def test_normalize_q10_room_name(raw_name: str, expected: str) -> None:
    assert normalize_q10_room_name(raw_name) == expected


def test_parse_customer_clean_payload_with_multiple_rooms() -> None:
    room_block_1 = bytearray(26)
    room_block_1[0:2] = (42).to_bytes(2, "big")
    room_block_1[2] = 7
    room_block_1[3:5] = (3).to_bytes(2, "big")
    room_block_1[5:7] = (2).to_bytes(2, "big")
    room_block_1[7] = 1
    room_block_1[8] = 4
    room_block_1[9] = 2
    room_block_1[10] = 0
    room_block_1[11] = 1
    room_name_1 = bytearray(20)
    room_name_1[0] = 14
    room_name_1[1:15] = b"rr_living_room"
    vertices_1 = bytes([1]) + (100).to_bytes(2, "big") + (250).to_bytes(2, "big")

    room_block_2 = bytearray(26)
    room_block_2[0:2] = (99).to_bytes(2, "big")
    room_block_2[2] = 2
    room_block_2[3:5] = (1).to_bytes(2, "big")
    room_block_2[5:7] = (1).to_bytes(2, "big")
    room_block_2[7] = 2
    room_block_2[8] = 3
    room_block_2[9] = 1
    room_block_2[10] = 1
    room_block_2[11] = 0
    room_name_2 = bytearray(20)
    room_name_2[0] = 7
    room_name_2[1:8] = b"rr_hall"
    vertices_2 = (
        bytes([2])
        + (300).to_bytes(2, "big")
        + (450).to_bytes(2, "big")
        + (500).to_bytes(2, "big")
        + (700).to_bytes(2, "big")
    )

    raw = (
        bytes([2])
        + bytes(room_block_1)
        + bytes(room_name_1)
        + vertices_1
        + bytes(room_block_2)
        + bytes(room_name_2)
        + vertices_2
    )
    payload_b64 = base64.b64encode(raw).decode("ascii")

    parsed = parse_customer_clean_payload(payload_b64)

    assert parsed.declared_count == 2
    assert parsed.parsed_count == 2
    rooms_by_id = {r.room_id: r for r in parsed.rooms}
    assert rooms_by_id[42].raw_room_name == "rr_living_room"
    assert rooms_by_id[42].room_name == "Living Room"
    assert rooms_by_id[42].vertices_num == 1
    assert rooms_by_id[99].raw_room_name == "rr_hall"
    assert rooms_by_id[99].room_name == "Hall"
    assert rooms_by_id[99].vertices_num == 2

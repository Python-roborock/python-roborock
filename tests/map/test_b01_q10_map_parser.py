"""Tests for the Roborock Q10 (B01/ss07) map parser."""

from pathlib import Path

import pytest

from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    Q10Room,
    is_map_packet,
    lz4_block_decompress,
    parse_map_packet,
)

FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_map.bin"


def _payload() -> bytes:
    return FIXTURE.read_bytes()


def test_lz4_block_roundtrip_all_literals() -> None:
    """A simple all-literals block decodes back to the original bytes."""
    original = bytes(range(60)) * 3
    block = bytearray()
    block.append(0x0F << 4)
    block.append(len(original) - 15)
    block += original
    assert lz4_block_decompress(bytes(block)) == original


def test_lz4_block_back_reference() -> None:
    """Back-references expand runs (e.g. RLE-style repeats)."""
    # seq1: 1 literal 'A', then match (offset 1, length 4+4=8) -> 'A' x9.
    # seq2: final literals-only token (0 literals) ends the block per LZ4 spec.
    block = bytes([0x14, ord("A"), 0x01, 0x00, 0x00])
    assert lz4_block_decompress(block) == b"A" * 9


def test_is_map_packet() -> None:
    assert is_map_packet(b"\x01\x01rest")
    assert not is_map_packet(b"\x02\x01rest")  # trace packet
    assert not is_map_packet(b"")


def test_parse_map_packet() -> None:
    packet = parse_map_packet(_payload())
    assert packet.width == 8
    assert packet.height == 6
    assert packet.map_id == 0x01020304
    assert len(packet.grid) == packet.width * packet.height
    assert [(r.id, r.raw_name) for r in packet.rooms] == [(2, "rr_living_room"), (3, "bedroom")]


def test_room_name_normalization() -> None:
    """Firmware ``rr_`` default names are normalized; custom names are titled."""
    assert Q10Room(id=2, raw_name="rr_living_room", pixel_value=8, pixel_count=9).name == "Living Room"
    assert Q10Room(id=3, raw_name="bedroom", pixel_value=12, pixel_count=9).name == "Bedroom"


def test_room_pixel_count_matches_grid() -> None:
    packet = parse_map_packet(_payload())
    for room in packet.rooms:
        assert room.pixel_value == (room.id * 4) & 0xFF
        assert room.pixel_count == packet.grid.count(room.pixel_value)


def test_parser_renders_png_and_room_names() -> None:
    parsed = B01Q10MapParser().parse(_payload())
    assert parsed.image_content is not None
    assert parsed.image_content[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
    assert parsed.map_data is not None
    assert parsed.map_data.additional_parameters["room_names"] == {2: "Living Room", 3: "Bedroom"}


def test_parse_rejects_non_map_packet() -> None:
    with pytest.raises(RoborockException, match="not a Q10 map packet"):
        parse_map_packet(b"\x02\x01" + b"\x00" * 40)


def test_parse_rejects_bad_layout_length() -> None:
    payload = bytearray(_payload())
    payload[27:29] = (0xFFFF).to_bytes(2, "big")  # compressed length past the buffer
    with pytest.raises(RoborockException, match="invalid layout block length"):
        parse_map_packet(bytes(payload))

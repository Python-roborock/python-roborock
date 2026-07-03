"""Tests for the Roborock Q10 (B01/ss07) map parser."""

from pathlib import Path

import pytest

from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    Q10Room,
    is_map_packet,
    is_trace_packet,
    lz4_block_decompress,
    parse_map_packet,
    parse_trace_packet,
)

FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_map.bin"
TRACE_FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_trace.bin"
TRACE_MULTI_FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_trace_multi.bin"
# Real 15-point packet captured from an R1 corridor run (full session path).
TRACE_SESSION_FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_trace_session.bin"


def _payload() -> bytes:
    return FIXTURE.read_bytes()


def _literal_lz4_block(data: bytes) -> bytes:
    block = bytearray()
    literal_length = len(data)
    if literal_length < 15:
        block.append(literal_length << 4)
    else:
        block.append(0xF0)
        remaining = literal_length - 15
        while remaining >= 0xFF:
            block.append(0xFF)
            remaining -= 0xFF
        block.append(remaining)
    block.extend(data)
    return bytes(block)


def _synthetic_map_payload(width: int, decoded_layout: bytes) -> bytes:
    compressed = _literal_lz4_block(decoded_layout)
    payload = bytearray(29)
    payload[0:2] = b"\x01\x01"
    payload[2:6] = (0x01020304).to_bytes(4, "big")
    payload[8:10] = width.to_bytes(2, "little")
    payload[27:29] = len(compressed).to_bytes(2, "big")
    payload.extend(compressed)
    return bytes(payload)


def _room_record(room_id: int, name: str) -> bytes:
    record = bytearray(47)  # _ROOM_RECORD_LENGTH
    record[0:2] = room_id.to_bytes(2, "big")
    encoded = name.encode("utf-8")
    record[26] = len(encoded)
    record[27 : 27 + len(encoded)] = encoded
    return bytes(record)


def _full_header_map_payload(width: int, height: int, decoded_layout: bytes) -> bytes:
    """Build a map packet that populates the real u16be width and height fields."""
    compressed = _literal_lz4_block(decoded_layout)
    payload = bytearray(29)
    payload[0:2] = b"\x01\x01"
    payload[2:6] = (0x01020304).to_bytes(4, "big")
    payload[7:9] = width.to_bytes(2, "big")
    payload[9:11] = height.to_bytes(2, "big")
    payload[27:29] = len(compressed).to_bytes(2, "big")
    payload.extend(compressed)
    return bytes(payload)


def _trace_payload(points: list[tuple[int, int]], sequence: int = 1) -> bytes:
    header = bytearray(10)
    header[0:2] = b"\x02\x01"
    header[3] = sequence
    body = b"".join(x.to_bytes(2, "big", signed=True) + y.to_bytes(2, "big", signed=True) for x, y in points)
    return bytes(header) + body


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


def test_parse_map_packet_allows_zero_room_metadata() -> None:
    """A map can be present before the robot has room segmentation records."""
    grid = bytes([240, 240, 249, 243, 240, 240])
    packet = parse_map_packet(_synthetic_map_payload(width=3, decoded_layout=grid + b"\x01\x00"))
    assert packet.width == 3
    assert packet.height == 2
    assert packet.grid == grid
    assert packet.rooms == []


def test_parse_map_packet_reads_header_height() -> None:
    """Width and height come straight from the u16be header fields."""
    grid = bytes([8]) * 6 + bytes([12]) * 6  # two rooms, 4x3 grid
    layout = grid + b"\x01\x02" + _room_record(2, "rr_kitchen") + _room_record(3, "den")
    packet = parse_map_packet(_full_header_map_payload(width=4, height=3, decoded_layout=layout))
    assert (packet.width, packet.height) == (4, 3)
    assert [(r.id, r.raw_name) for r in packet.rooms] == [(2, "rr_kitchen"), (3, "den")]


def test_parse_map_packet_dimensions_straddling_256() -> None:
    """Regression: a 222x261 map (dimensions in different 256-bands).

    Width and height are consecutive u16be header fields. The earlier u16le read
    at offset 8 picked up the height's high byte, decoding this map's width as
    478 (0xDE | 0x01 << 8) and failing to split the layout. Reported, diagnosed
    and verified by @andrewlyeats from a real 222x261 capture.
    """
    width, height = 222, 261
    grid = bytearray(width * height)
    grid[0:100] = bytes([8]) * 100  # room id 2 -> pixel value 8
    grid[100:250] = bytes([12]) * 150  # room id 3 -> pixel value 12
    layout = bytes(grid) + b"\x01\x02" + _room_record(2, "rr_kitchen") + _room_record(3, "den")
    payload = _full_header_map_payload(width, height, layout)
    # The old u16le @ offset 8 read would have produced 478, not 222.
    assert int.from_bytes(payload[8:10], "little") == 478
    packet = parse_map_packet(payload)
    assert (packet.width, packet.height) == (222, 261)
    assert [(r.id, r.raw_name) for r in packet.rooms] == [(2, "rr_kitchen"), (3, "den")]


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


def test_packet_markers_are_distinct() -> None:
    map_payload = _payload()
    trace_payload = TRACE_FIXTURE.read_bytes()
    assert is_map_packet(map_payload) and not is_trace_packet(map_payload)
    assert is_trace_packet(trace_payload) and not is_map_packet(trace_payload)


def test_parse_trace_packet_real_single_point() -> None:
    """A real ss07 packet captured early in a session has a single path point."""
    trace = parse_trace_packet(TRACE_FIXTURE.read_bytes())
    assert trace.sequence == 9
    assert [(p.x, p.y) for p in trace.points] == [(169, 0)]
    assert trace.robot_position is not None
    assert (trace.robot_position.x, trace.robot_position.y) == (169, 0)


def test_parse_trace_packet_real_session_path() -> None:
    """A real 15-point packet (corridor run) decodes the full accumulated path.

    Captured live from an R1: the same session emitted packets of 1, then 3,
    then 15 points, proving the path accumulates rather than reporting only the
    current position. The most recent point is the current robot position.
    """
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    points = [(p.x, p.y) for p in trace.points]
    assert len(points) == 15
    assert points[0] == (-34, 0)  # oldest
    assert points[-1] == (276, -1)  # most recent == current position
    # After the initial repositioning, x marches steadily down the corridor.
    tail_x = [p[0] for p in points[2:]]
    assert tail_x == sorted(tail_x)
    assert points[-1][0] - points[0][0] > 300  # spans the corridor
    assert trace.robot_position is not None
    assert (trace.robot_position.x, trace.robot_position.y) == (276, -1)


def test_parse_trace_packet_multi_point() -> None:
    """A multi-point packet decodes all points; position is the most recent."""
    trace = parse_trace_packet(TRACE_MULTI_FIXTURE.read_bytes())
    assert [(p.x, p.y) for p in trace.points] == [(100, 200), (150, 250), (-50, 300)]
    # Signed coordinates are supported (negative x).
    assert trace.robot_position is not None
    assert (trace.robot_position.x, trace.robot_position.y) == (-50, 300)


def test_parse_trace_drops_stray_leading_point() -> None:
    """A stray first point far outside the path is dropped (calibration hygiene)."""
    points = [(0, -1907), (-3760, -1920), (-3758, -1918), (-3756, -1919)]
    trace = parse_trace_packet(_trace_payload(points))
    assert [(p.x, p.y) for p in trace.points] == points[1:]
    assert trace.robot_position is not None
    assert (trace.robot_position.x, trace.robot_position.y) == points[-1]


def test_parse_trace_keeps_genuine_first_point() -> None:
    """A normal first step (same scale as the rest) is never dropped."""
    points = [(0, 0), (10, 0), (22, 0), (35, 1)]
    trace = parse_trace_packet(_trace_payload(points))
    assert [(p.x, p.y) for p in trace.points] == points


def test_parse_trace_session_keeps_initial_reposition() -> None:
    """The real corridor capture has a 4.8x first step -- well under the 20x cut."""
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    assert len(trace.points) == 15
    assert (trace.points[0].x, trace.points[0].y) == (-34, 0)


def test_parse_trace_empty_path_has_no_position() -> None:
    header_only = b"\x02\x01" + b"\x00" * 8  # 10-byte header, no points
    trace = parse_trace_packet(header_only)
    assert trace.points == []
    assert trace.robot_position is None


def test_parse_trace_rejects_non_trace_packet() -> None:
    with pytest.raises(RoborockException, match="not a Q10 trace packet"):
        parse_trace_packet(_payload())


def test_parse_trace_rejects_misaligned_points() -> None:
    with pytest.raises(RoborockException, match="not 4-byte"):
        parse_trace_packet(b"\x02\x01" + b"\x00" * 8 + b"\x01\x02\x03")


def test_parse_rejects_bad_layout_length() -> None:
    payload = bytearray(_payload())
    payload[27:29] = (0xFFFF).to_bytes(2, "big")  # compressed length past the buffer
    with pytest.raises(RoborockException, match="invalid layout block length"):
        parse_map_packet(bytes(payload))

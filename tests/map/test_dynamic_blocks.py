"""Tests for the byte-level V1 map block container helpers."""

import struct
from pathlib import Path

import pytest

from roborock.exceptions import RoborockException
from roborock.map.dynamic_blocks import (
    DIGEST_BLOCK_TYPE,
    MAP_NONCE_ENTRY_ID,
    NONCE_TABLE_BLOCK_TYPE,
    MapBlock,
    decode_nonce_table,
    encode_blocks,
    find_block,
    iter_blocks,
    parse_dynamic_value,
    replace_block,
    split_map_file,
)

V1_FIXTURES = sorted((Path(__file__).parent / "testdata" / "v1").glob("*.bin"))


def raw_block(block_type: int, payload: bytes, extra_header: bytes = b"", *, header_length: int | None = None) -> bytes:
    """Hand-frame a block, optionally lying about the header length."""
    declared = 8 + len(extra_header) if header_length is None else header_length
    return struct.pack("<HHI", block_type, declared, len(payload)) + extra_header + payload


def nonce_table_block(entries: list[tuple[int, int]], *, num: int | None = None) -> MapBlock:
    """Build a block 34 with the given ``(id, nonce)`` entries."""
    payload = b"".join(struct.pack("<BI", entry_id, nonce) for entry_id, nonce in entries)
    return MapBlock(NONCE_TABLE_BLOCK_TYPE, payload, struct.pack("<I", len(entries) if num is None else num))


# --- Framing -----------------------------------------------------------------


def test_iter_blocks_round_trips_and_skips_extended_headers() -> None:
    """Blocks with extended headers are stepped over by their declared length."""
    blocks = [
        MapBlock(3, b"\x10\x00\x20\x00", b"\x01\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00"),
        MapBlock(18, b"\x01"),
        MapBlock(8, struct.pack("<iii", -100, 200, 90)),
    ]
    assert list(iter_blocks(encode_blocks(blocks))) == blocks


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (raw_block(8, b"\x00" * 12)[:5], "shorter than its common header"),
        (raw_block(8, b"\x00" * 12, header_length=0), "header length 0 < 8"),
        (raw_block(8, b"\x00" * 12)[:-1], "extends past the end"),
        (raw_block(8, b"\x00" * 12) + raw_block(3, b"\x00" * 4)[:7], "shorter than its common header"),
    ],
    ids=["truncated-header", "zero-header-no-progress", "truncated-payload", "trailing-partial"],
)
def test_iter_blocks_rejects_invalid_framing(data: bytes, message: str) -> None:
    """Malformed framing raises rather than yielding a partial block."""
    with pytest.raises(RoborockException, match=message):
        list(iter_blocks(data))


# --- Dynamic values ----------------------------------------------------------


@pytest.mark.parametrize("count", [0, 4], ids=["empty", "four-blocks"])
def test_parse_dynamic_value_accepts_up_to_four_blocks(count: int) -> None:
    """Dynamic values hold zero (empty) to four blocks."""
    blocks = [MapBlock(8, bytes([i]) * 12) for i in range(count)]
    assert parse_dynamic_value(encode_blocks(blocks)) == blocks


def test_parse_dynamic_value_rejects_fifth_block() -> None:
    """Reaching a fifth block trips the bounded guard."""
    data = encode_blocks(MapBlock(8, b"\x00" * 12) for _ in range(5))
    with pytest.raises(RoborockException, match="more than 4 blocks"):
        parse_dynamic_value(data)


# --- Map files ---------------------------------------------------------------


@pytest.mark.parametrize("fixture", V1_FIXTURES, ids=lambda p: p.stem)
def test_split_map_file_round_trips_real_maps(fixture: Path) -> None:
    """Every real fixture splits into blocks and re-encodes byte for byte.

    Byte identity is what lets the merge layer hand a rebuilt file to the
    upstream parser without the parser being able to tell the difference.
    """
    original = fixture.read_bytes()
    map_file = split_map_file(original)
    assert map_file.header.startswith(b"rr")
    assert map_file.blocks[0].block_type == 2, "image block is expected first"
    assert map_file.blocks[-1].block_type == DIGEST_BLOCK_TYPE
    assert map_file.encode() == original


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"xx" + struct.pack("<H", 20) + b"\x00" * 16, "'rr' marker"),
        (b"rr\x00", "shorter than its header length"),
        (b"rr" + struct.pack("<H", 99), "invalid header length"),
    ],
    ids=["bad-magic", "too-short", "header-beyond-end"],
)
def test_split_map_file_rejects_bad_headers(data: bytes, message: str) -> None:
    """A map file needs the marker and a sane header length."""
    with pytest.raises(RoborockException, match=message):
        split_map_file(data)


# --- Block substitution -------------------------------------------------------

IMAGE = MapBlock(2, b"\xff" * 4, b"\x00" * 16)
CHARGER = MapBlock(1, b"\x00" * 8)
PATH = MapBlock(3, b"\x01" * 4, b"\x00" * 12)
DIGEST = MapBlock(DIGEST_BLOCK_TYPE, b"\x00" * 20)


@pytest.mark.parametrize(
    ("blocks", "new_block", "expected_types"),
    [
        ([IMAGE, CHARGER, PATH, DIGEST], PATH.with_payload(b"\x02" * 8), [2, 1, 3, 1024]),
        ([IMAGE, CHARGER, PATH, DIGEST], MapBlock(18, b"\x01"), [2, 1, 3, 18, 1024]),
        ([IMAGE, CHARGER, PATH], MapBlock(18, b"\x01"), [2, 1, 3, 18]),
        ([], MapBlock(8, b"\x00" * 12), [8]),
    ],
    ids=["replace-in-place", "insert-before-digest", "append-without-digest", "empty-list"],
)
def test_replace_block_ordering(blocks: list[MapBlock], new_block: MapBlock, expected_types: list[int]) -> None:
    """Existing types are replaced in place; new types land before the digest.

    The parser only builds the mop path when block 18 follows block 3, and it
    locates the robot's room by the image block's byte offset, so order matters.
    """
    result = replace_block(blocks, new_block)
    assert [block.block_type for block in result] == expected_types
    assert find_block(result, new_block.block_type) == new_block
    assert find_block(result, 999) is None
    assert blocks is not result, "input list must not be mutated"


# --- Nonce table -------------------------------------------------------------


def test_decode_nonce_table_separates_map_and_element_nonces() -> None:
    """Entry 35 is the map nonce; everything else keys an element.

    Uses the fourteen entry shape observed on a real device and goes through
    the framing layer so the header and payload lengths are exercised too.
    """
    element_ids = [1, 2, 3, 5, 6, 11, 15, 16, 17, 21, 25, 26, 27]
    entries = [(element_id, 1000 + element_id) for element_id in element_ids] + [(MAP_NONCE_ENTRY_ID, 0xFFFFFFFF)]
    [decoded] = iter_blocks(nonce_table_block(entries).encode())
    table = decode_nonce_table(decoded)
    assert table.map_nonce == 0xFFFFFFFF, "nonces decode unsigned"
    assert table.element_nonces == {element_id: 1000 + element_id for element_id in element_ids}


def test_decode_nonce_table_without_map_entry() -> None:
    """A table lacking entry 35 reports no map nonce rather than guessing one."""
    table = decode_nonce_table(nonce_table_block([(3, 1)]))
    assert table.map_nonce is None
    assert table.element_nonces == {3: 1}


@pytest.mark.parametrize(
    ("block", "message"),
    [
        (MapBlock(3, b"", b"\x00" * 4), "not a nonce table"),
        (MapBlock(NONCE_TABLE_BLOCK_TYPE, b""), "shorter than 12 bytes"),
        (nonce_table_block([(3, 1)], num=2), "payload is too short"),
    ],
    ids=["wrong-type", "short-header", "num-exceeds-payload"],
)
def test_decode_nonce_table_rejects_malformed_blocks(block: MapBlock, message: str) -> None:
    """Structural problems raise instead of producing a partial table."""
    with pytest.raises(RoborockException, match=message):
        decode_nonce_table(block)

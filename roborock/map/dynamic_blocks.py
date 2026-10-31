"""Byte-level container helpers for Roborock V1 map blocks.

A V1 map file and the ``data`` / ``robot_data`` values returned by the dynamic
map diff commands share one block framing. Every block begins with an
eight-byte common header::

    offset 0, u16  block type
    offset 2, u16  header length H (including these eight bytes)
    offset 4, u32  payload length P
    offset 8 ..H   type-specific header fields
    offset H ..H+P payload

The next block starts exactly ``H + P`` bytes after the current one. All
multibyte fields are little-endian and unsigned.

This module only understands that framing. It can split a map file or a
dynamic value into blocks, rebuild a map file from blocks, and decode the
block 34 nonce table that identifies the base map and its dynamic elements.
It deliberately knows nothing about the meaning of any block payload; that
stays with the map parser (full maps) and the dynamic element merge logic.
"""

import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Self

from roborock.exceptions import RoborockException

# Marker at the start of a full V1 map file.
MAP_FILE_MAGIC = b"rr"

# Size of the block header fields shared by every block type.
COMMON_HEADER_LEN = 8

# A dynamic ``data`` / ``robot_data`` value holds at most this many blocks.
MAX_DYNAMIC_VALUE_BLOCKS = 4

# Block type of the nonce table carried inside a full map.
NONCE_TABLE_BLOCK_TYPE = 34

# Entry identifier inside the nonce table that supplies the map nonce.
MAP_NONCE_ENTRY_ID = 35

# Trailing digest block of a full map. New blocks are inserted before it.
DIGEST_BLOCK_TYPE = 1024

_COMMON_HEADER = struct.Struct("<HHI")
_NONCE_TABLE_NUM = struct.Struct("<I")
_NONCE_ENTRY = struct.Struct("<BI")
_NONCE_TABLE_MIN_HEADER_LEN = COMMON_HEADER_LEN + _NONCE_TABLE_NUM.size
_MAP_FILE_HEADER_LEN = struct.Struct("<H")


@dataclass(frozen=True)
class MapBlock:
    """One framed block: its type, type-specific header fields, and payload.

    ``extra_header`` holds the bytes between the common eight-byte header and
    the payload, so the common header is always regenerated from the lengths
    and can never disagree with the data it describes.
    """

    block_type: int
    payload: bytes
    extra_header: bytes = b""

    @property
    def header_length(self) -> int:
        """Total header length ``H`` written to the common header."""
        return COMMON_HEADER_LEN + len(self.extra_header)

    def with_payload(self, payload: bytes) -> Self:
        """Return a copy carrying ``payload`` and the same type and header fields."""
        return type(self)(self.block_type, payload, self.extra_header)

    def encode(self) -> bytes:
        """Serialize the block with a regenerated common header."""
        common = _COMMON_HEADER.pack(self.block_type, self.header_length, len(self.payload))
        return common + self.extra_header + self.payload


def iter_blocks(data: bytes, start: int = 0) -> Iterator[MapBlock]:
    """Yield consecutive blocks from ``data`` beginning at byte ``start``.

    The sequence must consume ``data`` exactly. A header shorter than eight
    bytes, a header or payload that runs past the end of ``data``, or a block
    that does not fit a complete common header is rejected.
    """
    position = start
    end = len(data)
    while position < end:
        if end - position < COMMON_HEADER_LEN:
            raise RoborockException(f"Map block at offset {position} is shorter than its common header")
        block_type, header_length, payload_length = _COMMON_HEADER.unpack_from(data, position)
        if header_length < COMMON_HEADER_LEN:
            raise RoborockException(f"Map block at offset {position} declares header length {header_length} < 8")
        block_end = position + header_length + payload_length
        if block_end > end:
            raise RoborockException(f"Map block at offset {position} extends past the end of the data")
        header_end = position + header_length
        yield MapBlock(
            block_type=block_type,
            payload=data[header_end:block_end],
            extra_header=data[position + COMMON_HEADER_LEN : header_end],
        )
        position = block_end


def parse_dynamic_value(data: bytes) -> list[MapBlock]:
    """Split a decoded dynamic ``data`` / ``robot_data`` value into blocks.

    A dynamic value is a bare block sequence: there is no ``rr`` file header
    and no digest. An empty value yields no blocks. A value that reaches a
    fifth block is rejected, so a non-empty value holds one to four blocks.
    """
    blocks: list[MapBlock] = []
    for block in iter_blocks(data):
        if len(blocks) == MAX_DYNAMIC_VALUE_BLOCKS:
            raise RoborockException(f"Dynamic map value holds more than {MAX_DYNAMIC_VALUE_BLOCKS} blocks")
        blocks.append(block)
    return blocks


def encode_blocks(blocks: Iterable[MapBlock]) -> bytes:
    """Serialize a block sequence without any file header."""
    return b"".join(block.encode() for block in blocks)


@dataclass(frozen=True)
class MapFile:
    """A full V1 map file split into its file header and framed blocks."""

    header: bytes
    """The ``rr`` file header, kept verbatim so it round-trips unchanged."""

    blocks: list[MapBlock]

    def encode(self) -> bytes:
        """Serialize the file header followed by every block."""
        return self.header + encode_blocks(self.blocks)


def split_map_file(map_bytes: bytes) -> MapFile:
    """Split a decompressed full map into its file header and blocks."""
    if not map_bytes.startswith(MAP_FILE_MAGIC):
        raise RoborockException("Map file does not start with the 'rr' marker")
    if len(map_bytes) < _MAP_FILE_HEADER_LEN.size + 2:
        raise RoborockException("Map file is shorter than its header length field")
    (header_length,) = _MAP_FILE_HEADER_LEN.unpack_from(map_bytes, 2)
    if header_length < 4 or header_length > len(map_bytes):
        raise RoborockException(f"Map file declares an invalid header length {header_length}")
    return MapFile(header=map_bytes[:header_length], blocks=list(iter_blocks(map_bytes, header_length)))


def find_block(blocks: Iterable[MapBlock], block_type: int) -> MapBlock | None:
    """Return the first block of ``block_type``, or ``None`` when absent."""
    for block in blocks:
        if block.block_type == block_type:
            return block
    return None


def replace_block(blocks: list[MapBlock], new_block: MapBlock) -> list[MapBlock]:
    """Return a new block list with ``new_block`` substituted for its type.

    The first existing block of the same type is replaced in place, so the
    relative order the map parser depends on (for example mop flags after
    the path they describe) is preserved. When the type is not present the
    block is inserted before the trailing digest, or appended when there is
    no digest.
    """
    for index, block in enumerate(blocks):
        if block.block_type == new_block.block_type:
            return [*blocks[:index], new_block, *blocks[index + 1 :]]
    for index, block in enumerate(blocks):
        if block.block_type == DIGEST_BLOCK_TYPE:
            return [*blocks[:index], new_block, *blocks[index:]]
    return [*blocks, new_block]


@dataclass(frozen=True)
class NonceTable:
    """Decoded block 34: identities of the base map and its dynamic elements.

    Nonces are opaque 32-bit identities. Only equality is meaningful. They are
    decoded unsigned to preserve all 32 bits. JSON values may use a signed
    representation, as the app's binary reader does. Callers must normalize
    JSON nonces with ``value & 0xFFFFFFFF`` before comparing them to this table.
    """

    map_nonce: int | None
    """Nonce of the base map (entry 35), or ``None`` when the table lacks it."""

    element_nonces: dict[int, int]
    """Element nonce keyed by element id, excluding the map nonce entry."""


def decode_nonce_table(block: MapBlock) -> NonceTable:
    """Decode a block 34 nonce table.

    The header carries ``num`` as a u32 at offset 8. The payload holds ``num``
    five-byte entries, each a one-byte identifier followed by a u32 nonce.
    """
    if block.block_type != NONCE_TABLE_BLOCK_TYPE:
        raise RoborockException(f"Block type {block.block_type} is not a nonce table")
    if block.header_length < _NONCE_TABLE_MIN_HEADER_LEN:
        raise RoborockException("Nonce table header is shorter than 12 bytes")
    (num,) = _NONCE_TABLE_NUM.unpack_from(block.extra_header, 0)
    if len(block.payload) < num * _NONCE_ENTRY.size:
        raise RoborockException(f"Nonce table declares {num} entries but the payload is too short")
    map_nonce: int | None = None
    element_nonces: dict[int, int] = {}
    for index in range(num):
        entry_id, nonce = _NONCE_ENTRY.unpack_from(block.payload, index * _NONCE_ENTRY.size)
        if entry_id == MAP_NONCE_ENTRY_ID:
            map_nonce = nonce
        else:
            element_nonces[entry_id] = nonce
    return NonceTable(map_nonce=map_nonce, element_nonces=element_nonces)

"""Parser for Roborock Q10 (B01/ss07) map packets.

Q10 devices deliver map data as a protocol-301 ``MAP_RESPONSE`` message (pushed a
few seconds after a ``dpRequestDps`` request). Unlike the Q7 ``SCMap`` protobuf
format, the Q10 uses a custom, unencrypted binary packet:

- ``01 01`` marker, then a ``u32be`` map id (bytes 2-5) and two consecutive
  ``u16be`` dimensions: grid width (bytes 7-8) and grid height (bytes 9-10).
- A header field at offset 27 (``u16be``) giving the compressed layout length.
- An LZ4-block-compressed occupancy grid starting at offset 29. Once inflated it
  is ``width * height`` cells of grid data followed by room metadata records.
- Room metadata begins with ``01 <room_count>`` followed by fixed 47-byte
  records (id, hints, ascii name). Each room paints cells with value
  ``room_id * 4`` in the grid.

The packet layout was confirmed against live Q10 captures. The format
documentation that informed this clean-room implementation comes from the
``roborock-qseries-map-bridge`` project (GPL-3.0-or-later):
https://github.com/v1b3c0d3x3r/roborock-qseries-map-bridge
"""

import colorsys
import io
import math
import statistics
from dataclasses import dataclass, field, replace

from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException

from .b01_grid_layers import (
    LAYER_BACKGROUND,
    LAYER_FLOOR,
    LAYER_UNKNOWN,
    LAYER_WALL,
    GridLayers,
    decompose_grid,
)
from .map_parser import ParsedMapData

_MAP_FILE_FORMAT = "PNG"

# Semantic raster classes, confirmed against real ss07 captures (rendered and
# eyeballed): 243 is the background outside the home (~half the grid), 240 is
# scanned floor not yet assigned to a room, other values >= 240 are walls, and
# 0 < value < 240 are per-room floor cells (value == room_id * 4).
_BACKGROUND_VALUE = 243
_UNSEGMENTED_FLOOR_VALUE = 240


def classify_q10_cell(value: int) -> str:
    """Map a Q10 grid cell value to a canonical layer class."""
    if value == 0:
        return LAYER_UNKNOWN
    if value == _BACKGROUND_VALUE:
        return LAYER_BACKGROUND
    if value == _UNSEGMENTED_FLOOR_VALUE:
        return LAYER_FLOOR
    if value >= _WALL_THRESHOLD:
        return LAYER_WALL
    return LAYER_FLOOR


MAP_PACKET_MARKER = b"\x01\x01"
TRACE_PACKET_MARKER = b"\x02\x01"

_MAP_ID_OFFSET = 2
# Width and height are two consecutive u16be fields. An earlier revision read the
# width as u16le at offset 8; that high byte is actually the height's high byte,
# so it only matched the true width when width and height fell in the same
# 256-band -- e.g. a 222x261 map decoded its width as 478 and failed to split.
# Reported and diagnosed by @andrewlyeats (independent B01/Q10 decoder), and
# corroborated by the ioBroker roborock adapter (both read these as u16be).
_WIDTH_OFFSET = 7
_HEIGHT_OFFSET = 9
_COMPRESSED_LAYOUT_LENGTH_OFFSET = 27
_LAYOUT_COMPRESSED_OFFSET = 29
_ROOM_RECORD_LENGTH = 47
_ROOM_NAME_LENGTH_OFFSET = 26
_MAX_ROOMS = 32
# Sanity bound for the erase-zone vector section's vertices-per-polygon field.
_MAX_ERASE_ZONE_VERTICES = 16

# The 01 01 grid-frame header also carries the map's calibration, so a
# GridCalibration can be derived without fitting a cleaning path (i.e. docked /
# pre-clean). Absolute byte offsets in the frame, reported and verified by
# @andrewlyeats across independent ss07 (fw 03.11.24) captures and cross-checked
# with the ioBroker roborock adapter:
# - 11-12 x_min, 13-14 y_min (s16be): map origin in 5 mm units. The grid is
#   50 mm/px, so dividing by 10 yields the origin in grid pixels -- the (ox, oy)
#   that solve_calibration otherwise recovers by sliding the path.
# - 15-16 resolution (u16be): reads 5 (= 0.05 m/px = 50 mm/px) universally.
# - 17-18 charger x, 19-20 charger y (s16be, 5 mm units), 21-22 charger phi.
_ORIGIN_X_OFFSET = 11
_ORIGIN_Y_OFFSET = 13
_HEADER_RESOLUTION_OFFSET = 15
_CHARGER_X_OFFSET = 17
_CHARGER_Y_OFFSET = 19
_CHARGER_PHI_OFFSET = 21
# The header origin/charger are in 5 mm units and the grid is 50 mm/px, so a
# header coordinate maps to grid pixels by dividing by this.
_HEADER_UNITS_PER_PIXEL = 10

# Grid cell values >= this are walls / borders rather than room segments.
_WALL_THRESHOLD = 240


@dataclass
class Q10Room:
    """A room (segment) described in a Q10 map packet."""

    id: int
    raw_name: str
    pixel_value: int
    pixel_count: int

    @property
    def name(self) -> str:
        """User friendly room name (firmware ``rr_`` defaults are normalized)."""
        return self.raw_name.removeprefix("rr_").replace("_", " ").strip().title()


@dataclass
class Q10EraseZone:
    """A user-drawn "erase" area (polygon) carried in the map packet.

    These are the app's *Erase* tool rectangles -- regions the user marked to be
    removed from the map (e.g. phantom floor the lidar mapped through windows).
    Coordinates are world units (millimetres), same frame as the path/zones.

    Confirmed by a controlled diff: removing the two erase zones on a live device
    dropped this section's count from 2 to 0 while the grid and the trailing
    raster were byte-identical. (Earlier revisions misidentified this section as
    "carpets"; it is the erase-zone list.)
    """

    vertices: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Q10HeaderCalibration:
    """Calibration carried in the ``01 01`` grid-frame header (ss07).

    Lets a :class:`~roborock.map.b01_grid_layers.GridCalibration` origin be read
    straight from the map packet -- no cleaning path / fit required, so it works
    docked or pre-clean. See :meth:`origin_pixels`.

    ``origin_x`` / ``origin_y`` and the charger coordinates are in 5 mm units;
    ``resolution`` is the raw header field (5 == 50 mm/px). ``charger_phi`` is the
    raw dock heading field. Reported and verified by @andrewlyeats (ss07).
    """

    origin_x: int
    origin_y: int
    resolution: int
    charger_x: int
    charger_y: int
    charger_phi: int

    @property
    def is_keepalive(self) -> bool:
        """True for null/keepalive frames (``x_min == y_min == 0``), which carry
        no usable origin -- callers should fall back to a path-fit calibration."""
        return self.origin_x == 0 and self.origin_y == 0

    def origin_pixels(self) -> tuple[float, float] | None:
        """The grid-pixel origin ``(ox, oy)`` for a ``GridCalibration``.

        The header origin is in 5 mm units and the grid is 50 mm/px, so the
        pixel origin is the header value divided by 10. Returns ``None`` for a
        keepalive frame (no origin to use)."""
        if self.is_keepalive:
            return None
        return (self.origin_x / _HEADER_UNITS_PER_PIXEL, self.origin_y / _HEADER_UNITS_PER_PIXEL)


@dataclass
class Q10MapPacket:
    """Decoded contents of a Q10 ``01 01`` map packet."""

    map_id: int
    width: int
    height: int
    grid: bytes
    rooms: list[Q10Room] = field(default_factory=list)
    erase_zones: list[Q10EraseZone] = field(default_factory=list)
    """Erase areas decoded from the packet tail (world coordinates)."""
    header_calibration: Q10HeaderCalibration | None = None
    """Calibration read straight from the grid-frame header (ss07), or ``None``."""
    carpet_mask: bytes | None = None
    """Carpet mask decoded from the packet tail: a full ``width*height`` grid in
    the same (top-down) pixel space as :attr:`grid`, where a non-zero cell is
    carpet (the value is the carpet kind). ``None`` if the packet carried none."""

    @property
    def layers(self) -> GridLayers:
        """Split the occupancy grid into separable grid-pixel layers."""
        rooms = [(room.id, room.name, room.pixel_value, room.pixel_count) for room in self.rooms]
        # The ss07 grid is stored top-down (row 0 = top), so no display flip is applied.
        return decompose_grid(self.width, self.height, self.grid, rooms, classify_q10_cell, flip=False)


@dataclass
class Q10Point:
    """A single point in Q10 map/trace coordinate space."""

    x: int
    y: int


@dataclass
class Q10TracePacket:
    """Decoded contents of a Q10 ``02 01`` cleaning-path packet.

    The robot accumulates the **full path of the current cleaning session** and
    serves it in a single packet: ``points`` holds the whole trajectory so far
    (oldest first), growing as the robot cleans. This was confirmed live -- a
    corridor run produced packets of 0 (just a heading, docked), then 3, then 14
    points, each a strict superset describing the path travelled. Because the
    robot keeps the path server-side, a client that connects mid-session still
    receives the complete path (this is how the app shows the trail even after a
    cold launch).

    A docked/idle robot can still emit a packet carrying only the ``heading``
    (zero points). The most recent point is the current robot position.
    """

    points: list[Q10Point] = field(default_factory=list)
    sequence: int = 0
    """Session counter (byte 3); increments per cleaning session, tracking the
    device clean count. Not a per-packet sequence."""

    heading: int = 0
    """Robot heading from the 0201 SLAM field (bytes 10-11), in degrees:
    ``0`` = +x, ``+90`` = +y, ``±180`` = −x, ``−90`` = −y. This is the current
    orientation; pair it with :attr:`robot_position` to draw a facing robot.

    Convention (incl. the y-sign) ground-truthed on a live R1 clean: across
    straight segments the reported heading equalled the direction of travel
    ``atan2(dy, dx)`` -- +x read 0, −x read ±180, a slight −y drift read
    negative."""

    @property
    def robot_position(self) -> Q10Point | None:
        """The current robot position (the most recent point)."""
        return self.points[-1] if self.points else None


# Trace packet (``02 01``): a 14-byte header followed by big-endian int16 (x, y)
# point pairs forming the accumulated session path. Header layout confirmed
# against live ss07 captures and cross-checked by @andrewlyeats:
# - byte 3: a session counter (tracks the device clean count).
# - bytes 8-9: a u16be point count -- the exact number of (x, y) pairs from
#   byte 14 (verified: captures of 1417 / 2462 points carried 0x0589 / 0x099e).
# - bytes 10-11: the 0201 SLAM heading (s16be degrees; 0 = +x, +90 = +y,
#   +-180 = -x, -90 = -y) -- the robot's current orientation.
# - bytes 12-13: a constant (0x0000).
# - byte 14 onward: the path points.
# An earlier revision used a 10-byte header, which folded the heading word into
# a phantom leading point ``(heading, 0)`` -- that is the "stray point" the
# heuristic below was papering over, and why the count read "one high". The
# parser reads all 4-byte pairs in the body rather than trusting the count
# field, so a truncated tail can't desync it.
# NOTE: the format documented by roborock-qseries-map-bridge (18-byte header)
# did not match this firmware -- this 14-byte layout is what the device sent.
_TRACE_HEADER_LENGTH = 14
_TRACE_SEQUENCE_OFFSET = 3
_TRACE_HEADING_OFFSET = 10

# Some cleans still prepend a single near-origin sentinel as the first real
# point (e.g. ~(5, 76) / (-3, 0) when the path proper starts near (-1700, -800));
# it skews the rendered start/bounding box and any path-based calibration. (This
# is distinct from the heading word the old 10-byte header used to surface as a
# phantom point -- that is now consumed by the header.) We drop points[0] only
# when its step to points[1] is a gross outlier (this multiple of the median step
# of the rest of the path), so a genuine first point is never lost. The current
# position (last point) is unaffected. Trigger and threshold reported and
# verified by @andrewlyeats across independent B01/Q10 captures.
_STRAY_POINT_STEP_RATIO = 20


def is_map_packet(payload: bytes) -> bool:
    """Return True if the payload is a Q10 full-map (``01 01``) packet."""
    return payload[:2] == MAP_PACKET_MARKER


def is_trace_packet(payload: bytes) -> bool:
    """Return True if the payload is a Q10 live trace (``02 01``) packet."""
    return payload[:2] == TRACE_PACKET_MARKER


def parse_trace_packet(payload: bytes) -> Q10TracePacket:
    """Parse a Q10 ``02 01`` trace packet into path points + robot position."""
    if not is_trace_packet(payload):
        raise RoborockException("Payload is not a Q10 trace packet")
    if len(payload) < _TRACE_HEADER_LENGTH:
        raise RoborockException("Q10 trace packet is shorter than its header")
    body = payload[_TRACE_HEADER_LENGTH:]
    if len(body) % 4:
        raise RoborockException("Q10 trace points are not 4-byte (x, y) pairs")

    heading = int.from_bytes(payload[_TRACE_HEADING_OFFSET : _TRACE_HEADING_OFFSET + 2], "big", signed=True)
    points = [
        Q10Point(
            x=int.from_bytes(body[offset : offset + 2], "big", signed=True),
            y=int.from_bytes(body[offset + 2 : offset + 4], "big", signed=True),
        )
        for offset in range(0, len(body), 4)
    ]
    points = _drop_stray_leading_point(points)
    return Q10TracePacket(points=points, sequence=payload[_TRACE_SEQUENCE_OFFSET], heading=heading)


def _drop_stray_leading_point(points: list[Q10Point]) -> list[Q10Point]:
    """Drop a spurious leading point that some cleans prepend to the trace.

    Returns ``points`` unchanged unless the very first step is a gross outlier
    versus the median of the remaining steps (see ``_STRAY_POINT_STEP_RATIO``),
    in which case the first point is dropped. Needs at least three points to have
    a stable median to compare against.
    """
    if len(points) < 3:
        return points
    steps = [math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(points, points[1:])]
    median_rest = statistics.median(steps[1:])
    if median_rest > 0 and steps[0] > _STRAY_POINT_STEP_RATIO * median_rest:
        return points[1:]
    return points


def lz4_block_decompress(data: bytes) -> bytes:
    """Decompress a raw LZ4 *block* (no frame header).

    The Q10 map grid is stored as a single LZ4 block. This implements the
    standard LZ4 block format so we don't add a native dependency.
    """
    index = 0
    output = bytearray()

    def read_length(value: int) -> int:
        nonlocal index
        if value != 0x0F:
            return value
        while True:
            if index >= len(data):
                raise RoborockException("Truncated LZ4 block while reading length")
            part = data[index]
            index += 1
            value += part
            if part != 0xFF:
                return value

    while True:
        if index >= len(data):
            raise RoborockException("Truncated LZ4 block while reading token")
        token = data[index]
        index += 1

        literal_length = read_length((token >> 4) & 0x0F)
        end = index + literal_length
        if end > len(data):
            raise RoborockException("Truncated LZ4 block while reading literals")
        output.extend(data[index:end])
        index = end

        if index == len(data):
            return bytes(output)
        if index + 2 > len(data):
            raise RoborockException("Truncated LZ4 block while reading match offset")

        offset = data[index] | (data[index + 1] << 8)
        index += 2
        if offset == 0 or offset > len(output):
            raise RoborockException("Invalid LZ4 back-reference offset")

        match_length = read_length(token & 0x0F) + 4
        for _ in range(match_length):
            output.append(output[-offset])


def _split_with_dims(decoded: bytes, width: int, height: int) -> tuple[bytes, bytes] | None:
    """Split the inflated layout into (grid, room_data) using header dimensions.

    Returns ``None`` when ``width * height`` does not leave a well-formed
    ``01 <room_count>`` room-record section, so the caller can fall back to
    brute-force inference (e.g. for captures/fixtures without a height field).
    """
    area = width * height
    if area <= 0 or area > len(decoded):
        return None
    room_data = decoded[area:]
    if len(room_data) < 2 or room_data[0] != 1:
        return None
    if len(room_data) != 2 + room_data[1] * _ROOM_RECORD_LENGTH:
        return None
    return decoded[:area], room_data


def _infer_layout(decoded: bytes, width: int) -> tuple[int, bytes, bytes]:
    """Split the inflated layout into (height, grid, room_data).

    The grid is ``width * height`` cells; the remaining bytes are room records
    introduced by an ``01 <room_count>`` marker. The room count is unknown up
    front, so we search for the split that makes the grid rectangular and lines
    up with the marker. Used as a fallback when the header carries no usable
    height.
    """
    for room_count in range(0, _MAX_ROOMS + 1):
        room_data_length = 2 + room_count * _ROOM_RECORD_LENGTH
        area = len(decoded) - room_data_length
        if area <= 0 or area % width:
            continue
        room_data = decoded[area:]
        if room_data[0] == 1 and room_data[1] == room_count:
            return area // width, decoded[:area], room_data
    raise RoborockException("Could not infer Q10 layout dimensions / room records")


def _parse_rooms(room_data: bytes, grid: bytes) -> list[Q10Room]:
    rooms: list[Q10Room] = []
    room_count = room_data[1]
    for index in range(room_count):
        start = 2 + index * _ROOM_RECORD_LENGTH
        record = room_data[start : start + _ROOM_RECORD_LENGTH]
        room_id = int.from_bytes(record[0:2], "big")
        name_length = record[_ROOM_NAME_LENGTH_OFFSET]
        raw_name = record[27 : 27 + name_length].decode("utf-8", errors="replace")
        pixel_value = (room_id * 4) & 0xFF
        rooms.append(
            Q10Room(
                id=room_id,
                raw_name=raw_name,
                pixel_value=pixel_value,
                pixel_count=grid.count(pixel_value),
            )
        )
    return rooms


def parse_map_packet(payload: bytes) -> Q10MapPacket:
    """Parse a Q10 ``01 01`` map packet into grid + room metadata."""
    if len(payload) < _LAYOUT_COMPRESSED_OFFSET or not is_map_packet(payload):
        raise RoborockException("Payload is not a Q10 map packet")

    map_id = int.from_bytes(payload[_MAP_ID_OFFSET : _MAP_ID_OFFSET + 4], "big")
    width = int.from_bytes(payload[_WIDTH_OFFSET : _WIDTH_OFFSET + 2], "big")
    height = int.from_bytes(payload[_HEIGHT_OFFSET : _HEIGHT_OFFSET + 2], "big")
    if width <= 0:
        raise RoborockException("Q10 map packet has invalid width")

    compressed_length = int.from_bytes(
        payload[_COMPRESSED_LAYOUT_LENGTH_OFFSET : _COMPRESSED_LAYOUT_LENGTH_OFFSET + 2], "big"
    )
    layout_end = _LAYOUT_COMPRESSED_OFFSET + compressed_length
    if compressed_length <= 0 or layout_end > len(payload):
        raise RoborockException("Q10 map packet has invalid layout block length")

    decoded = lz4_block_decompress(payload[_LAYOUT_COMPRESSED_OFFSET:layout_end])
    # Prefer the header height; fall back to inference if it doesn't line up
    # (e.g. older captures/fixtures that don't populate the height field).
    split = _split_with_dims(decoded, width, height) if height > 0 else None
    if split is not None:
        grid, room_data = split
    else:
        height, grid, room_data = _infer_layout(decoded, width)
    rooms = _parse_rooms(room_data, grid)
    tail = payload[layout_end:]
    erase_zones = _parse_erase_zones(tail)
    carpet_mask = _parse_carpet_mask(tail, width, height)
    header_calibration = _parse_header_calibration(payload)
    return Q10MapPacket(
        map_id=map_id,
        width=width,
        height=height,
        grid=grid,
        rooms=rooms,
        erase_zones=erase_zones,
        header_calibration=header_calibration,
        carpet_mask=carpet_mask,
    )


def _parse_header_calibration(payload: bytes) -> Q10HeaderCalibration | None:
    """Read the calibration fields from the ``01 01`` grid-frame header.

    All fields sit inside the fixed 29-byte header (already length-checked by
    the caller). See the offset constants for the byte layout. Returns the
    decoded :class:`Q10HeaderCalibration` (callers skip keepalive frames via
    :attr:`Q10HeaderCalibration.is_keepalive`)."""

    def s16(offset: int) -> int:
        return int.from_bytes(payload[offset : offset + 2], "big", signed=True)

    return Q10HeaderCalibration(
        origin_x=s16(_ORIGIN_X_OFFSET),
        origin_y=s16(_ORIGIN_Y_OFFSET),
        resolution=int.from_bytes(payload[_HEADER_RESOLUTION_OFFSET : _HEADER_RESOLUTION_OFFSET + 2], "big"),
        charger_x=s16(_CHARGER_X_OFFSET),
        charger_y=s16(_CHARGER_Y_OFFSET),
        charger_phi=s16(_CHARGER_PHI_OFFSET),
    )


def _parse_erase_zones(tail: bytes) -> list[Q10EraseZone]:
    """Decode erase areas from the bytes after the compressed grid block.

    The tail begins with a vector section ``[count: u8][vertices_per: u8]`` then
    ``count`` polygons of ``vertices_per`` int16-BE (x, y) pairs (axis-aligned
    rectangles in practice). Identified by a controlled diff on a live ss07
    device: deleting the two app *Erase* zones dropped ``count`` 2->0 with the
    rest of the packet byte-identical. The remaining tail (a run-length raster +
    signature) is unrelated to erase and is not decoded here.
    """
    if len(tail) < 2:
        return []
    count = tail[0]
    vertices_per = tail[1]
    if count == 0 or not 1 <= vertices_per <= _MAX_ERASE_ZONE_VERTICES:
        return []

    erase_zones: list[Q10EraseZone] = []
    offset = 2
    for _ in range(count):
        end = offset + vertices_per * 4
        if end > len(tail):
            break
        vertices = [
            (
                int.from_bytes(tail[offset + j * 4 : offset + j * 4 + 2], "big", signed=True),
                int.from_bytes(tail[offset + j * 4 + 2 : offset + j * 4 + 4], "big", signed=True),
            )
            for j in range(vertices_per)
        ]
        erase_zones.append(Q10EraseZone(vertices=vertices))
        offset = end
    return erase_zones


def _carpet_offset(tail: bytes) -> int:
    """Byte offset within the post-grid tail where the carpet mask begins.

    The erase section is ``[u8 count][u8 vertices_per]`` then ``count`` polygons
    of ``vertices_per`` int16 (x, y) pairs, so it always occupies
    ``2 + count*vertices_per*4`` bytes -- just the 2-byte header when count is 0.
    """
    if len(tail) < 2:
        return len(tail)
    count, vertices_per = tail[0], tail[1]
    return 2 + count * vertices_per * 4


def _parse_carpet_mask(tail: bytes, width: int, height: int) -> bytes | None:
    """Decode the carpet mask that follows the erase section in the packet tail.

    Framing matches the main grid block: ``[u32 uncompressed_len]``
    ``[u16 compressed_len][LZ4 block]``. The decompressed mask is a full
    ``width*height`` grid in the same (top-down) pixel space as the main grid; a
    non-zero cell is carpet (the value is the carpet kind). Confirmed byte-exact
    on live ss07 captures (R1 / RDC), where ``uncompressed_len == width*height``.

    Returns the decompressed mask, or ``None`` if the section is absent or does
    not line up (the ``uncompressed_len == width*height`` invariant is used as the
    guard so a mis-located section yields no carpet rather than garbage).
    """
    offset = _carpet_offset(tail)
    if offset + 6 > len(tail):
        return None
    uncompressed_len = int.from_bytes(tail[offset : offset + 4], "big")
    compressed_len = int.from_bytes(tail[offset + 4 : offset + 6], "big")
    block_end = offset + 6 + compressed_len
    if uncompressed_len != width * height or compressed_len <= 0 or block_end > len(tail):
        return None
    try:
        mask = lz4_block_decompress(tail[offset + 6 : block_end])
    except RoborockException:
        return None
    return mask if len(mask) == width * height else None


def erased_packet(packet: "Q10MapPacket", cells: set[int]) -> "Q10MapPacket":
    """Return a copy of ``packet`` with ``cells`` (grid indices) set to background.

    Used to apply the app's erase zones: cells inside an erase rectangle are blanked
    to the background class so they drop out of the rendered map and every layer.
    """
    if not cells:
        return packet
    grid = bytearray(packet.grid)
    for cell in cells:
        if 0 <= cell < len(grid):
            grid[cell] = _BACKGROUND_VALUE
    return replace(packet, grid=bytes(grid))


@dataclass
class B01Q10MapParserConfig:
    """Configuration for the Q10 map parser."""

    map_scale: int = 4
    """Scale factor for the rendered map image."""


class B01Q10MapParser:
    """Decoder/renderer for Q10 ``MAP_RESPONSE`` (protocol 301) payloads."""

    def __init__(self, config: B01Q10MapParserConfig | None = None) -> None:
        self._config = config or B01Q10MapParserConfig()

    @property
    def config(self) -> B01Q10MapParserConfig:
        """The parser configuration (image scale, ...)."""
        return self._config

    def parse(self, payload: bytes) -> ParsedMapData:
        """Parse a raw Q10 map packet into a rendered PNG + ``MapData``."""
        return self.parsed_from_packet(parse_map_packet(payload))

    def parse_packet(self, packet: Q10MapPacket) -> ParsedMapData:
        """Render an already-decoded packet.

        This preserves the public API used by the existing map trait. Callers
        rendering a modified packet can use :meth:`parsed_from_packet` directly.
        """
        return self.parsed_from_packet(packet)

    def parsed_from_packet(self, packet: Q10MapPacket) -> ParsedMapData:
        """Render a (possibly erase-modified) packet into a PNG + ``MapData``."""
        image = self._render(packet)

        map_data = MapData()
        map_data.image = ImageData(
            size=packet.width * packet.height,
            top=0,
            left=0,
            height=packet.height,
            width=packet.width,
            image_config=ImageConfig(scale=self._config.map_scale),
            data=image,
            img_transformation=lambda p: p,
        )
        room_names = {room.id: room.name for room in packet.rooms}
        if room_names:
            map_data.additional_parameters["room_names"] = room_names

        # Carpet cells are flat grid indices (y*width + x) in the same top-down
        # pixel space as the rendered raster, so they line up with the image.
        if packet.carpet_mask is not None:
            map_data.carpet_map = {i for i, value in enumerate(packet.carpet_mask) if value}

        image_bytes = io.BytesIO()
        image.save(image_bytes, format=_MAP_FILE_FORMAT)
        return ParsedMapData(image_content=image_bytes.getvalue(), map_data=map_data)

    def _render(self, packet: Q10MapPacket) -> Image.Image:
        """Render the Q10 grid: rooms get distinct colors, walls white, rest dark."""
        palette = _build_palette(packet.grid)
        rgb = bytearray()
        for value in packet.grid:
            rgb.extend(palette[value])
        img = Image.frombytes("RGB", (packet.width, packet.height), bytes(rgb))
        # The ss07 grid is stored top-down (row 0 = top of the home), so it is
        # rendered as-is -- unlike the V1/Q7 convention, no vertical flip.
        scale = self._config.map_scale
        if scale > 1:
            img = img.resize((packet.width * scale, packet.height * scale), resample=Image.Resampling.NEAREST)
        return img


def _build_palette(grid: bytes) -> list[tuple[int, int, int]]:
    """Map each grid value to an RGB color (rooms distinct, walls white)."""
    palette: list[tuple[int, int, int]] = [(28, 30, 38)] * 256  # default: unknown/outside
    room_values = sorted({v for v in set(grid) if 0 < v < _WALL_THRESHOLD})
    for index, value in enumerate(room_values):
        hue = (index * 0.139) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.5, 0.95)
        palette[value] = (int(r * 255), int(g * 255), int(b * 255))
    for value in range(_WALL_THRESHOLD, 256):
        palette[value] = (235, 235, 240)  # walls / borders
    palette[0] = (28, 30, 38)
    return palette

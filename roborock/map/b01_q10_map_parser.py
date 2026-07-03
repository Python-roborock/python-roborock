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
from dataclasses import dataclass, field

from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException

from .map_parser import ParsedMapData

_MAP_FILE_FORMAT = "PNG"

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
class Q10MapPacket:
    """Decoded contents of a Q10 ``01 01`` map packet."""

    map_id: int
    width: int
    height: int
    grid: bytes
    rooms: list[Q10Room] = field(default_factory=list)


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
    corridor run produced packets of 1, then 3, then 15 points, each a strict
    superset describing the path travelled. Because the robot keeps the path
    server-side, a client that connects mid-session still receives the complete
    path (this is how the app shows the trail even after a cold launch).

    The robot only emits these while a session is active, so an idle/docked robot
    will not produce them. The most recent point is the current robot position.
    """

    points: list[Q10Point] = field(default_factory=list)
    sequence: int = 0
    """Session counter (byte 3); increments per cleaning session, tracking the
    device clean count. Not a per-packet sequence."""

    @property
    def robot_position(self) -> Q10Point | None:
        """The current robot position (the most recent point)."""
        return self.points[-1] if self.points else None


# Trace packet (``02 01``): a 10-byte header followed by big-endian int16 (x, y)
# point pairs forming the accumulated session path. Header layout confirmed
# against live ss07 captures: byte 3 is a session counter (tracks the device
# clean count); bytes 8-9 are a u16be point count minus one (verified: a 15-point
# packet carried 0x000e == 14). The parser reads all 4-byte pairs in the body
# rather than trusting the count field, so a truncated tail can't desync it.
# NOTE: the format documented by roborock-qseries-map-bridge (18-byte header)
# did not match this firmware -- this 10-byte layout is what the device sent.
_TRACE_HEADER_LENGTH = 10
_TRACE_SEQUENCE_OFFSET = 3

# Some cleans prepend a single stray point to the path, far outside the map
# (e.g. ~(0, -1907) when the real path starts near (-3760, -1920)); it skews the
# rendered start/bounding box and any path-based calibration. We drop points[0]
# only when its step to points[1] is a gross outlier (this multiple of the
# median step of the rest of the path), so a genuine first point is never lost.
# The current position (last point) is unaffected. Trigger and threshold
# reported and verified by @andrewlyeats across independent B01/Q10 captures.
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

    points = [
        Q10Point(
            x=int.from_bytes(body[offset : offset + 2], "big", signed=True),
            y=int.from_bytes(body[offset + 2 : offset + 4], "big", signed=True),
        )
        for offset in range(0, len(body), 4)
    ]
    points = _drop_stray_leading_point(points)
    return Q10TracePacket(points=points, sequence=payload[_TRACE_SEQUENCE_OFFSET])


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
    return Q10MapPacket(map_id=map_id, width=width, height=height, grid=grid, rooms=rooms)


@dataclass
class B01Q10MapParserConfig:
    """Configuration for the Q10 map parser."""

    map_scale: int = 4
    """Scale factor for the rendered map image."""


class B01Q10MapParser:
    """Decoder/renderer for Q10 ``MAP_RESPONSE`` (protocol 301) payloads."""

    def __init__(self, config: B01Q10MapParserConfig | None = None) -> None:
        self._config = config or B01Q10MapParserConfig()

    def parse(self, payload: bytes) -> ParsedMapData:
        """Parse a raw Q10 map packet into a rendered PNG + ``MapData``."""
        return self.parse_packet(parse_map_packet(payload))

    def parse_packet(self, packet: Q10MapPacket) -> ParsedMapData:
        """Render an already-parsed Q10 map packet into a PNG + ``MapData``.

        The protocol layer parses the wire bytes into a :class:`Q10MapPacket`;
        this renders that packet without re-parsing it.
        """
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
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
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

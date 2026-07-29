"""Decoders for Q10 (B01/ss07) map vector overlays.

No-go zones, no-mop zones, virtual walls and zoned-clean areas are not part of
the map raster; the device reports them as base64-encoded blobs in separate data
points (``dpRestrictedZoneUp`` 55, ``dpVirtualWallUp`` 57, ``dpZonedUp`` 59).

The restricted-zone / zoned blob format (DP 55 and DP 59) was reverse-engineered
from a live ss07 (confirmed against 7 real no-go zones):

    [version: u8][count: u8] then ``count`` fixed-size records, each:
        [type: u8][vertex_count: u8] then vertex_count (x, y) int16-BE pairs,
        zero-padded to the record size.

Use :func:`parse_zone_blob` for those.  Virtual walls (DP 57) use a *different
framing* -- a bare ``[count]`` and 8-byte ``(x, y)`` records, no version/type/pad
-- so they have their own :func:`parse_virtual_wall_blob`; feeding DP 57 to
:func:`parse_zone_blob` mis-frames it (the leading byte is read as a version and
the next, a coordinate, as a record count).  The coordinate order matches the
zones (first wire word = x), confirmed against the app.  Provenance and the
byte-level breakdown are in PR #850's review thread.

Coordinates are in the device's world units (the same space as the cleaning
path), so a :class:`~roborock.map.b01_grid_layers.GridCalibration` maps them to
map pixels. ``type`` distinguishes the restriction kind (2 = no-mop, 3 = door
threshold, anything else -- incl. 0 -- a no-go zone); it is preserved verbatim
so callers can route polygons to the right ``MapData`` layer.
"""

import base64
import binascii
from dataclasses import dataclass, field

_DEFAULT_RECORD_SIZE = 38  # 2-byte record header + up to 9 (x, y) int16 pairs


@dataclass
class Q10Zone:
    """A polygon overlay (no-go / no-mop / virtual wall) in world coordinates."""

    type: int
    vertices: list[tuple[int, int]] = field(default_factory=list)


def _decode_blob(data: str | None) -> bytes:
    if data is None:
        return b""
    try:
        return base64.b64decode(data + "=" * (-len(data) % 4))
    except (ValueError, binascii.Error):
        return b""


def parse_zone_blob(data: str | None) -> list[Q10Zone]:
    """Decode a Q10 zone/wall overlay blob into a list of :class:`Q10Zone`.

    Accepts the base64 string straight from the data point. Returns ``[]`` for
    empty/absent/unparsable blobs (the device sends a single ``0x00`` byte when
    there are none).
    """
    raw = _decode_blob(data)
    if len(raw) < 2:
        return []
    count = raw[1]
    if count <= 0:
        return []

    body = raw[2:]
    record_size = len(body) // count if count and len(body) % count == 0 else _DEFAULT_RECORD_SIZE
    if record_size < 2:
        return []

    zones: list[Q10Zone] = []
    for index in range(count):
        record = body[index * record_size : (index + 1) * record_size]
        if len(record) < 2:
            break
        zone_type = record[0]
        vertex_count = record[1]
        needed = 2 + vertex_count * 4
        if needed > len(record):
            continue  # malformed record; skip rather than misread padding
        vertices = [
            (
                int.from_bytes(record[2 + j * 4 : 4 + j * 4], "big", signed=True),
                int.from_bytes(record[4 + j * 4 : 6 + j * 4], "big", signed=True),
            )
            for j in range(vertex_count)
        ]
        zones.append(Q10Zone(type=zone_type, vertices=vertices))
    return zones


_WALL_RECORD_SIZE = 8  # two (x, y) int16-BE endpoints


def parse_virtual_wall_blob(data: str | None) -> list[Q10Zone]:
    """Decode a Q10 virtual-wall overlay blob (``dpVirtualWallUp`` 57).

    Virtual walls use a *different framing* from the restricted-zone DPs handled
    by :func:`parse_zone_blob`: a single ``[count: u8]`` byte (no version, no
    per-record type/pad) followed by ``count`` 8-byte records, each two
    ``(x, y)`` int16-BE endpoints. The *coordinate order is the same* as the
    restricted zones (first wire word = x), so a wall and a no-go zone drawn on
    the same line decode parallel rather than transposed.

    Each wall is returned as a :class:`Q10Zone` of type
    :data:`ZONE_TYPE_VIRTUAL_WALL` with its two ``(x, y)`` endpoints, so callers
    can place them onto the map through the same
    :class:`~roborock.map.b01_grid_layers.GridCalibration` as the zones.

    Accepts the base64 string straight from the data point. Returns ``[]`` for
    empty/absent/unparsable blobs (the device sends a single ``0x00`` byte --
    base64 ``AA==`` -- when there are none).

    The axis order was confirmed against the app: a horizontal wall drawn below
    a room reads back with x varying and y constant (and the wide RDC no-go zone
    reads back wide), so DP 57 shares DP 55's order. An earlier revision swapped
    the wall axes to ``(y, x)`` -- following a misreading of PR #850's notes --
    which placed every wall transposed 90 degrees from where it was drawn.
    """
    raw = _decode_blob(data)
    if len(raw) < 1:
        return []
    count = raw[0]
    if count <= 0:
        return []

    body = raw[1:]
    walls: list[Q10Zone] = []
    for index in range(count):
        record = body[index * _WALL_RECORD_SIZE : (index + 1) * _WALL_RECORD_SIZE]
        if len(record) < _WALL_RECORD_SIZE:
            break  # truncated trailing record; stop rather than misread
        vertices = [
            (
                int.from_bytes(record[p * 4 : p * 4 + 2], "big", signed=True),
                int.from_bytes(record[p * 4 + 2 : p * 4 + 4], "big", signed=True),
            )
            for p in range(2)
        ]
        walls.append(Q10Zone(type=ZONE_TYPE_VIRTUAL_WALL, vertices=vertices))
    return walls


# Observed ``type`` values, confirmed against an ss07 Q10 (firmware 03.11.24) and
# cross-checked with the ioBroker roborock adapter: 2 = no-mop, 3 = door
# threshold. Any other value (including 0) is a no-go zone. The raw value is also
# kept on ``Q10Zone.type`` for callers that recognise it.
#
# Virtual walls arrive on a separate DP (VIRTUAL_WALL_UP 57) with their own frame
# (see :func:`parse_virtual_wall_blob`), so this restricted-zone DP only carries
# 0 / 2 / 3 -- never a 1.  ``ZONE_TYPE_VIRTUAL_WALL`` is kept here only to tag the
# walls that :func:`parse_virtual_wall_blob` produces.
#
# Corrected from an earlier reading that treated type 3 as no-mop -- 3 is the
# door-threshold rectangle; the no-mop area reads back as type 2. Reported and
# verified by @andrewlyeats (ss07 read-backs + the ioBroker Q10 parser).
ZONE_TYPE_NO_GO = 0
ZONE_TYPE_VIRTUAL_WALL = 1
ZONE_TYPE_NO_MOP = 2
ZONE_TYPE_THRESHOLD = 3

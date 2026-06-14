"""Decoders for Q10 (B01/ss07) map vector overlays.

No-go zones, no-mop zones, virtual walls and zoned-clean areas are not part of
the map raster; the device reports them as base64-encoded blobs in separate data
points (``dpRestrictedZoneUp`` 55, ``dpVirtualWallUp`` 57, ``dpZonedUp`` 59).

The blob format was reverse-engineered from a live ss07 (confirmed against 7
real no-go zones):

    [version: u8][count: u8] then ``count`` fixed-size records, each:
        [type: u8][vertex_count: u8] then vertex_count (x, y) int16-BE pairs,
        zero-padded to the record size.

Coordinates are in the device's world units (the same space as the cleaning
path), so a :class:`~roborock.map.b01_grid_layers.GridCalibration` maps them to
map pixels. ``type`` distinguishes the restriction kind (0 = no-go, 3 = no-mop
observed); it is preserved verbatim so callers can route polygons to the right
``MapData`` layer.
"""

import base64
from dataclasses import dataclass, field

_DEFAULT_RECORD_SIZE = 38  # 2-byte record header + up to 9 (x, y) int16 pairs


@dataclass
class Q10Zone:
    """A polygon overlay (no-go / no-mop / virtual wall) in world coordinates."""

    type: int
    vertices: list[tuple[int, int]] = field(default_factory=list)


def _as_bytes(data: bytes | str | None) -> bytes:
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    try:
        return base64.b64decode(data + "=" * (-len(data) % 4))
    except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
        return b""


def parse_zone_blob(data: bytes | str | None) -> list[Q10Zone]:
    """Decode a Q10 zone/wall overlay blob into a list of :class:`Q10Zone`.

    Accepts the raw bytes or the base64 string straight from the data point.
    Returns ``[]`` for empty/absent/unparseable blobs (the device sends a single
    ``0x00`` byte when there are none).
    """
    raw = _as_bytes(data)
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


# Observed ``type`` values. 0 = no-go (vacuum forbidden), 3 = no-mop. Others are
# surfaced verbatim on Q10Zone.type for callers that recognise them.
ZONE_TYPE_NO_GO = 0
ZONE_TYPE_NO_MOP = 3

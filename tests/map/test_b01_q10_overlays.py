"""Tests for the Q10 vector-overlay (no-go / no-mop / virtual wall) decoder."""

import base64

from roborock.map.b01_q10_overlays import (
    ZONE_TYPE_NO_GO,
    ZONE_TYPE_NO_MOP,
    ZONE_TYPE_THRESHOLD,
    ZONE_TYPE_VIRTUAL_WALL,
    parse_virtual_wall_blob,
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


def test_zone_type_constants() -> None:
    """ss07 + ioBroker: 0 no-go, 1 virtual wall, 2 no-mop, 3 threshold."""
    assert (ZONE_TYPE_NO_GO, ZONE_TYPE_VIRTUAL_WALL, ZONE_TYPE_NO_MOP, ZONE_TYPE_THRESHOLD) == (0, 1, 2, 3)


def test_parse_zone_blob_distinguishes_no_mop_and_threshold() -> None:
    """A no-mop (2) and a door-threshold (3) zone keep distinct types."""
    no_mop = _rect(ZONE_TYPE_NO_MOP, [(0, 0), (10, 0), (10, 10), (0, 10)])
    threshold = _rect(ZONE_TYPE_THRESHOLD, [(20, 20), (30, 20), (30, 22), (20, 22)])
    zones = parse_zone_blob(_blob(1, [no_mop, threshold]))
    assert [z.type for z in zones] == [ZONE_TYPE_NO_MOP, ZONE_TYPE_THRESHOLD]


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


def test_parse_zone_blob_real_rdc_three_no_go() -> None:
    """Real DP-55 read-back from our RDC ss07 with three No-Go Zones drawn.

    Captured live; exercises the 38-byte slot walk at count=3 against actual
    device bytes (all type 0 = no-go).
    """
    blob = (
        "AQMABP9A9ToAEPU6ABDzzv9A884AAAAAAAAAAAAAAAAAAAAAAAAAAAAE/Rb/mv5z/5r+c/3L/Rb9ywAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAQDpADEB3UAxAd1/GMDpPxjAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    )
    zones = parse_zone_blob(blob)
    assert [z.type for z in zones] == [ZONE_TYPE_NO_GO, ZONE_TYPE_NO_GO, ZONE_TYPE_NO_GO]
    assert zones[2].vertices == [(932, 196), (1909, 196), (1909, -925), (932, -925)]


def test_parse_virtual_wall_blob_real_capture() -> None:
    """Real DP-57 read-back from an ss07 (one wall drawn in the app).

    Frame is ``[count]`` + 8-byte ``(x, y)`` records -- no version byte, and the
    same coordinate order as the restricted zones (first wire word = x).
    Provenance: PR #850 review thread.
    """
    walls = parse_virtual_wall_blob("Aflu+cX87PoO")
    assert len(walls) == 1
    assert walls[0].type == ZONE_TYPE_VIRTUAL_WALL
    assert walls[0].vertices == [(-1682, -1595), (-788, -1522)]


def test_parse_virtual_wall_blob_real_r1_horizontal() -> None:
    """Real DP-57 read-back from the R1, ground-truthed against the app.

    The wall was drawn horizontally just below the Kids bedroom; it reads back
    with x varying (377 -> 951) and y constant (-83), i.e. horizontal. This is
    the capture that settled DP 57's axis order: an earlier revision swapped the
    axes and would have placed this wall vertical (transposed 90 degrees).
    """
    walls = parse_virtual_wall_blob("AQF5/60Dt/+t")
    assert [(w.type, w.vertices) for w in walls] == [
        (ZONE_TYPE_VIRTUAL_WALL, [(377, -83), (951, -83)]),
    ]


def test_parse_virtual_wall_blob_real_r1_mixed_orientation() -> None:
    """Real DP-57 read-back from the R1 with one horizontal + one vertical wall.

    Ground-truthed against the app: a wall drawn horizontally and another drawn
    (near-)vertically. They decode as such -- the first with y constant, the
    second with x near-constant (the 4-unit x drift matches the wall not being
    drawn perfectly vertical). This pins DP 57's axis order for *both*
    orientations at once, so a mixed pair can't come back transposed.
    """
    walls = parse_virtual_wall_blob("AgNyBGMFsARjAf8FAAH7CnE=")
    assert [(w.type, w.vertices) for w in walls] == [
        (ZONE_TYPE_VIRTUAL_WALL, [(882, 1123), (1456, 1123)]),  # horizontal: y constant
        (ZONE_TYPE_VIRTUAL_WALL, [(511, 1280), (507, 2673)]),  # vertical: x near-constant
    ]


def test_parse_virtual_wall_blob_real_rdc_two_walls() -> None:
    """Real DP-57 read-back from our RDC ss07 with two Invisible Walls drawn.

    Captured live after drawing the walls in the official app; the old
    parse_zone_blob silently returned [] for this exact blob (the regression
    this fix addresses).
    """
    walls = parse_virtual_wall_blob("AgAz/QMCDv0D/83+Dv/O/OY=")
    assert [(w.type, w.vertices) for w in walls] == [
        (ZONE_TYPE_VIRTUAL_WALL, [(51, -765), (526, -765)]),
        (ZONE_TYPE_VIRTUAL_WALL, [(-51, -498), (-50, -794)]),
    ]


def test_parse_virtual_wall_blob_empty_variants() -> None:
    assert parse_virtual_wall_blob(None) == []
    assert parse_virtual_wall_blob(b"\x00") == []  # device's "no walls" sentinel
    assert parse_virtual_wall_blob("AA==") == []  # base64 of 0x00


def test_parse_virtual_wall_blob_multiple_walls() -> None:
    """Two walls back-to-back; each is a separate 8-byte (x, y) record."""
    wall_a = bytes.fromhex("000a0014001e0028")  # (x,y)=(10,20)->(30,40)
    wall_b = bytes.fromhex("fffb0005fff6000a")  # (x,y)=(-5,5)->(-10,10)
    walls = parse_virtual_wall_blob(bytes([2]) + wall_a + wall_b)
    assert [w.vertices for w in walls] == [[(10, 20), (30, 40)], [(-5, 5), (-10, 10)]]


def test_parse_virtual_wall_blob_truncated_record_dropped() -> None:
    """A trailing record shorter than 8 bytes is dropped, not misread."""
    blob = bytes([2]) + bytes([0x00, 0x0A, 0x00, 0x14, 0x00, 0x1E, 0x00, 0x28]) + b"\x00\x00"
    walls = parse_virtual_wall_blob(blob)
    assert [w.vertices for w in walls] == [[(10, 20), (30, 40)]]


def test_zone_parser_misframes_virtual_wall_blob() -> None:
    """The restricted-zone parser must NOT be used on DP 57 -- it mis-frames it.

    Regression guard for the original bug: a DP-57 blob fed to parse_zone_blob
    reads the leading 0x01 as a version and the next coordinate byte as a record
    count, yielding garbage (here: nothing), so DP 57 needs its own decoder.
    """
    assert parse_zone_blob("Aflu+cX87PoO") != parse_virtual_wall_blob("Aflu+cX87PoO")

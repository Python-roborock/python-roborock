"""Tests for composing a Q10 map packet + overlays into a rendered result.

The pixel-level machinery (erase blanking, world-to-pixel overlay placement,
path drawing and calibration fitting) lives in ``b01_q10_render``. The map
trait's own tests cover the state management that drives this module.
"""

import io
from dataclasses import replace
from pathlib import Path

from PIL import Image

from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10EraseZone,
    Q10HeaderCalibration,
    Q10MapPacket,
    Q10Point,
    Q10TracePacket,
    parse_map_packet,
)
from roborock.map.b01_q10_overlays import (
    ZONE_TYPE_NO_GO,
    ZONE_TYPE_NO_MOP,
    ZONE_TYPE_VIRTUAL_WALL,
    Q10Zone,
)
from roborock.map.b01_q10_render import (
    _Q10_RESOLUTIONS,
    Q10MapOverlays,
    _calibration_from_header_metadata,
    _erased_cells,
    _vector_calibration,
    render_q10_map,
    solve_q10_calibration,
)

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
CONFIG = B01Q10MapParserConfig()

# identity-ish calibration used across the geometry tests: world (x, y) -> grid
# pixel (x, 5 - y) over the fixture's 8x6 grid (top-down, no flip).
IDENTITY = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
HEADER = Q10HeaderCalibration(origin_x=0, origin_y=50, resolution=5, charger_x=30, charger_y=30, charger_phi=90)
TRACE_CALIBRATION = GridCalibration(resolution=20.0, origin_x=0.0, origin_y=5.0, y_sign=1)
VECTOR_CALIBRATION = GridCalibration(resolution=10.0, origin_x=0.0, origin_y=5.0, y_sign=1)


def _packet() -> Q10MapPacket:
    return parse_map_packet(FIXTURE.read_bytes())


def _render(
    packet: Q10MapPacket | None = None,
    *,
    trace: Q10TracePacket | None = None,
    overlays: Q10MapOverlays | None = None,
) -> bytes:
    return render_q10_map(
        packet if packet is not None else _packet(),
        trace,
        overlays or Q10MapOverlays(),
        config=CONFIG,
    )


def _floor_world_points(layers, cal: GridCalibration, count: int) -> list[Q10Point]:
    """``count`` world points lying on the map's floor under ``cal``."""
    floor = [
        (px, py)
        for py in range(layers.height)
        for px in range(layers.width)
        if layers.cell_class(layers.grid[py * layers.width + px]) == "floor"
    ]
    return [Q10Point(*(int(v) for v in cal.pixel_to_world(px, py))) for px, py in floor[:count]]


def _world_vertices(calibration: GridCalibration, pixels: list[tuple[int, int]]) -> list[tuple[int, int]]:
    vertices = []
    for px, py in pixels:
        world_x, world_y = calibration.pixel_to_world(px, py)
        vertices.append((int(world_x), int(world_y)))
    return vertices


def _calibrated_inputs(*, heading: int = 0) -> tuple[Q10MapPacket, Q10TracePacket]:
    packet = replace(_packet(), header_calibration=HEADER)
    pixels = [(1, 1), (6, 1), (1, 2), (6, 2), (2, 3), (5, 3)]
    points = [Q10Point(*(int(value) for value in TRACE_CALIBRATION.pixel_to_world(px, py))) for px, py in pixels]
    trace = Q10TracePacket(points=points, heading=heading)
    return packet, trace


def test_render_base_map_without_calibration() -> None:
    """Without a calibration only the base raster is produced."""
    image = _render()
    assert image[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_draws_path_and_position() -> None:
    """The map and trace derive calibration and draw the robot position."""
    packet, trace = _calibrated_inputs()
    image = _render(packet, trace=trace)
    calibration = solve_q10_calibration(packet, trace)
    assert calibration is not None
    assert trace.robot_position is not None
    px, py = calibration.world_to_pixel(trace.robot_position.x, trace.robot_position.y)
    image_position = (round(px * CONFIG.map_scale), round(py * CONFIG.map_scale))
    rendered = Image.open(io.BytesIO(image)).convert("RGBA")
    assert rendered.size == (8 * 4, 6 * 4)
    # The shared V1 robot glyph has a white body at its center.
    assert rendered.getpixel(image_position) == (255, 255, 255, 255)


def test_render_draws_zones_and_virtual_walls() -> None:
    """Decoded DPS overlays are included in the composed image."""
    packet, trace = _calibrated_inputs()
    zones = [
        Q10Zone(type=ZONE_TYPE_NO_GO, vertices=_world_vertices(VECTOR_CALIBRATION, [(1, 1), (4, 1), (4, 4), (1, 4)])),
        Q10Zone(type=ZONE_TYPE_NO_MOP, vertices=_world_vertices(VECTOR_CALIBRATION, [(4, 1), (6, 1), (6, 3), (4, 3)])),
    ]
    walls = [Q10Zone(type=ZONE_TYPE_VIRTUAL_WALL, vertices=_world_vertices(VECTOR_CALIBRATION, [(1, 1), (6, 1)]))]
    base = _render(packet, trace=trace)
    rendered = _render(packet, trace=trace, overlays=Q10MapOverlays(zones=zones, virtual_walls=walls))
    assert rendered != base


def test_render_draws_zones_and_virtual_walls_without_trace() -> None:
    """Header calibration is sufficient to place restrictions while idle."""
    packet = replace(_packet(), header_calibration=HEADER)
    zones = [
        Q10Zone(
            type=ZONE_TYPE_NO_GO,
            vertices=_world_vertices(VECTOR_CALIBRATION, [(1, 1), (4, 1), (4, 4), (1, 4)]),
        )
    ]
    walls = [
        Q10Zone(
            type=ZONE_TYPE_VIRTUAL_WALL,
            vertices=_world_vertices(VECTOR_CALIBRATION, [(1, 1), (6, 1)]),
        )
    ]

    base = _render(packet)
    rendered = _render(packet, overlays=Q10MapOverlays(zones=zones, virtual_walls=walls))

    assert rendered != base


def test_render_draws_dock_from_header_without_trace() -> None:
    """The saved dock remains visible while the robot has no cleaning trace."""
    packet = _packet()

    base = _render(packet)
    rendered = _render(replace(packet, header_calibration=HEADER))

    assert rendered != base


def test_render_applies_erase_zones() -> None:
    """With a calibration, erase-zone cells are blanked from the image."""
    packet, trace = _calibrated_inputs()
    base = _render(packet, trace=trace)
    trace_calibration = solve_q10_calibration(packet, trace)
    calibration = _vector_calibration(packet, trace_calibration)
    assert calibration == VECTOR_CALIBRATION

    # A rectangle covering the whole grid in world coords erases every cell.
    corners = [(-1, -1), (8, -1), (8, 6), (-1, 6)]
    erase_zone = Q10EraseZone(vertices=_world_vertices(calibration, corners))
    cells = _erased_cells(packet.layers, [erase_zone], calibration)
    render = _render(replace(packet, erase_zones=[erase_zone]), trace=trace)

    assert len(cells) == packet.layers.width * packet.layers.height
    assert render != base


def test_render_applies_erase_zones_from_header_without_trace() -> None:
    """The map header is sufficient to erase zones while the robot is idle."""
    packet = replace(_packet(), header_calibration=HEADER)
    calibration = _calibration_from_header_metadata(packet)
    assert calibration == VECTOR_CALIBRATION

    corners = [(-1, -1), (8, -1), (8, 2), (-1, 2)]
    erase_zone = Q10EraseZone(vertices=_world_vertices(calibration, corners))
    cells = _erased_cells(packet.layers, [erase_zone], calibration)
    base = _render(packet)
    render = _render(replace(packet, erase_zones=[erase_zone]))

    assert 0 < len(cells) < packet.layers.width * packet.layers.height
    assert render != base


def test_render_partial_erase() -> None:
    """An erase rectangle only blanks the cells it covers, leaving the rest."""
    packet, trace = _calibrated_inputs()
    base = _render(packet, trace=trace)
    trace_calibration = solve_q10_calibration(packet, trace)
    calibration = _vector_calibration(packet, trace_calibration)
    assert calibration == VECTOR_CALIBRATION

    # Cover only the top two grid rows.
    corners = [(-1, -1), (8, -1), (8, 2), (-1, 2)]
    erase_zone = Q10EraseZone(vertices=_world_vertices(calibration, corners))
    cells = _erased_cells(packet.layers, [erase_zone], calibration)
    render = _render(replace(packet, erase_zones=[erase_zone]), trace=trace)

    assert 0 < len(cells) < packet.layers.width * packet.layers.height
    assert render != base


def test_render_robot_marker_reflects_heading() -> None:
    """The shared V1 robot glyph rotates its details with the Q10 heading."""
    packet, trace_right = _calibrated_inputs(heading=0)
    _, trace_up = _calibrated_inputs(heading=90)

    assert _render(packet, trace=trace_right) != _render(packet, trace=trace_up)


def test_solve_q10_calibration_uses_header_origin_with_short_path() -> None:
    """A grid-frame header origin lets a short path calibrate (origin is exact)."""
    packet, trace = _calibrated_inputs()
    assert len(trace.points) < 20  # far too short for the full origin+resolution fit

    cal = solve_q10_calibration(packet, trace)
    assert cal is not None
    # Origin comes straight from the header (exact); only the resolution is fit,
    # so it lands on one of the candidates (the exact pick is grid-quantized).
    assert (cal.origin_x, cal.origin_y) == (0.0, 5.0)
    assert cal.resolution in _Q10_RESOLUTIONS


def test_solve_q10_calibration_short_path_without_header_returns_none() -> None:
    """Without a header origin a short path is too sparse for the full fit."""
    packet = _packet()
    trace = Q10TracePacket(points=_floor_world_points(packet.layers, IDENTITY, 6))
    assert solve_q10_calibration(packet, trace) is None

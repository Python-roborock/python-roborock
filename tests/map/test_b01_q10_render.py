"""Tests for composing a Q10 map packet + overlays into a rendered result.

The pixel-level machinery (erase blanking, world-to-pixel overlay placement,
path drawing and calibration fitting) lives in ``b01_q10_render``. The map
trait's own tests cover the state management that drives this module.
"""

import io
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from PIL import Image
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.map_data import MapData, Point

from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10EraseZone,
    Q10HeaderCalibration,
    Q10HistoricalTracePacket,
    Q10MapPacket,
    Q10MapPacketKind,
    Q10Obstacle,
    Q10Point,
    Q10Room,
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
    Q10MapOverlays,
    _calibration_from_header_metadata,
    _erased_cells,
    _obstacle_calibration,
    _place_docked_robot,
    _place_obstacles,
    _room_at_position,
    _vector_calibration,
    render_q10_map,
    resolve_q10_current_room,
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
    trace: Q10TracePacket | Q10HistoricalTracePacket | None = None,
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


def _room_packet(grid: list[int], width: int) -> Q10MapPacket:
    """Build a minimal segmented map for deterministic room lookup tests."""
    return Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=width,
        height=len(grid) // width,
        grid=bytes(grid),
        rooms=[
            Q10Room(2, "rr_kitchen", 8, grid.count(8)),
            Q10Room(3, "hall", 12, grid.count(12)),
        ],
    )


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


def test_render_accepts_historical_trace() -> None:
    """A validated clean-record path uses the same calibrated drawing path."""
    packet, live_trace = _calibrated_inputs()
    historical = Q10HistoricalTracePacket(points=live_trace.points, heading=live_trace.heading)

    assert _render(packet, trace=historical) == _render(packet, trace=live_trace)


def test_place_obstacles_uses_its_validated_coordinate_scale() -> None:
    """Obstacle coordinates use 50 raw units per grid pixel around the origin."""
    packet = replace(
        _packet(),
        header_calibration=replace(HEADER, charger_x=0, charger_y=0),
        obstacles=[Q10Obstacle(50, 100), Q10Obstacle(-50, -50)],
    )
    map_data = MapData()

    calibration = _obstacle_calibration(packet)
    assert calibration == GridCalibration(resolution=50.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    assert _place_obstacles(map_data, packet)
    assert map_data.obstacles is not None
    assert [(obstacle.x, obstacle.y) for obstacle in map_data.obstacles] == [(1.0, 3.0), (-1.0, 6.0)]
    assert all(obstacle.details.type is None for obstacle in map_data.obstacles)


def test_place_obstacles_requires_header_calibration() -> None:
    """Unanchored obstacle points remain exposed but cannot be drawn safely."""
    packet = replace(_packet(), header_calibration=None, obstacles=[Q10Obstacle(50, 100)])
    map_data = MapData()

    assert _obstacle_calibration(packet) is None
    assert not _place_obstacles(map_data, packet)
    assert map_data.obstacles is None


def test_render_obstacles_respects_drawables_config() -> None:
    packet = replace(
        _packet(),
        header_calibration=replace(HEADER, charger_x=0, charger_y=0),
        obstacles=[Q10Obstacle(100, 100)],
    )

    hidden = render_q10_map(packet, None, Q10MapOverlays(), config=B01Q10MapParserConfig(drawables=[]))
    visible = render_q10_map(
        packet,
        None,
        Q10MapOverlays(),
        config=B01Q10MapParserConfig(drawables=[Drawable.OBSTACLES]),
    )

    assert visible != hidden


def test_skip_cleaning_points_are_not_rendered_as_obstacles() -> None:
    """The distinct skip-clean table must never gain an obstacle glyph."""
    packet = replace(
        _packet(),
        header_calibration=replace(HEADER, charger_x=0, charger_y=0),
        skip_cleaning_points=[Q10Point(100, 100)],
    )
    config = B01Q10MapParserConfig(drawables=[Drawable.OBSTACLES])

    assert _render(packet) == render_q10_map(packet, None, Q10MapOverlays(), config=config)


def test_room_at_position_exact_segment_wins_over_nearby_majority() -> None:
    packet = _room_packet([12, 12, 12, 12, 8, 12, 12, 12, 12], width=3)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(10, 10), calibration) == packet.rooms[0]


def test_room_at_position_uses_half_open_cell_boundaries() -> None:
    packet = _room_packet([8, 8, 12, 12], width=4)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(19, 0), calibration) == packet.rooms[0]
    assert _room_at_position(packet, Q10Point(20, 0), calibration) == packet.rooms[1]


@pytest.mark.parametrize("position", [Q10Point(-1, 10), Q10Point(30, 10), Q10Point(10, -1), Q10Point(10, 30)])
def test_room_at_position_rejects_fractional_and_exact_out_of_bounds(position: Q10Point) -> None:
    packet = _room_packet([8] * 9, width=3)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, position, calibration) is None


@pytest.mark.parametrize("coordinate", [float("nan"), float("inf"), float("-inf")])
def test_room_at_position_rejects_nonfinite_coordinates(coordinate: float) -> None:
    packet = _room_packet([8], width=1)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(cast(int, coordinate), 0), calibration) is None


def test_room_at_position_recovers_unique_nearby_room() -> None:
    packet = _room_packet([8, 8, 8, 8, 0, 8, 8, 8, 8], width=3)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(10, 10), calibration) == packet.rooms[0]


def test_room_at_position_expands_when_first_radius_has_no_room_cells() -> None:
    grid = [8, 0, 0, 0, 8] + [0] * 15 + [8, 0, 0, 0, 8]
    packet = _room_packet(grid, width=5)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    # Radius one has no segmented cells; radius two has only Kitchen cells.
    assert _room_at_position(packet, Q10Point(20, 20), calibration) == packet.rooms[0]


def test_room_at_position_returns_none_for_any_nearby_room_conflict() -> None:
    packet = _room_packet([8, 0, 12, 8, 0, 8, 8, 8, 8], width=3)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    # Kitchen has the numerical majority, but Hall is also present in the first
    # nonempty radius, so assigning a room would be ambiguous.
    assert _room_at_position(packet, Q10Point(10, 10), calibration) is None


def test_room_at_position_can_disable_nearby_fallback() -> None:
    packet = _room_packet([8, 8, 8, 8, 0, 8, 8, 8, 8], width=3)
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(10, 10), calibration, search_radius=0) is None


def test_room_at_position_requires_matching_room_metadata() -> None:
    packet = replace(_room_packet([8], width=1), rooms=[])
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    assert _room_at_position(packet, Q10Point(0, 0), calibration) is None


def test_resolve_current_room_uses_latest_live_position() -> None:
    packet = _room_packet([8, 12], width=2)
    trace = Q10TracePacket(points=[Q10Point(0, 0), Q10Point(10, 0)])
    calibration = GridCalibration(resolution=10, origin_x=0, origin_y=0, y_sign=-1)

    with patch("roborock.map.b01_q10_render.solve_q10_calibration", return_value=calibration):
        room = resolve_q10_current_room(packet, trace)

    assert room == packet.rooms[1]
    assert room is not packet.rooms[1]
    assert room is not None
    room.raw_name = "mutated"
    assert packet.rooms[1].raw_name == "hall"


def test_resolve_current_room_requires_position_and_calibration() -> None:
    packet = _room_packet([8], width=1)

    assert resolve_q10_current_room(packet, None) is None
    assert resolve_q10_current_room(packet, Q10TracePacket()) is None
    assert resolve_q10_current_room(packet, Q10TracePacket(points=[Q10Point(0, 0)])) is None


def test_single_point_uses_exact_header_transform_for_room_and_rendering() -> None:
    packet = replace(
        _packet(),
        header_calibration=replace(HEADER, charger_x=0, charger_y=0),
    )
    trace = Q10TracePacket(points=[Q10Point(100, 60)], heading=45)

    calibration = solve_q10_calibration(packet, trace)
    assert calibration == TRACE_CALIBRATION
    assert calibration.world_to_pixel(100, 60) == (5.0, 2.0)
    assert resolve_q10_current_room(packet, trace) == packet.rooms[1]

    rendered = Image.open(io.BytesIO(_render(packet, trace=trace))).convert("RGBA")
    position = (5 * CONFIG.map_scale, 2 * CONFIG.map_scale)
    assert rendered.getpixel(position) == (255, 255, 255, 255)


def test_empty_trace_does_not_force_a_map_redraw() -> None:
    """A metadata-only zero-point trace contributes no drawable content."""
    packet = replace(
        _packet(),
        header_calibration=replace(HEADER, charger_x=0, charger_y=0),
    )

    assert _render(packet, trace=Q10TracePacket()) == _render(packet)


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


def test_place_docked_robot_uses_shared_v1_marker_geometry() -> None:
    """The idle robot sits beside the dock, facing it, without a path."""
    map_data = MapData()
    map_data.charger = Point(20, 30, 90)

    assert _place_docked_robot(map_data)

    assert map_data.vacuum_position == Point(
        20,
        30 - Sizes.SIZES[Size.CHARGER_RADIUS],
        90,
    )
    assert map_data.path is None


def test_zero_degree_dock_places_robot_to_its_right() -> None:
    """The Q10 dock heading is already its outward-facing direction."""
    map_data = MapData()
    map_data.charger = Point(3, 3, 0)

    assert _place_docked_robot(map_data)

    assert map_data.vacuum_position == Point(
        3 + Sizes.SIZES[Size.CHARGER_RADIUS],
        3,
        0,
    )


def test_render_applies_erase_zones() -> None:
    """With a calibration, erase-zone cells are blanked from the image."""
    packet, trace = _calibrated_inputs()
    assert packet.header_calibration is not None
    packet = replace(packet, header_calibration=replace(packet.header_calibration, charger_x=0, charger_y=0))
    base = _render(packet)
    trace_calibration = solve_q10_calibration(packet, trace)
    calibration = _vector_calibration(packet, trace_calibration)
    assert calibration == VECTOR_CALIBRATION

    # A rectangle covering the whole grid in world coords erases every cell.
    corners = [(-1, -1), (8, -1), (8, 6), (-1, 6)]
    erase_zone = Q10EraseZone(vertices=_world_vertices(calibration, corners))
    cells = _erased_cells(packet.layers, [erase_zone], calibration)
    render = _render(replace(packet, erase_zones=[erase_zone]))

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


def test_header_vector_calibration_is_independent_of_trace_orientation() -> None:
    """A live trace cannot flip saved erase/restriction geometry vertically."""
    packet = replace(_packet(), header_calibration=HEADER)
    mirrored_trace = replace(TRACE_CALIBRATION, y_sign=-1)

    assert _vector_calibration(packet, mirrored_trace) == VECTOR_CALIBRATION


def test_render_partial_erase() -> None:
    """An erase rectangle only blanks the cells it covers, leaving the rest."""
    packet, trace = _calibrated_inputs()
    assert packet.header_calibration is not None
    packet = replace(packet, header_calibration=replace(packet.header_calibration, charger_x=0, charger_y=0))
    base = _render(packet)
    trace_calibration = solve_q10_calibration(packet, trace)
    calibration = _vector_calibration(packet, trace_calibration)
    assert calibration == VECTOR_CALIBRATION

    # Cover only the top two grid rows.
    corners = [(-1, -1), (8, -1), (8, 2), (-1, 2)]
    erase_zone = Q10EraseZone(vertices=_world_vertices(calibration, corners))
    cells = _erased_cells(packet.layers, [erase_zone], calibration)
    render = _render(replace(packet, erase_zones=[erase_zone]))

    assert 0 < len(cells) < packet.layers.width * packet.layers.height
    assert render != base


def test_render_robot_marker_reflects_heading() -> None:
    """The shared V1 robot glyph rotates its details with the Q10 heading."""
    packet, trace_right = _calibrated_inputs(heading=0)
    _, trace_up = _calibrated_inputs(heading=90)

    assert _render(packet, trace=trace_right) != _render(packet, trace=trace_up)


def test_solve_q10_calibration_uses_header_origin_with_short_path() -> None:
    """Validated header metadata calibrates a short path exactly."""
    packet, trace = _calibrated_inputs()
    assert len(trace.points) < 20  # far too short for the full origin+resolution fit

    cal = solve_q10_calibration(packet, trace)
    assert cal is not None
    assert cal == TRACE_CALIBRATION


@pytest.mark.parametrize(
    "header",
    [
        replace(HEADER, resolution=100),
        replace(HEADER, origin_x=100_000, origin_y=100_000),
    ],
)
def test_solve_q10_calibration_rejects_implausible_header_and_falls_back(
    header: Q10HeaderCalibration,
) -> None:
    """Corrupt metadata cannot displace an otherwise fit-able cleaning path."""
    packet = replace(_packet(), header_calibration=header)
    trace = Q10TracePacket(points=[Q10Point(index, index) for index in range(20)])
    fallback = GridCalibration(resolution=17, origin_x=3, origin_y=4, y_sign=-1)

    with patch("roborock.map.b01_q10_render._calibration_from_fit", return_value=fallback) as fit:
        assert solve_q10_calibration(packet, trace) == fallback

    fit.assert_called_once_with(packet.layers, [(point.x, point.y) for point in trace.points])


def test_solve_q10_calibration_short_path_without_header_returns_none() -> None:
    """Without a header origin a short path is too sparse for the full fit."""
    packet = _packet()
    trace = Q10TracePacket(points=_floor_world_points(packet.layers, IDENTITY, 6))
    assert solve_q10_calibration(packet, trace) is None

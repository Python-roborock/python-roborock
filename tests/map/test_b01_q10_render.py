"""Tests for composing a Q10 map packet + overlays into a rendered result.

The pixel-level machinery (erase blanking, world-to-pixel overlay placement,
path drawing and calibration fitting) lives in ``b01_q10_render``. The map
trait's own tests cover the state management that drives this module.
"""

import io
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.map_data import MapData, Point

from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10CleanRecordDetail,
    Q10EraseZone,
    Q10HeaderCalibration,
    Q10HistoricalTracePacket,
    Q10MapPacket,
    Q10MapPacketKind,
    Q10Obstacle,
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
    Q10MapOverlays,
    _calibration_from_header_metadata,
    _erased_cells,
    _map_data_from_packet,
    _place_docked_robot,
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


def test_render_distinct_background_floor_and_walls() -> None:
    """Background must not hide the wall layer by sharing its color."""
    packet = Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=4,
        height=1,
        grid=bytes([243, 240, 249, 8]),
    )
    rendered = _render(packet)
    image = Image.open(io.BytesIO(rendered))
    scale = CONFIG.map_scale
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)
    assert image.getpixel((scale, 0)) == (32, 115, 185, 255)
    assert image.getpixel((scale * 2, 0)) == (93, 109, 126, 255)
    assert image.getpixel((scale * 3, 0)) == (133, 193, 233, 255)


def test_render_gives_adjacent_rooms_distinct_palette_colors() -> None:
    """Repeated V1 palette entries do not merge neighboring Q10 rooms."""
    packet = Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=2,
        height=1,
        grid=bytes([2 * 4, 12 * 4]),
    )
    rendered = _render(packet)
    image = Image.open(io.BytesIO(rendered))
    scale = CONFIG.map_scale
    assert image.getpixel((0, 0)) != image.getpixel((scale, 0))


def test_map_data_from_packet_populates_room_names_and_carpet_map() -> None:
    """Base MapData populates room_names and flat carpet_map indices."""
    carpet = bytearray(8 * 6)
    carpet[10] = 4
    carpet[20] = 3
    packet = replace(_packet(), carpet_mask=bytes(carpet))
    map_data = _map_data_from_packet(packet, config=CONFIG)
    assert map_data.additional_parameters["room_names"] == {2: "Living Room", 3: "bedroom"}
    assert map_data.carpet_map == {10, 20}


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

    archived = Q10CleanRecordDetail(map=packet, trace=historical)
    assert _render(archived.map, trace=archived.trace) == _render(packet, trace=live_trace)
    assert _render(archived.map) != _render(archived.map, trace=archived.trace)


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
    packet = replace(packet, header_calibration=replace(HEADER, charger_x=-1, charger_y=-1))
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
    packet = replace(packet, header_calibration=replace(HEADER, charger_x=-1, charger_y=-1))
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
    """A grid-frame header origin lets a short path calibrate (origin is exact)."""
    packet, trace = _calibrated_inputs()
    assert len(trace.points) < 20  # far too short for the full origin+resolution fit

    cal = solve_q10_calibration(packet, trace)
    assert cal is not None
    assert cal == TRACE_CALIBRATION


def test_solve_q10_calibration_short_path_without_header_returns_none() -> None:
    """Without a header origin a short path is too sparse for the full fit."""
    packet = _packet()
    trace = Q10TracePacket(points=_floor_world_points(packet.layers, IDENTITY, 6))
    assert solve_q10_calibration(packet, trace) is None


@pytest.mark.parametrize(
    "pixel, expected_id", [((2, 2), 2), ((5, 2), 3), ((0, 2), 2), ((3, 4), None), ((-1, 2), None), ((8, 2), None)]
)
def test_resolve_current_room_exact_nearby_ambiguous_and_outside(
    pixel: tuple[int, int],
    expected_id: int | None,
) -> None:
    """Fixture segments resolve exactly or conservatively around doorways."""
    packet = replace(_packet(), header_calibration=HEADER)
    points = [Q10Point(40, 60), Q10Point(100, 60)]
    points.append(Q10Point(*(int(value) for value in TRACE_CALIBRATION.pixel_to_world(*pixel))))
    trace = Q10TracePacket(points=points)
    room = resolve_q10_current_room(packet, trace)
    assert (room.id if room is not None else None) == expected_id


def test_single_pose_uses_header_calibration_for_room_and_rendering() -> None:
    packet = replace(_packet(), header_calibration=replace(HEADER, charger_x=-1, charger_y=-1))
    trace = Q10TracePacket(points=[Q10Point(100, 60)], heading=45)
    assert solve_q10_calibration(packet, trace) == TRACE_CALIBRATION
    assert resolve_q10_current_room(packet, trace) == packet.rooms[1]
    rendered = Image.open(io.BytesIO(_render(packet, trace=trace)))
    assert rendered.getpixel((5 * CONFIG.map_scale, 2 * CONFIG.map_scale)) == (255, 255, 255, 255)


@pytest.mark.parametrize(
    "header", [None, replace(HEADER, resolution=100), replace(HEADER, origin_x=30000, origin_y=30000)]
)
def test_current_room_uses_dense_path_fallback_when_header_is_unusable(header: Q10HeaderCalibration | None) -> None:
    packet = replace(_packet(), header_calibration=header)
    floor_pixels = [(x, y) for y in (1, 2, 3) for x in (1, 2, 3, 4, 5, 6)]
    pixels = floor_pixels * 2 + [(5, 2)]
    trace = Q10TracePacket(
        points=[Q10Point(*(int(v) for v in TRACE_CALIBRATION.pixel_to_world(x, y))) for x, y in pixels]
    )
    calibration = solve_q10_calibration(packet, trace)
    assert calibration is not None
    assert resolve_q10_current_room(packet, trace) == packet.rooms[1]


def test_current_room_requires_pose_calibration_and_matching_metadata() -> None:
    packet = _packet()
    assert resolve_q10_current_room(packet, None) is None
    assert resolve_q10_current_room(packet, Q10TracePacket()) is None
    assert resolve_q10_current_room(packet, Q10TracePacket(points=[Q10Point(100, 60)])) is None
    packet = replace(packet, header_calibration=HEADER, rooms=[])
    assert resolve_q10_current_room(packet, Q10TracePacket(points=[Q10Point(100, 60)])) is None


@pytest.mark.parametrize("origin", [(0, 500), (100, 600)])
def test_render_obstacle_at_header_anchored_position(origin: tuple[int, int]) -> None:
    """A marker is placed using 50 raw units per pixel, with a top-down image."""
    header = Q10HeaderCalibration(*origin, 5, -1, -1, 0)
    packet = Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=100,
        height=100,
        grid=bytes([8]) * 10000,
        header_calibration=header,
        obstacles=[Q10Obstacle((50 - origin[0] // 10) * 50, (origin[1] // 10 - 40) * 50)],
    )
    config = B01Q10MapParserConfig(map_scale=4, drawables=[Drawable.OBSTACLES])
    rendered = Image.open(io.BytesIO(render_q10_map(packet, None, Q10MapOverlays(), config=config)))
    base = Image.open(io.BytesIO(render_q10_map(replace(packet, obstacles=[]), None, Q10MapOverlays(), config=config)))
    assert rendered.getpixel((200, 160)) != base.getpixel((200, 160))
    assert rendered.getpixel((20, 20)) == base.getpixel((20, 20))


@pytest.mark.parametrize("header", [None, Q10HeaderCalibration(0, 0, 5, -1, -1, 0)])
def test_render_unanchored_obstacle_matches_base(header: Q10HeaderCalibration | None) -> None:
    packet = replace(_packet(), header_calibration=header, obstacles=[Q10Obstacle(100, 100)])
    assert _render(packet) == _render(replace(packet, obstacles=[]))


def test_render_obstacles_respects_drawables_and_ignores_skip_markers() -> None:
    packet = Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=100,
        height=100,
        grid=bytes([8]) * 10000,
        header_calibration=Q10HeaderCalibration(0, 500, 5, -1, -1, 0),
        obstacles=[Q10Obstacle(2500, 500)],
        skip_cleaning_points=[Q10Point(100, 100)],
    )

    def render(drawables: list[Drawable], source: Q10MapPacket = packet) -> bytes:
        return render_q10_map(source, None, Q10MapOverlays(), config=B01Q10MapParserConfig(drawables=drawables))

    assert render([Drawable.OBSTACLES]) != render([])
    assert render([]) == render([], replace(packet, obstacles=[]))
    assert render([Drawable.OBSTACLES], replace(packet, obstacles=[])) == render([], replace(packet, obstacles=[]))


def test_resolve_current_room_valid_header_avoids_grid_decomposition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading the current room with a valid header only samples raw grid cells."""
    packet = replace(_packet(), header_calibration=HEADER)
    trace = Q10TracePacket(points=[Q10Point(100, 60)])

    def fail_decomposition(*args: object, **kwargs: object) -> None:
        pytest.fail("Current-room lookup decomposed the full occupancy grid")

    monkeypatch.setattr("roborock.map.b01_q10_map_parser.decompose_grid", fail_decomposition)
    assert resolve_q10_current_room(packet, trace) == packet.rooms[1]

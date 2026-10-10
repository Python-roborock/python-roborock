"""Compose a Q10 (B01/ss07) map into a single rendered result.

The :class:`~roborock.map.b01_q10_map_parser.B01Q10MapParser` turns wire bytes
into a :class:`~roborock.map.b01_q10_map_parser.Q10MapPacket`; this module
combines that map-protocol packet with the latest trace-protocol packet and DPS
overlay snapshot. Calibration, path and position are derived from those source
objects rather than managed independently by callers.

It exists so the map trait stays about state management: the trait accumulates
the pushed inputs and calls :func:`render_q10_map` once per change, holding the
returned image rather than mutating a pile of derived fields itself. All the
low-level pixel work (erase-zone blanking, world->pixel overlay placement, path
drawing) and the calibration policy live here, next to the rest of the map code.
"""

import io
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.map_data import Area, MapData, Obstacle, ObstacleDetails, Path, Point, Wall

from roborock.exceptions import RoborockException

from .b01_grid_layers import (
    GridCalibration,
    GridLayers,
    solve_calibration,
)
from .b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10EraseZone,
    Q10HistoricalTracePacket,
    Q10MapPacket,
    Q10Point,
    Q10Room,
    Q10TracePacket,
    erased_packet,
)
from .b01_q10_overlays import ZONE_TYPE_NO_GO, ZONE_TYPE_NO_MOP, Q10Zone
from .map_parser import DEFAULT_DRAWABLES, MapParserConfig, _create_image_generator

# Path-units-per-pixel candidates for packets without usable header metadata.
# A dense ss07 path lands a
# best fit of 20.0 around the header origin -- ground-truthed June 2026 on the
# R1: a corridor drive registered at 20 (matching the format author's
# independent "20 path-units/px"), and the dock->corridor span lined up with the
# ruler-measured 8.81 m corridor. With the header resolution=5 (50 mm/px grid)
# that makes one path-unit exactly 50/20 = 2.5 mm -- so a path-unit is NOT a
# millimetre (the open scale question). An earlier [10.0..18.0] range couldn't
# reach 20 (it railed at the bound), biasing the fit. A dense cleaning path
# selects the best fit within this bracket.
_Q10_RESOLUTIONS = [step * 0.5 for step in range(24, 53)]  # 12.0 .. 26.0
# The header resolution is expressed in centimetres per grid pixel, while
# erase/restriction vectors use 5 mm units: one header unit therefore equals
# two vector units. Trace points use a separate 2.5 mm coordinate scale.
_Q10_VECTOR_UNITS_PER_HEADER_RESOLUTION_UNIT = 2.0
# The grid header's resolution is centimetres per pixel, while live trace
# coordinates are 2.5 mm units. One header unit therefore spans four trace
# units (5 cm/pixel -> 20 trace units/pixel for the observed resolution 5).
_Q10_TRACE_UNITS_PER_HEADER_RESOLUTION_UNIT = 4.0
# A path needs enough shape to constrain a full (origin + resolution) fit; a few
# points cannot.
_MIN_CALIBRATION_POINTS = 20
_Q10_DRAWABLE_TYPES = {
    Drawable.CHARGER,
    Drawable.NO_GO_AREAS,
    Drawable.NO_MOPPING_AREAS,
    Drawable.OBSTACLES,
    Drawable.PATH,
    Drawable.VACUUM_POSITION,
    Drawable.VIRTUAL_WALLS,
}
_Q10_DRAWABLES = [drawable for drawable in DEFAULT_DRAWABLES if drawable in _Q10_DRAWABLE_TYPES]


@dataclass(frozen=True)
class Q10MapOverlays:
    """Latest decoded map-overlay values from the Q10 DPS stream."""

    zones: Sequence[Q10Zone] = ()
    virtual_walls: Sequence[Q10Zone] = ()


def render_q10_map(
    packet: Q10MapPacket,
    trace: Q10TracePacket | Q10HistoricalTracePacket | None,
    overlays: Q10MapOverlays,
    *,
    config: B01Q10MapParserConfig,
    robot_at_dock: bool = False,
) -> bytes:
    """Compose the latest map, trace and DPS inputs into one PNG image.

    Separate transforms are derived for 2.5 mm trace points and 5 mm
    erase/restriction vectors. Erase zones are blanked out of the raster, while
    available trace and DPS overlays are projected and drawn in pixel space.
    Raises :class:`RoborockException` if map rendering fails.
    """
    parser = B01Q10MapParser(config)
    trace_calibration = solve_q10_calibration(packet, trace)
    vector_calibration = _vector_calibration(packet, trace_calibration)

    render_packet = packet
    if vector_calibration is not None:
        cells = _erased_cells(packet.layers, packet.erase_zones, vector_calibration)
        if cells:
            # Blank the erase-zone cells before parsing the raster so phantom
            # areas disappear (as the app shows).
            render_packet = erased_packet(packet, cells)

    parsed = parser.parsed_from_packet(render_packet)
    if parsed.image_content is None or parsed.map_data is None:
        raise RoborockException("Failed to render Q10 map image")
    map_data = parsed.map_data

    has_drawables = _place_obstacles(map_data, packet)
    if trace_calibration is not None and trace is not None:
        charger_heading = packet.header_calibration.charger_phi if packet.header_calibration is not None else None
        _place_trace(map_data, trace_calibration, trace, charger_heading=charger_heading)
        has_drawables = True
    has_drawables = _place_charger_from_header(map_data, packet) or has_drawables
    if robot_at_dock:
        has_drawables = _place_docked_robot(map_data) or has_drawables
    if vector_calibration is not None:
        _place_overlays(map_data, vector_calibration, overlays)
        has_drawables = has_drawables or bool(map_data.no_go_areas or map_data.no_mopping_areas or map_data.walls)
    if has_drawables:
        return _draw_map_content(map_data, config=config)

    return parsed.image_content


def _obstacle_calibration(packet: Q10MapPacket) -> GridCalibration | None:
    """Build the obstacle-table transform from the map header.

    Q10 obstacle positions use 50 raw units per occupancy-grid pixel, unlike
    the 5 mm restriction vectors and 2.5 mm cleaning traces.
    """
    header = packet.header_calibration
    if header is None or (origin := header.origin_pixels()) is None:
        return None
    return GridCalibration(resolution=50.0, origin_x=origin[0], origin_y=origin[1], y_sign=1)


def _place_obstacles(map_data: MapData, packet: Q10MapPacket) -> bool:
    """Project position-only Q10 obstacle markers into shared ``MapData``."""
    calibration = _obstacle_calibration(packet)
    if calibration is None or not packet.obstacles:
        return False
    map_data.obstacles = [
        Obstacle(*calibration.world_to_pixel(obstacle.x, obstacle.y), ObstacleDetails())
        for obstacle in packet.obstacles
    ]
    return True


def solve_q10_calibration(
    packet: Q10MapPacket,
    trace: Q10TracePacket | Q10HistoricalTracePacket | None,
) -> GridCalibration | None:
    """Derive world-to-pixel calibration from a map and its current trace.

    When the map packet carries usable ss07 header metadata, its fixed origin
    and resolution are authoritative and work from the first live pose. Older
    or incomplete packets fall back to a full origin/resolution fit, which needs
    a reasonably dense cleaning path. Returns ``None`` when neither is usable.
    """
    if trace is None or not trace.points:
        return None
    if calibration := _trace_calibration_from_header_metadata(packet, trace.points):
        return calibration
    points: list[tuple[float, float]] = [(point.x, point.y) for point in trace.points]
    return _calibration_from_fit(packet.layers, points)


def _trace_calibration_from_header_metadata(
    packet: Q10MapPacket,
    points: Sequence[Q10Point],
) -> GridCalibration | None:
    """Build the live-trace transform directly from validated header metadata."""
    header = packet.header_calibration
    if header is None or header.resolution <= 0 or (origin := header.origin_pixels()) is None:
        return None
    resolution = header.resolution * _Q10_TRACE_UNITS_PER_HEADER_RESOLUTION_UNIT
    if not min(_Q10_RESOLUTIONS) <= resolution <= max(_Q10_RESOLUTIONS):
        return None
    calibration = GridCalibration(
        resolution=resolution,
        origin_x=origin[0],
        origin_y=origin[1],
        y_sign=1,
    )
    return calibration if _trace_projects_onto_floor(packet.layers, points, calibration) else None


def _trace_projects_onto_floor(
    layers: GridLayers,
    points: Sequence[Q10Point],
    calibration: GridCalibration,
) -> bool:
    """Validate header calibration against a bounded sample of trace points."""
    if not points:
        return False
    stride = max(1, len(points) // 256)
    sample = points[::stride]
    on_floor = 0
    for point in sample:
        pixel_x, pixel_y = calibration.world_to_pixel(point.x, point.y)
        if not math.isfinite(pixel_x) or not math.isfinite(pixel_y):
            continue
        column, row = math.floor(pixel_x), math.floor(pixel_y)
        if not (0 <= column < layers.width and 0 <= row < layers.height):
            continue
        if layers.cell_class(layers.grid[row * layers.width + column]) == "floor":
            on_floor += 1
    return on_floor >= len(sample) * 0.5


def _room_at_position(
    packet: Q10MapPacket,
    position: Q10Point,
    calibration: GridCalibration,
    *,
    search_radius: int = 2,
) -> Q10Room | None:
    """Resolve a live position to a segmented room in the occupancy grid.

    The exact cell wins. A robot centre can briefly land on a wall or doorway
    pixel, so a small expanding neighbourhood is used only when the exact cell
    is not segmented. Ambiguous ties stay unknown rather than naming the wrong
    room.
    """
    pixel_x, pixel_y = calibration.world_to_pixel(position.x, position.y)
    if not math.isfinite(pixel_x) or not math.isfinite(pixel_y):
        return None
    column, row = math.floor(pixel_x), math.floor(pixel_y)
    if not (0 <= column < packet.width and 0 <= row < packet.height):
        return None

    rooms_by_value = {room.pixel_value: room for room in packet.rooms}

    def room_at(column: int, row: int) -> Q10Room | None:
        if not (0 <= column < packet.width and 0 <= row < packet.height):
            return None
        return rooms_by_value.get(packet.grid[row * packet.width + column])

    if room := room_at(column, row):
        return room

    for radius in range(1, max(0, search_radius) + 1):
        room_ids = {
            candidate.id
            for nearby_row in range(row - radius, row + radius + 1)
            for nearby_column in range(column - radius, column + radius + 1)
            if (candidate := room_at(nearby_column, nearby_row)) is not None
        }
        if not room_ids:
            continue
        if len(room_ids) != 1:
            return None
        room_id = room_ids.pop()
        return next((room for room in packet.rooms if room.id == room_id), None)
    return None


def resolve_q10_current_room(packet: Q10MapPacket, trace: Q10TracePacket | None) -> Q10Room | None:
    """Infer the robot's current room from its latest live pose and map grid.

    No authoritative active-segment field has been identified or observed on
    ss07 firmware. The live trace's final point is the robot pose, and the full
    map labels every segmented floor cell. Header metadata supplies the fixed
    transform from trace coordinates to that grid; older/incomplete packets
    fall back to the path-fit calibration used by rendering.
    """
    if trace is None or (position := trace.robot_position) is None:
        return None
    calibration = solve_q10_calibration(packet, trace)
    if calibration is None:
        return None
    room = _room_at_position(packet, position, calibration)
    return replace(room) if room is not None else None


def _calibration_from_header_metadata(
    packet: Q10MapPacket,
    *,
    y_sign: int = 1,
) -> GridCalibration | None:
    """Build the vector transform directly from a usable map header."""
    header = packet.header_calibration
    if header is None or header.resolution <= 0 or (origin := header.origin_pixels()) is None:
        return None
    return GridCalibration(
        resolution=header.resolution * _Q10_VECTOR_UNITS_PER_HEADER_RESOLUTION_UNIT,
        origin_x=origin[0],
        origin_y=origin[1],
        y_sign=y_sign,
    )


def _vector_calibration(
    packet: Q10MapPacket,
    trace_calibration: GridCalibration | None,
) -> GridCalibration | None:
    """Derive the 5 mm erase/restriction-vector transform."""
    # Header vectors share the map packet's fixed top-down coordinate frame.
    # A trace fit may choose either Y orientation, but that must not move saved
    # erase/restriction geometry when a cleaning trace appears or disappears.
    if calibration := _calibration_from_header_metadata(packet):
        return calibration
    if trace_calibration is None:
        return None
    return GridCalibration(
        resolution=trace_calibration.resolution / 2,
        origin_x=trace_calibration.origin_x,
        origin_y=trace_calibration.origin_y,
        y_sign=trace_calibration.y_sign,
    )


def _calibration_from_fit(layers: GridLayers, points: list[tuple[float, float]]) -> GridCalibration | None:
    """Full origin + resolution fit; needs a reasonably dense path."""
    if len(points) < _MIN_CALIBRATION_POINTS:
        return None
    return solve_calibration(layers, points, resolutions=_Q10_RESOLUTIONS)


def _erased_cells(
    layers: GridLayers,
    erase_zones: Sequence[Q10EraseZone],
    calibration: GridCalibration,
) -> set[int]:
    """Grid-cell indices covered by the erase zones (axis-aligned bbox fill)."""
    if not erase_zones:
        return set()
    width, height = layers.width, layers.height
    cells: set[int] = set()
    for zone in erase_zones:
        pixels = [calibration.world_to_pixel(x, y) for x, y in zone.vertices]
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        for py in range(max(0, y0), min(height, y1 + 1)):
            for px in range(max(0, x0), min(width, x1 + 1)):
                cells.add(py * width + px)
    return cells


def _place_trace(
    map_data: MapData,
    calibration: GridCalibration,
    trace: Q10TracePacket | Q10HistoricalTracePacket,
    *,
    charger_heading: int | None = None,
) -> None:
    """Project trace path, position, heading and charger into pixel space.

    Points are stored in grid-pixel space (origin top-left), matching the Q10's
    top-down, un-flipped raster so they line up with the rendered image.
    """
    pixels = [Point(*calibration.world_to_pixel(point.x, point.y)) for point in trace.points]
    map_data.path = Path(len(pixels), 1, 0, [pixels])
    robot_position = trace.robot_position
    if robot_position is not None:
        px, py = calibration.world_to_pixel(robot_position.x, robot_position.y)
        # The shared V1 marker expects a map-space heading (+Y is up), not the
        # top-down PNG angle previously used by Q10's custom marker.
        map_data.vacuum_position = Point(px, py, calibration.y_sign * trace.heading)
    if pixels:
        map_data.charger = Point(
            pixels[0].x,
            pixels[0].y,
            calibration.y_sign * charger_heading if charger_heading is not None else None,
        )


def _place_charger_from_header(
    map_data: MapData,
    packet: Q10MapPacket,
) -> bool:
    """Place the saved dock using its absolute header pixel coordinates."""
    header = packet.header_calibration
    if header is None or (position := header.charger_pixels()) is None:
        return False
    map_data.charger = Point(*position, header.charger_phi)
    return True


def _place_docked_robot(map_data: MapData) -> bool:
    """Place a charging robot immediately in front of the saved dock.

    A zero-point idle trace has no robot coordinates. The dock heading does,
    however, identify its outward-facing side. Offset the robot by the shared
    unscaled V1 charger radius so the two standard glyphs meet without one
    covering the other, and preserve the saved dock heading.
    """
    charger = map_data.charger
    if charger is None or charger.a is None:
        return False
    angle = math.radians(charger.a)
    offset = Sizes.SIZES[Size.CHARGER_RADIUS]
    map_data.vacuum_position = Point(
        charger.x + offset * math.cos(angle),
        charger.y - offset * math.sin(angle),
        charger.a,
    )
    return True


def _place_overlays(
    map_data: MapData,
    calibration: GridCalibration,
    overlays: Q10MapOverlays,
) -> None:
    """Convert world-coordinate zones/walls into pixel-space ``MapData`` layers."""

    def to_area(zone: Q10Zone) -> Area | None:
        if len(zone.vertices) != 4:
            return None  # MapData.Area is a quad
        pts = [calibration.world_to_pixel(x, y) for x, y in zone.vertices]
        return Area(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], pts[3][0], pts[3][1])

    no_go = [area for zone in overlays.zones if zone.type == ZONE_TYPE_NO_GO and (area := to_area(zone))]
    no_mop = [area for zone in overlays.zones if zone.type == ZONE_TYPE_NO_MOP and (area := to_area(zone))]
    map_data.no_go_areas = no_go or None
    map_data.no_mopping_areas = no_mop or None

    walls: list[Wall] = []
    for zone in overlays.virtual_walls:
        if len(zone.vertices) >= 2:
            (x0, y0), (x1, y1) = zone.vertices[0], zone.vertices[1]
            p0 = calibration.world_to_pixel(x0, y0)
            p1 = calibration.world_to_pixel(x1, y1)
            walls.append(Wall(p0[0], p0[1], p1[0], p1[1]))
    map_data.walls = walls or None


def _draw_map_content(
    map_data: MapData,
    *,
    config: B01Q10MapParserConfig,
) -> bytes:
    """Draw Q10 content with the shared V1 image generator."""
    if map_data.image is None:
        raise RoborockException("Failed to render Q10 map image")
    drawables = (
        _Q10_DRAWABLES if config.drawables is None else [d for d in config.drawables if d in _Q10_DRAWABLE_TYPES]
    )
    generator = _create_image_generator(MapParserConfig(map_scale=config.map_scale), drawables=drawables)
    generator.draw_map(map_data)
    buffer = io.BytesIO()
    map_data.image.data.save(buffer, format="PNG")
    return buffer.getvalue()

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
from dataclasses import dataclass

from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.map_data import Area, MapData, Path, Point, Wall

from roborock.exceptions import RoborockException

from .b01_grid_layers import (
    GridCalibration,
    GridLayers,
    solve_calibration,
    solve_calibration_with_origin,
)
from .b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10EraseZone,
    Q10HistoricalTracePacket,
    Q10MapPacket,
    Q10TracePacket,
    erased_packet,
)
from .b01_q10_overlays import ZONE_TYPE_NO_GO, ZONE_TYPE_NO_MOP, Q10Zone
from .map_parser import DEFAULT_DRAWABLES, MapParserConfig, _create_image_generator

# Path-units-per-pixel candidates for calibration. A dense ss07 path lands a
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
# A path needs enough shape to constrain a full (origin + resolution) fit; a few
# points cannot.
_MIN_CALIBRATION_POINTS = 20
# When the grid-frame header supplies the origin, only the resolution is fit, so
# a much shorter path suffices to confirm it (early in a clean, not just a dense
# one). See :func:`solve_calibration_with_origin`.
_MIN_HEADER_CALIBRATION_POINTS = 4
_Q10_DRAWABLE_TYPES = {
    Drawable.CHARGER,
    Drawable.NO_GO_AREAS,
    Drawable.NO_MOPPING_AREAS,
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

    has_drawables = False
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


def solve_q10_calibration(
    packet: Q10MapPacket,
    trace: Q10TracePacket | Q10HistoricalTracePacket | None,
) -> GridCalibration | None:
    """Derive world-to-pixel calibration from a map and its current trace.

    When the map packet's grid-frame header carries a calibration origin (ss07),
    only the resolution is fit -- around that fixed origin -- so a short path
    suffices and the origin is exact rather than recovered by a slide. Otherwise
    the full origin + resolution fit is used, which needs a reasonably dense
    cleaning path. Returns ``None`` if the path is too short/featureless to fit.
    """
    if trace is None:
        return None
    points: list[tuple[float, float]] = [(point.x, point.y) for point in trace.points]
    return _calibration_from_header(packet, points) or _calibration_from_fit(packet.layers, points)


def _calibration_from_header(
    packet: Q10MapPacket,
    points: list[tuple[float, float]],
) -> GridCalibration | None:
    """Calibrate around the header-supplied origin (resolution fit to a path)."""
    header_calibration = packet.header_calibration
    if header_calibration is None or len(points) < _MIN_HEADER_CALIBRATION_POINTS:
        return None
    origin = header_calibration.origin_pixels()
    if origin is None:  # keepalive frame -- no usable origin
        return None
    return solve_calibration_with_origin(packet.layers, points, origin, resolutions=_Q10_RESOLUTIONS)


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
    generator = _create_image_generator(
        MapParserConfig(map_scale=config.map_scale),
        drawables=_Q10_DRAWABLES,
    )
    generator.draw_map(map_data)
    buffer = io.BytesIO()
    map_data.image.data.save(buffer, format="PNG")
    return buffer.getvalue()

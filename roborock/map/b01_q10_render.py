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

from PIL import Image, ImageDraw
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
    Q10MapPacket,
    Q10TracePacket,
    erased_packet,
)
from .b01_q10_overlays import ZONE_TYPE_NO_GO, ZONE_TYPE_NO_MOP, Q10Zone

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
# A path needs enough shape to constrain a full (origin + resolution) fit; a few
# points cannot.
_MIN_CALIBRATION_POINTS = 20
# When the grid-frame header supplies the origin, only the resolution is fit, so
# a much shorter path suffices to confirm it (early in a clean, not just a dense
# one). See :func:`solve_calibration_with_origin`.
_MIN_HEADER_CALIBRATION_POINTS = 4


@dataclass(frozen=True)
class Q10MapOverlays:
    """Latest decoded map-overlay values from the Q10 DPS stream."""

    zones: Sequence[Q10Zone] = ()
    virtual_walls: Sequence[Q10Zone] = ()


def render_q10_map(
    packet: Q10MapPacket,
    trace: Q10TracePacket | None,
    overlays: Q10MapOverlays,
    *,
    config: B01Q10MapParserConfig,
) -> bytes:
    """Compose the latest map, trace and DPS inputs into one PNG image.

    Calibration is derived from ``packet`` (layers + header calibration) and
    ``trace`` (path points). Once calibrated, erase zones are blanked out of the
    raster and trace/overlay data is projected and drawn in pixel space.
    Without a usable trace only the base raster is rendered. Raises
    :class:`RoborockException` if map rendering fails.
    """
    parser = B01Q10MapParser(config)
    calibration = solve_q10_calibration(packet, trace)

    render_packet = packet
    if calibration is not None:
        cells = _erased_cells(packet.layers, packet.erase_zones, calibration)
        if cells:
            # Blank the erase-zone cells before parsing the raster so phantom
            # areas disappear (as the app shows).
            render_packet = erased_packet(packet, cells)

    parsed = parser.parsed_from_packet(render_packet)
    if parsed.image_content is None or parsed.map_data is None:
        raise RoborockException("Failed to render Q10 map image")
    map_data = parsed.map_data

    if calibration is not None and trace is not None:
        _place_trace(map_data, calibration, trace)
        _place_overlays(map_data, calibration, overlays)
        return _draw_map_content(parsed.image_content, map_data, config=config)

    return parsed.image_content


def solve_q10_calibration(
    packet: Q10MapPacket,
    trace: Q10TracePacket | None,
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
    trace: Q10TracePacket,
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
        # Store the heading in projected image coordinates so drawing does not
        # need to retain the world-to-pixel calibration.
        map_data.vacuum_position = Point(px, py, -calibration.y_sign * trace.heading)
    if pixels:
        map_data.charger = pixels[0]


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
    image_content: bytes,
    map_data: MapData,
    *,
    config: B01Q10MapParserConfig,
    line_color: tuple[int, int, int, int] = (235, 64, 52, 255),
    position_color: tuple[int, int, int, int] = (255, 211, 0, 255),
) -> bytes:
    """Draw projected map content onto a base PNG and return a fresh PNG."""
    scale = config.map_scale
    base = Image.open(io.BytesIO(image_content)).convert("RGBA")

    def to_image(point: Point) -> tuple[float, float]:
        return (point.x * scale, point.y * scale)

    draw = ImageDraw.Draw(base, "RGBA")

    # Erase zones are applied to the raster itself (cells blanked), so they are
    # not drawn here -- the base image already reflects them.

    # No-go (blue) and no-mop (magenta) zones beneath the path.
    for areas, fill, outline in (
        (map_data.no_go_areas or [], (0, 120, 255, 70), (0, 80, 200, 255)),
        (map_data.no_mopping_areas or [], (255, 0, 200, 70), (200, 0, 160, 255)),
    ):
        for area in areas:
            polygon = [
                (area.x0 * scale, area.y0 * scale),
                (area.x1 * scale, area.y1 * scale),
                (area.x2 * scale, area.y2 * scale),
                (area.x3 * scale, area.y3 * scale),
            ]
            draw.polygon(polygon, fill=fill, outline=outline)

    # Virtual walls (line segments, not polygons) drawn over the zones.
    for wall in map_data.walls or []:
        draw.line(
            [(wall.x0 * scale, wall.y0 * scale), (wall.x1 * scale, wall.y1 * scale)],
            fill=(255, 64, 64, 255),
            width=max(2, scale),
        )

    for path in map_data.path.path if map_data.path else []:
        if len(path) >= 2:
            draw.line([to_image(point) for point in path], fill=line_color, width=max(1, scale // 2))
    if map_data.charger is not None:
        dx, dy = to_image(map_data.charger)
        draw.ellipse([dx - scale, dy - scale, dx + scale, dy + scale], outline=(40, 200, 40, 255), width=2)
    robot_position = map_data.vacuum_position
    if robot_position is not None:
        cx, cy = to_image(robot_position)
        radius = scale
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=position_color)
        robot_heading = robot_position.a
        if robot_heading is not None:
            # Heading was projected into image coordinates alongside the robot
            # position, so no calibration state is needed during drawing.
            angle = math.radians(robot_heading)
            tick = 4 * radius
            draw.line(
                [cx, cy, cx + math.cos(angle) * tick, cy + math.sin(angle) * tick],
                fill=position_color,
                width=max(1, scale // 2),
            )
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    return buffer.getvalue()

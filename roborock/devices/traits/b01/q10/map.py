"""Map content trait for B01 Q10 devices.

Unlike the v1 / Q7 maps, the Q10 has no synchronous "get map" command, so this
trait is purely push-driven and mirrors the Q10 ``StatusTrait`` contract:

- The device pushes its current map/path as protocol-301 ``MAP_RESPONSE``
  messages (a ``dpRequestDps`` nudges it to do so). The protocol layer decodes
  each push into a typed :class:`~roborock.map.b01_q10_map_parser.Q10MapPacket`
  or :class:`~roborock.map.b01_q10_map_parser.Q10TracePacket`, and the
  ``Q10PropertiesApi`` subscribe loop routes those to
  :meth:`MapContentTrait.update_from_map_packet` /
  :meth:`MapContentTrait.update_from_trace_packet`.
- Those methods render/cache the packet, update the cached fields and notify
  update listeners (register via :meth:`add_update_listener`).
- ``parse_map_content()`` re-renders the cached map packet without I/O (e.g.
  after the calibration changed).
- ``image_content``, ``map_data``, ``rooms``, ``path`` and ``robot_position``
  are readable and reflect the most recently pushed map.

Unlike the Q7, the Q10 map payload is unencrypted, so no map key is required.
"""

import io
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageDraw
from vacuum_map_parser_base.map_data import Area, MapData, Path, Point, Wall

from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.common import TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.map.b01_grid_layers import (
    GridCalibration,
    GridLayers,
    solve_calibration,
    solve_calibration_with_origin,
)
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10EraseZone,
    Q10HeaderCalibration,
    Q10MapPacket,
    Q10Point,
    Q10Room,
    Q10TracePacket,
    decompose_layers,
    erased_packet,
)
from roborock.map.b01_q10_overlays import (
    ZONE_TYPE_NO_GO,
    ZONE_TYPE_NO_MOP,
    Q10Zone,
    parse_virtual_wall_blob,
    parse_zone_blob,
)

_LOGGER = logging.getLogger(__name__)

_TRUNCATE_LENGTH = 20

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


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing Q10 map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """Parsed map data (image metadata + room names)."""

    rooms: list[Q10Room] = field(default_factory=list)
    """Rooms (segments) reported by the device, with ids and names."""

    layers: GridLayers | None = None
    """Separable map layers (background / wall / floor / per-room) in grid-pixel
    space, each renderable to a transparent PNG for frontend compositing."""

    path: list[Q10Point] = field(default_factory=list)
    """Full path of the current cleaning session (oldest point first).

    The robot accumulates this server-side and serves the whole trajectory so
    far in one packet, so it is complete even if we connect mid-session. Only
    populated while a cleaning session is active."""

    robot_position: Q10Point | None = None
    """Current robot position (the most recent path point), if known."""

    robot_heading: int | None = None
    """Current robot heading in degrees from the trace packet (``0`` = +x,
    ``+90`` = +y, ``±180`` = −x, ``−90`` = −y), if a trace has been pushed."""

    calibration: GridCalibration | None = None
    """World<->pixel transform, solved from a cleaning path (see
    :meth:`MapContentTrait.solve_calibration`). Required to place the path,
    robot position and vector overlays onto the map raster."""

    zones: list[Q10Zone] = field(default_factory=list)
    """Restricted zones (no-go / no-mop) in world coordinates, from the device's
    ``dpRestrictedZoneUp``. See :meth:`MapContentTrait.load_overlays`."""

    virtual_walls: list[Q10Zone] = field(default_factory=list)
    """Virtual walls (line segments) in world coordinates."""

    erase_zones: list[Q10EraseZone] = field(default_factory=list)
    """Erase areas (the app's *Erase* tool) in world coordinates, decoded from the
    map packet tail. Once a calibration is available the cells inside them are
    blanked from the rendered map and every layer (see :meth:`MapContentTrait`)."""

    header_calibration: Q10HeaderCalibration | None = None
    """Calibration read straight from the map packet's grid-frame header (ss07).
    Supplies the world<->pixel origin without a fit, so :meth:`solve_calibration`
    can calibrate from a short path instead of a dense clean. ``None`` if the
    packet carried no header calibration or it was a keepalive frame."""

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, rooms={self.rooms!r})"


class MapContentTrait(MapContent, TraitUpdateListener):
    """Trait holding the most recently pushed parsed map content for Q10 devices.

    The Q10 has no synchronous get-map request; the device pushes map and trace
    packets, which the protocol layer decodes into typed packets and the
    ``Q10PropertiesApi`` subscribe loop feeds into :meth:`update_from_map_packet`
    / :meth:`update_from_trace_packet`. Consumers read the cached fields and/or
    register a callback with :meth:`add_update_listener` to be notified when new
    map content arrives.
    """

    def __init__(
        self,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._map_parser = B01Q10MapParser(map_parser_config)
        # The most recently pushed (parsed) map packet, cached so the map can be
        # re-rendered (e.g. to apply erase zones / overlays once a calibration is
        # known) without re-parsing wire bytes.
        self._packet: Q10MapPacket | None = None

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Render a pushed full-map packet into the cached image/rooms/layers.

        Rendering failures are logged and skipped (listeners are not notified) so
        a single bad push cannot tear down the subscribe loop.
        """
        try:
            self._render_packet(packet)
        except RoborockException as ex:
            _LOGGER.debug("Failed to render Q10 map packet: %s", ex)
            return
        self._notify_update()

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Cache the path / robot position / heading from a pushed trace packet."""
        self.path = packet.points
        self.robot_position = packet.robot_position
        self.robot_heading = packet.heading
        self._notify_update()

    def parse_map_content(self) -> None:
        """Re-render the cached map packet without performing any I/O.

        Used to refresh the rendered image / ``map_data`` after the calibration
        changed (so the path, overlays and erase zones are reapplied)."""
        if self._packet is None:
            raise RoborockException("No map payload available; no map has been pushed yet")
        self._render_packet(self._packet)

    def _render_packet(self, packet: Q10MapPacket) -> None:
        """Render a parsed map packet into the cached image / map_data / layers."""
        try:
            parsed = self._map_parser.parsed_from_packet(packet)
        except RoborockException:
            raise
        except Exception as ex:
            raise RoborockException("Failed to parse Q10 map data") from ex

        if parsed.image_content is None:
            raise RoborockException("Failed to render Q10 map image")

        self._packet = packet
        self.image_content = parsed.image_content
        self.map_data = parsed.map_data
        self.rooms = packet.rooms
        self.erase_zones = packet.erase_zones
        self.header_calibration = packet.header_calibration
        self.layers = decompose_layers(packet)
        if self.calibration is not None:
            self._apply_erase(self.calibration)
            self._populate_map_data_overlays(self.calibration)
            self._place_zones_on_map_data(self.calibration)

    def solve_calibration(self) -> GridCalibration | None:
        """Fit and cache the world<->pixel calibration from the current path.

        When the map packet's grid-frame header carries a calibration origin
        (ss07), only the resolution is fit -- around that fixed origin -- so a
        short path suffices and the origin is exact rather than recovered by a
        slide. Otherwise the full origin + resolution fit is used, which needs a
        reasonably dense cleaning path. Both inputs arrive as device pushes (the
        path is only populated during an active clean). Returns the calibration
        (also stored on :attr:`calibration`), or ``None`` if there is no map or
        the path is too short/featureless to fit.
        """
        if self.layers is None:
            return None
        points: list[tuple[float, float]] = [(point.x, point.y) for point in self.path]
        calibration = self._calibration_from_header(points) or self._calibration_from_fit(points)
        if calibration is not None:
            self.calibration = calibration
            self._apply_erase(calibration)
            self._populate_map_data_overlays(calibration)
            self._place_zones_on_map_data(calibration)
        return calibration

    def _calibration_from_header(self, points: list[tuple[float, float]]) -> GridCalibration | None:
        """Calibrate around the header-supplied origin (resolution fit to a path)."""
        if self.layers is None or self.header_calibration is None or len(points) < _MIN_HEADER_CALIBRATION_POINTS:
            return None
        origin = self.header_calibration.origin_pixels()
        if origin is None:  # keepalive frame -- no usable origin
            return None
        return solve_calibration_with_origin(self.layers, points, origin, resolutions=_Q10_RESOLUTIONS)

    def _calibration_from_fit(self, points: list[tuple[float, float]]) -> GridCalibration | None:
        """Full origin + resolution fit; needs a reasonably dense path."""
        if self.layers is None or len(points) < _MIN_CALIBRATION_POINTS:
            return None
        return solve_calibration(self.layers, points, resolutions=_Q10_RESOLUTIONS)

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Decode any vector-overlay data points present in a DPS push.

        The Q10 pushes no-go / no-mop zones (``dpRestrictedZoneUp``) and virtual
        walls (``dpVirtualWallUp``) as status data points rather than inside the
        map packet, so the map trait joins the ``Q10PropertiesApi`` DPS fan-out
        like the other read-model traits instead of being special-cased by the
        orchestrator. Data points absent from this push leave the existing
        overlays untouched (a partial status push must not wipe them); a push
        carrying neither is a no-op.
        """
        if B01_Q10_DP.RESTRICTED_ZONE_UP not in decoded_dps and B01_Q10_DP.VIRTUAL_WALL_UP not in decoded_dps:
            return
        self.load_overlays(
            restricted_zone_up=decoded_dps.get(B01_Q10_DP.RESTRICTED_ZONE_UP),
            virtual_wall_up=decoded_dps.get(B01_Q10_DP.VIRTUAL_WALL_UP),
        )
        self._notify_update()

    def load_overlays(
        self,
        *,
        restricted_zone_up: bytes | str | None = None,
        virtual_wall_up: bytes | str | None = None,
    ) -> None:
        """Decode the device's vector-overlay blobs (from the status DPs).

        Pass the raw ``dpRestrictedZoneUp`` / ``dpVirtualWallUp`` values
        (``Q10Status.restricted_zone_up`` / ``virtual_wall_up``). Stores them as
        world-coordinate :attr:`zones` / :attr:`virtual_walls`, and -- if a
        calibration is available -- places them onto ``map_data`` as
        ``no_go_areas`` / ``no_mopping_areas`` / ``walls`` in pixel space.

        ``None`` means "data point absent from this update" and leaves the
        existing value untouched (a partial status push must not wipe overlays).
        An explicit empty blob does clear them.
        """
        if restricted_zone_up is not None:
            self.zones = parse_zone_blob(restricted_zone_up)
        if virtual_wall_up is not None:
            self.virtual_walls = parse_virtual_wall_blob(virtual_wall_up)
        if self.calibration is not None:
            self._place_zones_on_map_data(self.calibration)

    def _place_zones_on_map_data(self, calibration: GridCalibration) -> None:
        """Convert world-coordinate zones/walls into pixel-space MapData layers."""
        if self.map_data is None:
            return

        def to_area(zone: Q10Zone) -> Area | None:
            if len(zone.vertices) != 4:
                return None  # MapData.Area is a quad
            pts = [calibration.world_to_pixel(x, y) for x, y in zone.vertices]
            return Area(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], pts[3][0], pts[3][1])

        no_go = [area for zone in self.zones if zone.type == ZONE_TYPE_NO_GO and (area := to_area(zone))]
        no_mop = [area for zone in self.zones if zone.type == ZONE_TYPE_NO_MOP and (area := to_area(zone))]
        self.map_data.no_go_areas = no_go or None
        self.map_data.no_mopping_areas = no_mop or None

        walls: list[Wall] = []
        for zone in self.virtual_walls:
            if len(zone.vertices) >= 2:
                (x0, y0), (x1, y1) = zone.vertices[0], zone.vertices[1]
                p0 = calibration.world_to_pixel(x0, y0)
                p1 = calibration.world_to_pixel(x1, y1)
                walls.append(Wall(p0[0], p0[1], p1[0], p1[1]))
        self.map_data.walls = walls or None

        # The robot starts a session at its dock, so the path origin is the charger.
        if self.path:
            cx, cy = calibration.world_to_pixel(self.path[0].x, self.path[0].y)
            self.map_data.charger = Point(cx, cy)

    def _erased_cells(self, calibration: GridCalibration) -> set[int]:
        """Grid-cell indices covered by the erase zones (axis-aligned bbox fill)."""
        if not self.erase_zones or self.layers is None:
            return set()
        width, height = self.layers.width, self.layers.height
        cells: set[int] = set()
        for zone in self.erase_zones:
            pixels = [calibration.world_to_pixel(x, y) for x, y in zone.vertices]
            xs = [p[0] for p in pixels]
            ys = [p[1] for p in pixels]
            x0, x1 = int(min(xs)), int(max(xs))
            y0, y1 = int(min(ys)), int(max(ys))
            for py in range(max(0, y0), min(height, y1 + 1)):
                for px in range(max(0, x0), min(width, x1 + 1)):
                    cells.add(py * width + px)
        return cells

    def _apply_erase(self, calibration: GridCalibration) -> None:
        """Blank erase-zone cells out of the rendered map, layers, and ``map_data``.

        The erase rectangles are world-coordinate areas the user marked for removal
        (e.g. phantom floor seen through windows). With a calibration we can place
        them in pixel space, blank those cells to background, and re-render so the
        phantom areas disappear -- matching what the app shows.
        """
        if self.layers is None or self._packet is None:
            return
        cells = self._erased_cells(calibration)
        if not cells:
            return
        packet = erased_packet(self._packet, cells)
        parsed = self._map_parser.parsed_from_packet(packet)
        self.image_content = parsed.image_content
        self.map_data = parsed.map_data
        self.layers = decompose_layers(packet)

    def _populate_map_data_overlays(self, calibration: GridCalibration) -> None:
        """Fill MapData.path / vacuum_position in grid-pixel coords.

        Points are stored in grid-pixel space (origin top-left), matching the
        Q10's top-down, un-flipped raster so they line up with the rendered image.
        """
        if self.map_data is None:
            return
        pixels = [Point(*calibration.world_to_pixel(point.x, point.y)) for point in self.path]
        self.map_data.path = Path(len(pixels), 1, 0, [pixels])
        if self.robot_position is not None:
            px, py = calibration.world_to_pixel(self.robot_position.x, self.robot_position.y)
            self.map_data.vacuum_position = Point(px, py)

    def render_path_on_map(
        self,
        *,
        line_color: tuple[int, int, int, int] = (235, 64, 52, 255),
        position_color: tuple[int, int, int, int] = (255, 211, 0, 255),
    ) -> bytes:
        """Return the map image (PNG) with the session path + robot position drawn.

        Solves the calibration on demand if not already cached. Raises
        :class:`RoborockException` if there is no map, or no calibration can be
        fitted (e.g. no cleaning path captured yet).
        """
        if self.image_content is None or self.layers is None:
            raise RoborockException("No map available; no map has been pushed yet")
        calibration = self.calibration or self.solve_calibration()
        if calibration is None:
            raise RoborockException(
                "No calibration available; a cleaning path must be captured (pushed) during a clean"
            )

        scale = self._map_parser.config.map_scale
        base = Image.open(io.BytesIO(self.image_content)).convert("RGBA")

        def world_to_image(x: float, y: float) -> tuple[float, float]:
            px, py = calibration.world_to_pixel(x, y)
            # The ss07 grid renders top-down (no flip), so grid-pixel (px, py) maps
            # straight to image space, only upscaled by ``scale``.
            return (px * scale, py * scale)

        def to_image(point: Q10Point) -> tuple[float, float]:
            return world_to_image(point.x, point.y)

        draw = ImageDraw.Draw(base, "RGBA")

        # Erase zones are applied to the raster itself (cells blanked), so they are
        # not drawn here -- the base image already reflects them.

        # No-go (blue) and no-mop (magenta) zones beneath the path.
        for zone in self.zones:
            if len(zone.vertices) < 3:
                continue
            polygon = [world_to_image(x, y) for x, y in zone.vertices]
            fill = (0, 120, 255, 70) if zone.type == ZONE_TYPE_NO_GO else (255, 0, 200, 70)
            outline = (0, 80, 200, 255) if zone.type == ZONE_TYPE_NO_GO else (200, 0, 160, 255)
            draw.polygon(polygon, fill=fill, outline=outline)

        # Virtual walls (line segments, not polygons) drawn over the zones.
        for wall in self.virtual_walls:
            if len(wall.vertices) < 2:
                continue
            draw.line(
                [world_to_image(x, y) for x, y in wall.vertices[:2]],
                fill=(255, 64, 64, 255),
                width=max(2, scale),
            )

        if len(self.path) >= 2:
            draw.line([to_image(point) for point in self.path], fill=line_color, width=max(1, scale // 2))
        if self.path:  # path origin == dock / charger
            dx, dy = to_image(self.path[0])
            draw.ellipse([dx - scale, dy - scale, dx + scale, dy + scale], outline=(40, 200, 40, 255), width=2)
        if self.robot_position is not None:
            cx, cy = to_image(self.robot_position)
            radius = scale
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=position_color)
            if self.robot_heading is not None:
                # Heading is world-space degrees (0 = +x, +90 = +y). Map a unit
                # world-space facing vector through the same transform (so the
                # Y-flip/scale match the marker), then normalize to a fixed
                # pixel-length tick so it reads at any calibration resolution.
                angle = math.radians(self.robot_heading)
                hx, hy = world_to_image(
                    self.robot_position.x + math.cos(angle),
                    self.robot_position.y + math.sin(angle),
                )
                norm = math.hypot(hx - cx, hy - cy)
                if norm > 0:
                    tick = 4 * radius
                    draw.line(
                        [cx, cy, cx + (hx - cx) / norm * tick, cy + (hy - cy) / norm * tick],
                        fill=position_color,
                        width=max(1, scale // 2),
                    )
        buffer = io.BytesIO()
        base.save(buffer, format="PNG")
        return buffer.getvalue()

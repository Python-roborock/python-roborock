"""Module for parsing B01/Q7 map content.

The inner SCMap blob is parsed with protobuf messages generated from
`roborock/map/proto/b01_scmap.proto`.
"""

import io
import math
from collections import deque
from dataclasses import dataclass

from google.protobuf.message import DecodeError
from PIL import Image
from vacuum_map_parser_base.config.color import ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import Area, ImageData, MapData, Path, Point, Room

from roborock.exceptions import RoborockException
from roborock.map.proto.b01_scmap_pb2 import RobotMap  # type: ignore[attr-defined]

from .map_parser import MapParserConfig, ParsedMapData, _create_image_generator
from .room_colors import adjacency_aware_room_colors

_MAP_FILE_FORMAT = "PNG"

_FLOOR = 127
_WALL = 128

_B01_DRAWABLES = [
    Drawable.CHARGER,
    Drawable.NO_GO_AREAS,
    Drawable.PATH,
    Drawable.ROOM_NAMES,
    Drawable.VACUUM_POSITION,
]


@dataclass
class B01MapParserConfig:
    """Configuration for the B01/Q7 map parser."""

    map_scale: int = 4
    """Scale factor for the rendered map image."""


class B01MapParser:
    """Decoder/parser for B01/Q7 SCMap payloads."""

    def __init__(self, config: B01MapParserConfig | None = None) -> None:
        self._config = config or B01MapParserConfig()

    def parse(self, payload: bytes) -> ParsedMapData:
        """Parse an inflated SCMap payload and return a PNG + MapData."""
        parsed = _parse_scmap_payload(payload)
        size_x, size_y, grid = _extract_grid(parsed)
        room_names = _extract_room_names(parsed)

        room_pixels = _assign_room_pixels(parsed, grid, size_x=size_x, size_y=size_y)
        carpet_pixels = _carpet_pixel_indices(parsed, grid, size_x=size_x, size_y=size_y)
        image = _render_occupancy_image(
            grid, room_pixels, carpet_pixels, size_x=size_x, size_y=size_y, scale=self._config.map_scale
        )

        map_data = MapData()
        map_data.image = ImageData(
            size=size_x * size_y,
            top=0,
            left=0,
            height=size_y,
            width=size_x,
            image_config=ImageConfig(scale=self._config.map_scale),
            data=image,
            # Overlay points are stored in the rendered image's top-down pixel
            # space. ImageDimensions applies V1's bottom-up flip before drawing,
            # so this adapter cancels it (same approach as the Q10 renderer).
            img_transformation=lambda p: Point(p.x, size_y - p.y - 1, p.a),
        )
        if room_names:
            map_data.additional_parameters["room_names"] = room_names

        projector = _WorldToPixel(parsed)
        has_drawables = _place_poses(map_data, parsed, projector)
        map_data.rooms = _extract_rooms(parsed, projector, room_names)
        has_drawables = has_drawables or bool(map_data.rooms)
        if carpet_pixels:
            # Same contract as the Q10 parser: flat top-down grid indices.
            map_data.carpet_map = {(size_y - 1 - index // size_x) * size_x + index % size_x for index in carpet_pixels}

        if has_drawables:
            generator = _create_image_generator(
                MapParserConfig(map_scale=self._config.map_scale),
                drawables=_B01_DRAWABLES,
            )
            generator.draw_map(map_data)
            image = map_data.image.data

        image_bytes = io.BytesIO()
        image.save(image_bytes, format=_MAP_FILE_FORMAT)

        return ParsedMapData(
            image_content=image_bytes.getvalue(),
            map_data=map_data,
        )


def _parse_scmap_payload(payload: bytes) -> RobotMap:
    """Parse inflated SCMap bytes into a generated protobuf message."""
    parsed = RobotMap()
    try:
        parsed.ParseFromString(payload)
    except DecodeError as err:
        raise RoborockException("Failed to parse B01 SCMap") from err
    return parsed


def _extract_grid(parsed: RobotMap) -> tuple[int, int, bytes]:
    if not parsed.HasField("mapHead") or not parsed.HasField("mapData"):
        raise RoborockException("Failed to parse B01 map header/grid")

    size_x = parsed.mapHead.sizeX if parsed.mapHead.HasField("sizeX") else 0
    size_y = parsed.mapHead.sizeY if parsed.mapHead.HasField("sizeY") else 0
    if not size_x or not size_y or not parsed.mapData.HasField("mapData"):
        raise RoborockException("Failed to parse B01 map header/grid")

    map_data = parsed.mapData.mapData
    expected_len = size_x * size_y
    if len(map_data) < expected_len:
        raise RoborockException("B01 map data shorter than expected dimensions")

    return size_x, size_y, map_data[:expected_len]


class _WorldToPixel:
    """Project SCMap world coordinates (meters) into top-down image pixels."""

    def __init__(self, parsed: RobotMap) -> None:
        head = parsed.mapHead
        self._min_x = head.minX
        self._min_y = head.minY
        self._max_x = head.maxX
        self._max_y = head.maxY
        self._resolution = head.resolution or 0.05
        self._size_y = head.sizeY

    def in_bounds(self, x: float, y: float) -> bool:
        """Whether a world point lies inside the map (rejects placeholder poses)."""
        return self._min_x <= x <= self._max_x and self._min_y <= y <= self._max_y

    def to_pixel(self, x: float, y: float) -> tuple[float, float]:
        """World meters to top-down image pixel coordinates."""
        px = (x - self._min_x) / self._resolution
        py = self._size_y - 1 - (y - self._min_y) / self._resolution
        return px, py


def _place_poses(map_data: MapData, parsed: RobotMap, projector: _WorldToPixel) -> bool:
    """Populate charger, robot position and path from the decoded SCMap."""
    has_drawables = False

    if parsed.HasField("chargeStation") and projector.in_bounds(parsed.chargeStation.x, parsed.chargeStation.y):
        px, py = projector.to_pixel(parsed.chargeStation.x, parsed.chargeStation.y)
        map_data.charger = Point(px, py, math.degrees(parsed.chargeStation.phi))
        has_drawables = True

    if parsed.HasField("currentPose") and projector.in_bounds(parsed.currentPose.x, parsed.currentPose.y):
        px, py = projector.to_pixel(parsed.currentPose.x, parsed.currentPose.y)
        map_data.vacuum_position = Point(px, py, math.degrees(parsed.currentPose.phi))
        has_drawables = True
    elif map_data.charger is not None:
        # A saved map carries no live pose; show the robot at its dock.
        map_data.vacuum_position = Point(map_data.charger.x, map_data.charger.y, map_data.charger.a)

    areas = [
        Area(*(coord for point in area.points for coord in projector.to_pixel(point.x, point.y)))
        for area in parsed.areaInfo
        if len(area.points) == 4
    ]
    if areas:
        # areaInfo type semantics are not yet mapped per zone kind; render all
        # restricted areas through the no-go drawable for now.
        map_data.no_go_areas = areas
        has_drawables = True

    if parsed.HasField("historyPose"):
        pixels = [
            Point(*projector.to_pixel(point.x, point.y))
            for point in parsed.historyPose.points
            if projector.in_bounds(point.x, point.y)
        ]
        if pixels:
            map_data.path = Path(len(pixels), 1, 0, [pixels])
            has_drawables = True

    return has_drawables


def _extract_rooms(parsed: RobotMap, projector: _WorldToPixel, room_names: dict[int, str]) -> dict[int, Room] | None:
    """Build room bounding boxes (image-pixel space) from room outlines."""
    rooms: dict[int, Room] = {}
    label_positions = {
        room.roomId: projector.to_pixel(room.roomNamePost.x, room.roomNamePost.y)
        for room in parsed.roomDataInfo
        if room.HasField("roomNamePost")
    }
    size_y = parsed.mapHead.sizeY
    for outline in parsed.roomOutline:
        if not outline.points:
            continue
        room_id = outline.roomId
        # Outline points are top-down after the same vertical flip as the raster.
        xs = [point.x for point in outline.points]
        ys = [size_y - 1 - point.y for point in outline.points]
        pos = label_positions.get(room_id)
        rooms[room_id] = Room(
            min(xs),
            min(ys),
            max(xs),
            max(ys),
            room_id,
            room_names.get(room_id),
            pos[0] if pos else None,
            pos[1] if pos else None,
        )
    return rooms or None


def _extract_room_names(parsed: RobotMap) -> dict[int, str]:
    # Expose room id/name mapping without inventing room geometry/polygons.
    room_names: dict[int, str] = {}
    for room in parsed.roomDataInfo:
        if room.HasField("roomId"):
            room_id = room.roomId
            room_names[room_id] = room.roomName if room.HasField("roomName") else f"Room {room_id}"
    return room_names


def _assign_room_pixels(parsed: RobotMap, grid: bytes, *, size_x: int, size_y: int) -> bytearray:
    """Assign a room id to each floor pixel by flood-filling from room labels.

    The grid itself carries no room ids; room geometry arrives as boundary
    pixel chains (``roomOutline``). Each room is filled from its label
    position, bounded by walls and by any room's outline pixels, all in the
    raw (bottom-up) grid space.
    """
    assignment = bytearray(len(grid))
    outlines = {outline.roomId: outline for outline in parsed.roomOutline if outline.points}
    if not outlines:
        return assignment

    barrier = {
        point.y * size_x + point.x
        for outline in outlines.values()
        for point in outline.points
        if point.x < size_x and point.y < size_y
    }
    floor_count = grid.count(_FLOOR)
    # ponytail: leak guard — a gapped outline would flood the whole floor, so a
    # fill larger than half of it is discarded instead of tracing outline gaps.
    max_fill = floor_count // 2

    head = parsed.mapHead
    label_positions = {
        room.roomId: (
            int((room.roomNamePost.x - head.minX) / head.resolution),
            int((room.roomNamePost.y - head.minY) / head.resolution),
        )
        for room in parsed.roomDataInfo
        if room.HasField("roomNamePost")
    }

    for room_id, outline in outlines.items():
        seed = label_positions.get(room_id)
        if seed is None:
            continue
        col, row = seed
        start = row * size_x + col
        if not (0 <= col < size_x and 0 <= row < size_y) or grid[start] != _FLOOR:
            continue
        filled = []
        queue = deque([start])
        seen = {start}
        while queue and len(filled) <= max_fill:
            index = queue.popleft()
            filled.append(index)
            for neighbor in (index - 1, index + 1, index - size_x, index + size_x):
                if (
                    0 <= neighbor < len(grid)
                    and neighbor not in seen
                    and grid[neighbor] == _FLOOR
                    and assignment[neighbor] == 0
                    and neighbor not in barrier
                    # Row-wrap guard for the horizontal neighbors.
                    and abs(neighbor % size_x - index % size_x) <= 1
                ):
                    seen.add(neighbor)
                    queue.append(neighbor)
        if len(filled) > max_fill:
            continue
        for index in filled:
            assignment[index] = room_id
        # Color the room's own boundary ring too where it sits on floor.
        for point in outline.points:
            index = point.y * size_x + point.x
            if index < len(grid) and grid[index] == _FLOOR and assignment[index] == 0:
                assignment[index] = room_id

    return assignment


def _carpet_pixel_indices(parsed: RobotMap, grid: bytes, *, size_x: int, size_y: int) -> set[int]:
    """Raw-grid indices of floor pixels covered by enabled carpets."""
    head = parsed.mapHead
    resolution = head.resolution or 0.05
    indices: set[int] = set()
    for carpet in parsed.carpetInfo:
        if not carpet.points or (carpet.HasField("enabled") and not carpet.enabled):
            continue
        cols = [int((point.x - head.minX) / resolution) for point in carpet.points]
        rows = [int((point.y - head.minY) / resolution) for point in carpet.points]
        for row in range(max(min(rows), 0), min(max(rows), size_y - 1) + 1):
            for col in range(max(min(cols), 0), min(max(cols), size_x - 1) + 1):
                index = row * size_x + col
                if grid[index] == _FLOOR:
                    indices.add(index)
    return indices


def _render_occupancy_image(
    grid: bytes, room_pixels: bytearray, carpet_pixels: set[int], *, size_x: int, size_y: int, scale: int
) -> Image.Image:
    """Render the B01 occupancy grid with per-room colors."""

    colors = ColorsPalette()
    room_colors = {
        room_id: tuple(color[:3]) + (255,)
        for room_id, color in adjacency_aware_room_colors(
            room_pixels, size_x, colors, lambda value: value or None
        ).items()
    }

    # The observed occupancy grid contains only:
    # - 0: outside/unknown
    # - 127: floor/free
    # - 128: wall/obstacle
    # Same V1 palette roles as the Q10 renderer: transparent outside, grey
    # walls/obstacles, MAP_INSIDE for floor not assigned to any room.
    outside = (0, 0, 0, 0)
    floor = tuple(colors.get_color(SupportedColor.MAP_INSIDE)[:3]) + (255,)
    base_colors = {
        0: outside,
        _FLOOR: floor,
        _WALL: tuple(colors.get_color(SupportedColor.GREY_WALL)[:3]) + (255,),
    }

    rgba = bytearray()
    for index, value in enumerate(grid):
        if value == _FLOOR and (room_id := room_pixels[index]):
            color = room_colors.get(room_id, floor)
        else:
            color = base_colors.get(value, floor)
        if index in carpet_pixels and (index // size_x + index % size_x) % 2 == 0:
            # Checkerboard stipple, like the V1 carpet texture.
            color = tuple(min(channel + 60, 255) for channel in color[:3]) + (255,)
        rgba.extend(color)

    # RGBA so the shared V1 ImageGenerator can alpha-composite overlay glyphs.
    img = Image.frombytes("RGBA", (size_x, size_y), bytes(rgba))
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    if scale > 1:
        img = img.resize((size_x * scale, size_y * scale), resample=Image.Resampling.NEAREST)

    return img

"""Module for parsing B01/Q7 map content.

The inner SCMap blob is parsed with protobuf messages generated from
`roborock/map/proto/b01_scmap.proto`.
"""

import io
from dataclasses import dataclass

from google.protobuf.message import DecodeError
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.exceptions import RoborockException
from roborock.map.proto.b01_scmap_pb2 import RobotMap  # type: ignore[attr-defined]

from .b01_grid_layers import (
    LAYER_BACKGROUND,
    LAYER_FLOOR,
    LAYER_WALL,
    GridCalibration,
    GridLayers,
    decompose_grid,
)
from .map_parser import ParsedMapData

_MAP_FILE_FORMAT = "PNG"


# The Q7 occupancy grid encodes only these classes (no per-room segmentation in
# the raster -- room ids/names live in the protobuf metadata, not the pixels).
_Q7_WALL_VALUE = 127
_Q7_FLOOR_VALUE = 128


def classify_q7_cell(value: int) -> str:
    """Map a Q7 SCMap grid cell value to a canonical layer class."""
    if value == _Q7_WALL_VALUE:
        return LAYER_WALL
    if value == _Q7_FLOOR_VALUE:
        return LAYER_FLOOR
    return LAYER_BACKGROUND  # 0 = outside / unknown


def decompose_q7_layers(payload: bytes) -> GridLayers:
    """Split an inflated Q7 SCMap into background / wall / floor layers.

    Q7 has no per-room raster, so ``GridLayers.rooms`` is empty; room ids/names
    are available separately via the map metadata. Reuses the same device-agnostic
    decomposition as the Q10.
    """
    parsed = _parse_scmap_payload(payload)
    size_x, size_y, grid = _extract_grid(parsed)
    return decompose_grid(size_x, size_y, grid, [], classify_q7_cell)


def q7_calibration(payload: bytes) -> GridCalibration | None:
    """Build a world<->pixel calibration straight from the Q7 ``mapHead``.

    Unlike the Q10 (whose packet carries no calibration), the Q7 SCMap header
    provides ``minX``/``minY``/``resolution`` directly, so no path fitting is
    needed. World coordinates are in metres; resolution is metres-per-pixel.
    """
    head = _parse_scmap_payload(payload).mapHead
    if not head.HasField("resolution") or head.resolution <= 0 or not head.HasField("sizeY"):
        return None
    resolution = head.resolution
    min_x = head.minX if head.HasField("minX") else 0.0
    min_y = head.minY if head.HasField("minY") else 0.0
    return GridCalibration(
        resolution=resolution,
        origin_x=-min_x / resolution,
        origin_y=(head.sizeY - 1) + min_y / resolution,
        y_sign=1,
    )


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

        image = _render_occupancy_image(grid, size_x=size_x, size_y=size_y, scale=self._config.map_scale)

        map_data = MapData()
        map_data.image = ImageData(
            size=size_x * size_y,
            top=0,
            left=0,
            height=size_y,
            width=size_x,
            image_config=ImageConfig(scale=self._config.map_scale),
            data=image,
            img_transformation=lambda p: p,
        )
        if room_names:
            map_data.additional_parameters["room_names"] = room_names

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


def _extract_room_names(parsed: RobotMap) -> dict[int, str]:
    # Expose room id/name mapping without inventing room geometry/polygons.
    room_names: dict[int, str] = {}
    for room in parsed.roomDataInfo:
        if room.HasField("roomId"):
            room_id = room.roomId
            room_names[room_id] = room.roomName if room.HasField("roomName") else f"Room {room_id}"
    return room_names


def _render_occupancy_image(grid: bytes, *, size_x: int, size_y: int, scale: int) -> Image.Image:
    """Render the B01 occupancy grid into a simple image."""

    # The observed occupancy grid contains only:
    # - 0: outside/unknown
    # - 127: wall/obstacle
    # - 128: floor/free
    table = bytearray(range(256))
    table[0] = 0
    table[127] = 180
    table[128] = 255

    mapped = grid.translate(bytes(table))
    img = Image.frombytes("L", (size_x, size_y), mapped)
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert("RGB")

    if scale > 1:
        img = img.resize((size_x * scale, size_y * scale), resample=Image.Resampling.NEAREST)

    return img

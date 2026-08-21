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

from .map_parser import ParsedMapData

_MAP_FILE_FORMAT = "PNG"


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


def parse_map_type(payload: bytes) -> int:
    """Return the SCMap frame's map type without rendering the image.

    Type 0 is the live map of the current cleaning run, other types are
    historic or saved maps.
    """
    return _parse_scmap_payload(payload).mapType


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

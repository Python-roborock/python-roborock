"""Module for parsing v1 Roborock map content."""

import io
import logging
from dataclasses import dataclass, field

from vacuum_map_parser_base.config.color import ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

from roborock.exceptions import RoborockException

_LOGGER = logging.getLogger(__name__)

DEFAULT_DRAWABLES = {
    Drawable.CHARGER: True,
    Drawable.CLEANED_AREA: False,
    Drawable.GOTO_PATH: False,
    Drawable.IGNORED_OBSTACLES: False,
    Drawable.IGNORED_OBSTACLES_WITH_PHOTO: False,
    Drawable.MOP_PATH: False,
    Drawable.NO_CARPET_AREAS: False,
    Drawable.NO_GO_AREAS: False,
    Drawable.NO_MOPPING_AREAS: False,
    Drawable.OBSTACLES: False,
    Drawable.OBSTACLES_WITH_PHOTO: False,
    Drawable.PATH: True,
    Drawable.PREDICTED_PATH: False,
    Drawable.VACUUM_POSITION: True,
    Drawable.VIRTUAL_WALLS: False,
    Drawable.ZONES: False,
}
DEFAULT_MAP_SCALE = 4
MAP_FILE_FORMAT = "PNG"


def _default_drawable_factory() -> list[Drawable]:
    return [drawable for drawable, default_value in DEFAULT_DRAWABLES.items() if default_value]


@dataclass
class MapParserConfig:
    """Configuration for the Roborock map parser."""

    drawables: list[Drawable] = field(default_factory=_default_drawable_factory)
    """List of drawables to include in the map rendering."""

    show_background: bool = True
    """Whether to show the background of the map."""

    show_walls: bool = True
    """Whether to show the walls of the map."""

    show_rooms: bool = True
    """Whether to show the rooms of the map."""

    map_scale: int = DEFAULT_MAP_SCALE
    """Scale factor for the map."""


@dataclass
class ParsedMapData:
    """Roborock Map Data.

    This class holds the parsed map data and the rendered image.
    """

    image_content: bytes | None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None
    """The parsed map data which contains metadata for points on the map."""


class MapParser:
    """Roborock Map Parser.

    This class is used to parse the map data from the device and render it into an image.
    """

    def __init__(self, config: MapParserConfig) -> None:
        """Initialize the MapParser."""
        self._map_parser = _create_map_data_parser(config)

    def parse(self, map_bytes: bytes) -> ParsedMapData | None:
        """Parse map_bytes and return MapData and the image."""
        try:
            parsed_map = self._map_parser.parse(map_bytes)
        except (IndexError, ValueError) as err:
            raise RoborockException("Failed to parse map data") from err
        if parsed_map.image is None:
            raise RoborockException("Failed to render map image")
        img_byte_arr = io.BytesIO()
        parsed_map.image.data.save(img_byte_arr, format=MAP_FILE_FORMAT)
        return ParsedMapData(image_content=img_byte_arr.getvalue(), map_data=parsed_map)


def _create_map_data_parser(config: MapParserConfig) -> RoborockMapDataParser:
    """Create a RoborockMapDataParser based on the config entry."""
    color_dicts = {}
    room_colors = {}

    if not config.show_background:
        color_dicts[SupportedColor.MAP_OUTSIDE] = (0, 0, 0, 0)

    if not config.show_walls:
        color_dicts[SupportedColor.GREY_WALL] = (0, 0, 0, 0)
        color_dicts[SupportedColor.MAP_WALL] = (0, 0, 0, 0)
        color_dicts[SupportedColor.MAP_WALL_V2] = (0, 0, 0, 0)

    if not config.show_rooms:
        room_colors = {str(x): (0, 0, 0, 0) for x in range(1, 32)}

    return RoborockMapDataParser(
        ColorsPalette(color_dicts if len(color_dicts) else None, room_colors if len(room_colors) else None),
        Sizes({k: v * config.map_scale for k, v in Sizes.SIZES.items() if k != Size.MOP_PATH_WIDTH}),
        config.drawables,
        ImageConfig(scale=config.map_scale),
        [],
    )

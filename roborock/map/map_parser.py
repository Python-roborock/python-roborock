"""Module for parsing v1 Roborock map content."""

import io
import logging
import threading
from dataclasses import dataclass, field

from vacuum_map_parser_base.config.color import Color, ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.image_generator import ImageGenerator
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_roborock.image_parser import RoborockImageParser
from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

from roborock.exceptions import RoborockException

from .room_colors import adjacency_aware_room_colors

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


class _AdjacencyAwareRoborockImageParser(RoborockImageParser):
    """Apply the shared adjacency color policy to V1 room cells."""

    def __init__(
        self,
        palette: ColorsPalette,
        image_config: ImageConfig,
        *,
        recolor_rooms: bool = True,
    ) -> None:
        super().__init__(palette, image_config)
        self._room_palette = palette
        self._base_room_colors = palette.cached_room_colors.copy()
        self._recolor_rooms = recolor_rooms
        self._palette_lock = threading.Lock()

    def parse(
        self,
        raw_data: bytes,
        width: int,
        height: int,
        carpet_map: set[int] | None,
        removed_map: set[int] | None = None,
    ):
        """Assign non-conflicting room colors before the V1 image pass."""
        with self._palette_lock:
            self._room_palette.cached_room_colors.clear()
            self._room_palette.cached_room_colors.update(self._base_room_colors)

            if self._recolor_rooms:

                def room_id(value: int) -> int | None:
                    if value in (self.MAP_OUTSIDE, self.MAP_WALL, self.MAP_INSIDE, self.MAP_SCAN):
                        return None
                    return self._get_room_number(value) if value & 0x07 == 0x07 else None

                room_colors = adjacency_aware_room_colors(raw_data, width, self._room_palette, room_id)
                for number, color in room_colors.items():
                    self._room_palette.cached_room_colors[number] = color
                    self._room_palette.cached_room_colors[str(number)] = color
            return super().parse(raw_data, width, height, carpet_map, removed_map)


def _create_map_data_parser(config: MapParserConfig) -> RoborockMapDataParser:
    """Create a RoborockMapDataParser based on the config entry."""
    palette, sizes, image_config = _create_rendering_components(config)
    parser = RoborockMapDataParser(
        palette,
        sizes,
        config.drawables,
        image_config,
        [],
    )
    parser._image_parser = _AdjacencyAwareRoborockImageParser(
        palette,
        image_config,
        recolor_rooms=config.show_rooms,
    )
    return parser


def create_image_generator(
    config: MapParserConfig,
    *,
    drawables: list[Drawable] | None = None,
) -> ImageGenerator:
    """Create the image generator used by V1-compatible map renderers.

    Other protocols should use this factory for shared drawables instead of
    copying V1 colors, sizes, glyphs, or transparency behavior.
    """
    palette, sizes, image_config = _create_rendering_components(config)
    return ImageGenerator(
        palette,
        sizes,
        config.drawables if drawables is None else drawables,
        image_config,
        [],
    )


def _create_rendering_components(
    config: MapParserConfig,
) -> tuple[ColorsPalette, Sizes, ImageConfig]:
    """Build the shared V1 palette, scaled sizes, and image configuration."""
    color_dicts: dict[SupportedColor, Color] = {}
    room_colors: dict[str, Color] = {}

    if not config.show_background:
        color_dicts[SupportedColor.MAP_OUTSIDE] = (0, 0, 0, 0)

    if not config.show_walls:
        color_dicts[SupportedColor.GREY_WALL] = (0, 0, 0, 0)
        color_dicts[SupportedColor.MAP_WALL] = (0, 0, 0, 0)
        color_dicts[SupportedColor.MAP_WALL_V2] = (0, 0, 0, 0)

    if not config.show_rooms:
        room_colors = {str(room_id): (0, 0, 0, 0) for room_id in map(int, ColorsPalette.ROOM_COLORS)}

    return (
        ColorsPalette(color_dicts, room_colors),
        Sizes({k: v * config.map_scale for k, v in Sizes.SIZES.items() if k != Size.MOP_PATH_WIDTH}),
        ImageConfig(scale=config.map_scale),
    )

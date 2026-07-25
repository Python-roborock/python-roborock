"""Tests for the map parser."""

from pathlib import Path

import pytest
from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Size

from roborock.exceptions import RoborockException
from roborock.map.map_parser import (
    MapParser,
    MapParserConfig,
    _AdjacencyAwareRoborockImageParser,
    _create_map_data_parser,
    create_image_generator,
)

MAP_DATA_FILE = Path(__file__).parent / "raw_map_data"
DEFAULT_MAP_CONFIG = MapParserConfig()


@pytest.mark.parametrize("map_content", [b"", b"12345"])
def test_invalid_map_content(map_content: bytes):
    """Test that parsing map data returns the expected image and data."""
    parser = MapParser(DEFAULT_MAP_CONFIG)
    with pytest.raises(RoborockException, match="Failed to parse map data"):
        parser.parse(map_content)


def test_shared_image_generator_matches_v1_rendering_components() -> None:
    """Protocol renderers share V1 colors, scaled sizes, and image config."""
    config = MapParserConfig(map_scale=3)
    drawables = [
        Drawable.CHARGER,
        Drawable.PATH,
        Drawable.VACUUM_POSITION,
        Drawable.VIRTUAL_WALLS,
    ]
    shared = create_image_generator(config, drawables=drawables)
    v1 = _create_map_data_parser(config)._image_generator

    assert shared._palette.cached_colors == v1._palette.cached_colors
    assert shared._palette.cached_room_colors == v1._palette.cached_room_colors
    assert shared._image_config == v1._image_config
    assert shared._drawables == drawables
    for size in Size:
        assert shared._sizes.get_size(size) == v1._sizes.get_size(size)


def test_v1_parser_gives_adjacent_rooms_distinct_palette_colors() -> None:
    """Repeated palette entries do not merge neighboring V1 rooms."""
    palette = ColorsPalette()
    original_room_12 = palette.get_room_color(12)
    image_parser = _AdjacencyAwareRoborockImageParser(palette, ImageConfig())
    raw_data = bytes([(2 << 3) | 7, (12 << 3) | 7])

    image, _rooms = image_parser.parse(raw_data, 2, 1, None)

    assert image is not None
    assert image.getpixel((0, 0)) != image.getpixel((1, 0))

    isolated_image, _rooms = image_parser.parse(bytes([(12 << 3) | 7]), 1, 1, None)

    assert isolated_image is not None
    assert isolated_image.getpixel((0, 0))[: len(original_room_12)] == original_room_12


def test_v1_parser_keeps_adjacent_rooms_hidden_when_rooms_disabled() -> None:
    """Adjacency conflict handling cannot override intentional transparency."""
    parser = _create_map_data_parser(MapParserConfig(show_rooms=False, map_scale=1))._image_parser
    raw_data = bytes([(2 << 3) | 7, (12 << 3) | 7])

    image, _rooms = parser.parse(raw_data, 2, 1, None)

    assert image is not None
    assert [image.getpixel((x, 0)) for x in range(2)] == [(0, 0, 0, 0)] * 2


# We can add additional tests here in the future that actually parse valid map data

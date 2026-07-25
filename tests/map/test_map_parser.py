"""Tests for the map parser."""

from pathlib import Path

import pytest
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size

from roborock.exceptions import RoborockException
from roborock.map.map_parser import (
    MapParser,
    MapParserConfig,
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


# We can add additional tests here in the future that actually parse valid map data

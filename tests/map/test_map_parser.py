"""Tests for the map parser."""

from pathlib import Path

import pytest
from roborock.exceptions import RoborockException
from roborock.map.map_parser import MapParser, MapParserConfig

MAP_DATA_FILE = Path(__file__).parent / "raw_map_data"
DEFAULT_MAP_CONFIG = MapParserConfig()


@pytest.mark.parametrize("map_content", [b"", b"12345"])
def test_invalid_map_content(map_content: bytes):
    """Test that parsing map data returns the expected image and data."""
    parser = MapParser(DEFAULT_MAP_CONFIG)
    with pytest.raises(RoborockException, match="Failed to parse map data"):
        parser.parse(map_content)


# We can add additional tests here in the future that actually parse valid map data

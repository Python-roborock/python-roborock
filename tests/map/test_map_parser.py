"""Tests for the map parser."""

import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from syrupy.assertion import SnapshotAssertion
from vacuum_map_parser_base.config.drawable import Drawable

from roborock.exceptions import RoborockException
from roborock.map.map_parser import MapParser, MapParserConfig, ParsedMapData, _create_image_generator

V1_FIXTURES_DIR = Path(__file__).resolve().parent / "testdata" / "v1"
DEFAULT_MAP_CONFIG = MapParserConfig()


def _map_data_to_snapshot(result: ParsedMapData) -> dict[str, Any]:
    md = result.map_data
    assert md is not None
    assert result.image_content is not None
    image = Image.open(io.BytesIO(result.image_content))
    return {
        "image_size": image.size,
        "image_format": image.format,
        "charger": md.charger,
        "vacuum_position": md.vacuum_position,
        "goto": md.goto,
        "rooms": md.rooms,
        "walls": md.walls,
        "no_go_areas": md.no_go_areas,
        "no_mopping_areas": md.no_mopping_areas,
        "zones": md.zones,
        "path_points": len(md.path.path[0]) if md.path and md.path.path else 0,
        "goto_path_points": len(md.goto_path.path[0]) if md.goto_path and md.goto_path.path else 0,
        "predicted_path_points": len(md.predicted_path.path[0]) if md.predicted_path and md.predicted_path.path else 0,
        "additional_parameters": md.additional_parameters,
    }


@pytest.mark.parametrize("map_content", [b"", b"12345"])
def test_invalid_map_content(map_content: bytes) -> None:
    """Test that parsing map data returns the expected image and data."""
    parser = MapParser(DEFAULT_MAP_CONFIG)
    with pytest.raises(RoborockException, match="Failed to parse map data"):
        parser.parse(map_content)


@pytest.mark.parametrize(
    "filename",
    [
        "s5_fw2008_with_segments.bin",
        "s5_fw1886_with_forbidden_zones_and_virtual_walls.bin",
        "s5_fw1886_with_goto_target.bin",
        "s6_fw2652_with_active_segment_and_no_mop_zone.bin",
    ],
)
def test_parse_v1_fixtures(
    filename: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that parsing valid V1 fixtures matches expected snapshot."""
    raw_data = (V1_FIXTURES_DIR / filename).read_bytes()
    parser = MapParser(DEFAULT_MAP_CONFIG)
    result = parser.parse(raw_data)

    assert result is not None
    assert result.image_content is not None
    assert result.image_content.startswith(b"\x89PNG\r\n\x1a\n")
    assert _map_data_to_snapshot(result) == snapshot


def test_map_parser_config_variants() -> None:
    """Test map parser with different display flags and scales."""
    raw_data = (V1_FIXTURES_DIR / "s6_fw2652_with_active_segment_and_no_mop_zone.bin").read_bytes()

    config_custom = MapParserConfig(
        show_background=False,
        show_walls=False,
        show_rooms=False,
        map_scale=2,
    )
    parser_custom = MapParser(config_custom)
    result_custom = parser_custom.parse(raw_data)
    assert result_custom is not None
    assert result_custom.image_content is not None

    parser_scaled = MapParser(MapParserConfig(map_scale=1))
    result_scaled = parser_scaled.parse(raw_data)
    assert result_scaled is not None
    assert result_scaled.image_content is not None

    img_scale2 = Image.open(io.BytesIO(result_custom.image_content))
    img_scale1 = Image.open(io.BytesIO(result_scaled.image_content))
    assert img_scale2.width > img_scale1.width
    assert img_scale2.height > img_scale1.height


def test_map_parser_rendering_failure() -> None:
    """Test that failure to generate an image raises RoborockException."""
    raw_data = (V1_FIXTURES_DIR / "s5_fw2008_with_segments.bin").read_bytes()
    parser = MapParser(DEFAULT_MAP_CONFIG)

    mock_map_data = MagicMock()
    mock_map_data.image = None

    with (
        patch.object(parser._map_parser, "parse", return_value=mock_map_data),
        pytest.raises(RoborockException, match="Failed to render map image"),
    ):
        parser.parse(raw_data)


def test_create_image_generator() -> None:
    """Test image generator creation with default and custom drawables."""
    generator = _create_image_generator(DEFAULT_MAP_CONFIG)
    assert generator is not None

    custom_generator = _create_image_generator(
        DEFAULT_MAP_CONFIG,
        drawables=[Drawable.PATH, Drawable.CHARGER],
    )
    assert custom_generator is not None

"""Tests for the MapContentTrait."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.map_content import MapContentTrait
from roborock.map.map_parser import ParsedMapData
from roborock.roborock_typing import RoborockCommand


@pytest.fixture
def map_content_trait(device: RoborockDevice) -> MapContentTrait:
    """Create a MapContentTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.map_content


async def test_refresh_map_content_trait(
    map_content_trait: MapContentTrait,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test successfully getting and parsing map content."""
    map_data = b"dummy_map_bytes"
    mock_map_rpc_channel.send_command.return_value = map_data
    mock_parsed_data = ParsedMapData(
        image_content=b"dummy_image_content",
        map_data=MagicMock(),
    )

    with patch("roborock.devices.traits.v1.map_content.MapParser.parse", return_value=mock_parsed_data) as mock_parse:
        await map_content_trait.refresh()
        mock_parse.assert_called_once_with(map_data)

    assert map_content_trait.image_content == b"dummy_image_content"
    assert map_content_trait.map_data is not None

    mock_map_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_MAP_V1)

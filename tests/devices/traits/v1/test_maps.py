"""Tests for the Maps related functionality."""

from unittest.mock import AsyncMock

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.maps import MapsTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

UPDATED_STATUS = {
    **mock_data.STATUS,
    "map_status": 123 * 4 + 3,  # Set current map to 123
}


MULTI_MAP_LIST_DATA = [
    {
        "max_multi_map": 1,
        "max_bak_map": 1,
        "multi_map_count": 1,
        "map_info": [
            {
                "mapFlag": 0,
                "add_time": 1747132930,
                "length": 0,
                "name": "Map 1",
                "bak_maps": [{"mapFlag": 4, "add_time": 1747132936}],
            },
            {
                "mapFlag": 123,
                "add_time": 1747132930,
                "length": 0,
                "name": "Map 2",
                "bak_maps": [{"mapFlag": 4, "add_time": 1747132936}],
            },
        ],
    }
]


@pytest.fixture
def status_trait(device: RoborockDevice) -> StatusTrait:
    """Create a MapsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.status


@pytest.fixture
def maps_trait(device: RoborockDevice) -> MapsTrait:
    """Create a MapsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.maps


async def test_refresh_maps_trait(
    maps_trait: MapsTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    status_trait: StatusTrait,
) -> None:
    """Test successfully getting multi maps list."""
    # Setup mock to return the sample multi maps list
    mock_rpc_channel.send_command.side_effect = [
        mock_data.STATUS,  # Initial status fetch
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,
    ]
    await status_trait.refresh()
    assert status_trait.current_map == 0

    # Populating the status information gives us the current map
    # flag, but we have not loaded the rest of the information.
    assert maps_trait.current_map == 0
    assert maps_trait.current_map_info is None

    # Load the maps information
    await maps_trait.refresh()

    assert maps_trait.max_multi_map == 1
    assert maps_trait.max_bak_map == 1
    assert maps_trait.multi_map_count == 1
    assert maps_trait.map_info

    assert len(maps_trait.map_info) == 2
    map_infos = maps_trait.map_info
    assert len(map_infos) == 2
    assert map_infos[0].map_flag == 0
    assert map_infos[0].name == "Map 1"
    assert map_infos[0].add_time == 1747132930
    assert map_infos[1].map_flag == 123
    assert map_infos[1].name == "Map 2"
    assert map_infos[1].add_time == 1747132930

    assert maps_trait.current_map == 0
    assert maps_trait.current_map_info is not None
    assert maps_trait.current_map_info.map_flag == 0
    assert maps_trait.current_map_info.name == "Map 1"

    # Verify the RPC call was made correctly
    assert mock_rpc_channel.send_command.call_count == 1
    mock_rpc_channel.send_command.assert_any_call(RoborockCommand.GET_STATUS)
    assert mock_mqtt_rpc_channel.send_command.call_count == 1
    mock_mqtt_rpc_channel.send_command.assert_any_call(RoborockCommand.GET_MULTI_MAPS_LIST)


async def test_set_current_map(
    status_trait: StatusTrait,
    maps_trait: MapsTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
) -> None:
    """Test successfully setting the current map."""
    assert hasattr(maps_trait, "mqtt_rpc_channel")
    mock_rpc_channel.send_command.side_effect = [
        mock_data.STATUS,  # Initial status fetch
        UPDATED_STATUS,  # Response for refreshing status
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Response for LOAD_MULTI_MAP
        {},  # Response for setting the current map
    ]
    await status_trait.refresh()

    # First refresh to populate initial state
    await maps_trait.refresh()

    # Verify current map

    assert maps_trait.current_map == 0
    assert maps_trait.current_map_info
    assert maps_trait.current_map_info.map_flag == 0
    assert maps_trait.current_map_info.name == "Map 1"

    # Call the method to set current map
    await maps_trait.set_current_map(123)

    # Verify the current map is updated
    assert maps_trait.current_map == 123
    assert maps_trait.current_map_info
    assert maps_trait.current_map_info.map_flag == 123
    assert maps_trait.current_map_info.name == "Map 2"

    # Verify the command sent are:
    # 1. GET_STATUS to get initial status
    # 2. GET_MULTI_MAPS_LIST to get the map list
    # 3. LOAD_MULTI_MAP to set the map
    # 4. GET_STATUS to refresh the current map in status
    assert mock_rpc_channel.send_command.call_count == 2
    mock_rpc_channel.send_command.assert_any_call(RoborockCommand.GET_STATUS)
    assert mock_mqtt_rpc_channel.send_command.call_count == 2
    mock_mqtt_rpc_channel.send_command.assert_any_call(RoborockCommand.GET_MULTI_MAPS_LIST)
    mock_mqtt_rpc_channel.send_command.assert_any_call(RoborockCommand.LOAD_MULTI_MAP, params=[123])

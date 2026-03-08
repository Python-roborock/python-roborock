"""Tests for the RoomMapping related functionality."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from roborock.data.containers import HomeDataRoom, NamedRoomMapping
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.rooms import RoomsTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.roborock_typing import RoborockCommand


@pytest.fixture
def status_trait(device: RoborockDevice) -> StatusTrait:
    """Create a StatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.status


@pytest.fixture
def rooms_trait(device: RoborockDevice) -> RoomsTrait:
    """Create a RoomsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.rooms


# Rooms from mock_data.HOME_DATA
# {"id": 2362048, "name": "Example room 1"},
# {"id": 2362044, "name": "Example room 2"},
# {"id": 2362041, "name": "Example room 3"},
@pytest.mark.parametrize(
    ("room_mapping_data"),
    [
        ([[16, "2362048"], [17, "2362044"], [18, "2362041"]]),
        ([[16, "2362048", 6], [17, "2362044", 14], [18, "2362041", 13]]),
    ],
)
async def test_refresh_rooms_trait(
    rooms_trait: RoomsTrait,
    mock_rpc_channel: AsyncMock,
    room_mapping_data: list[Any],
) -> None:
    """Test successfully getting room mapping."""
    # Setup mock to return the sample room mapping
    mock_rpc_channel.send_command.side_effect = [room_mapping_data]
    # Before refresh, rooms should be empty
    assert not rooms_trait.rooms

    # Load the room mapping information
    await rooms_trait.refresh()

    # Verify the room mappings are now populated
    assert rooms_trait.rooms
    rooms = rooms_trait.rooms
    assert len(rooms) == 3

    assert rooms[0].segment_id == 16
    assert rooms[0].name == "Example room 1"
    assert rooms[0].iot_id == "2362048"

    assert rooms[1].segment_id == 17
    assert rooms[1].name == "Example room 2"
    assert rooms[1].iot_id == "2362044"

    assert rooms[2].segment_id == 18
    assert rooms[2].name == "Example room 3"
    assert rooms[2].iot_id == "2362041"

    # Verify the RPC call was made correctly
    assert mock_rpc_channel.send_command.call_count == 1
    mock_rpc_channel.send_command.assert_any_call(RoborockCommand.GET_ROOM_MAPPING)


async def test_refresh_unknown_room_names_overwrites_home_data(
    rooms_trait: RoomsTrait,
    web_api_client: AsyncMock,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test web rooms are used to refresh home data for missing iot ids."""
    original_rooms = list(rooms_trait._home_data.rooms or ())
    try:
        web_api_client.get_rooms.return_value = [
            HomeDataRoom(id=2362048, name="Living Room"),
            HomeDataRoom(id=2362044, name="Example room 2"),
            HomeDataRoom(id=2362041, name="Example room 3"),
            HomeDataRoom(id=9999999, name="Office"),
        ]

        room_mapping_data = [[16, "2362048"], [17, "9999999"]]
        mock_rpc_channel.send_command.side_effect = [room_mapping_data]

        await rooms_trait.refresh()

        assert rooms_trait.rooms
        assert rooms_trait.rooms[0] == NamedRoomMapping(segment_id=16, iot_id="2362048", name="Living Room")
        assert rooms_trait.rooms[1] == NamedRoomMapping(segment_id=17, iot_id="9999999", name="Office")

        home_data_rooms = {str(room.id): room.name for room in rooms_trait._home_data.rooms or ()}
        assert home_data_rooms["2362048"] == "Living Room"
        assert home_data_rooms["9999999"] == "Office"
    finally:
        rooms_trait._home_data.rooms = original_rooms


async def test_refresh_unknown_room_names_web_api_called_once(
    rooms_trait: RoomsTrait,
    web_api_client: AsyncMock,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test unknown room IDs trigger one web lookup per iot_id."""
    original_rooms = list(rooms_trait._home_data.rooms or ())
    try:
        web_api_client.get_rooms.return_value = [
            HomeDataRoom(id=9999911, name="Living Room"),
        ]

        room_mapping_data = [[16, "9999911"]]
        mock_rpc_channel.send_command.side_effect = [room_mapping_data, room_mapping_data]

        await rooms_trait.refresh()
        assert rooms_trait.rooms
        assert rooms_trait.rooms[0].name == "Living Room"

        await rooms_trait.refresh()
        assert rooms_trait.rooms
        assert rooms_trait.rooms[0].name == "Living Room"
        web_api_client.get_rooms.assert_called_once()
    finally:
        rooms_trait._home_data.rooms = original_rooms


async def test_refresh_unknown_room_names_unresolved_uses_room_fallback(
    rooms_trait: RoomsTrait,
    web_api_client: AsyncMock,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test unresolved unknown names use Room fallback in RoomsTrait."""
    web_api_client.get_rooms.return_value = []
    room_mapping_data = [[33, "9999922"]]
    mock_rpc_channel.send_command.side_effect = [room_mapping_data, room_mapping_data]

    await rooms_trait.refresh()
    assert rooms_trait.rooms
    assert rooms_trait.rooms[0] == NamedRoomMapping(segment_id=33, iot_id="9999922", name="Room 33")

    await rooms_trait.refresh()
    assert rooms_trait.rooms
    assert rooms_trait.rooms[0] == NamedRoomMapping(segment_id=33, iot_id="9999922", name="Room 33")
    web_api_client.get_rooms.assert_called_once()

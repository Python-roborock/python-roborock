"""Tests for the Home related functionality."""

import base64
import copy
from collections.abc import Iterator
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from PIL import Image
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.map_data import ImageData, MapData

from roborock.data.containers import CombinedMapInfo, HomeDataRoom, NamedRoomMapping
from roborock.data.v1.v1_code_mappings import RoborockInCleaning, RoborockStateCode
from roborock.data.v1.v1_containers import MultiMapsListMapInfo, MultiMapsListRoom
from roborock.devices.cache import DeviceCache, DeviceCacheData, InMemoryCache
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.home import HomeTrait
from roborock.devices.traits.v1.map_content import MapContentTrait
from roborock.devices.traits.v1.maps import MapsTrait
from roborock.devices.traits.v1.rooms import RoomsTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockDeviceBusy, RoborockException, RoborockInvalidStatus
from roborock.map.map_parser import ParsedMapData
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

MULTI_MAP_LIST_DATA = [
    {
        "max_multi_map": 2,
        "max_bak_map": 1,
        "multi_map_count": 2,
        "map_info": [
            {
                "mapFlag": 0,
                "add_time": 1747132930,
                "length": 0,
                "name": "Ground Floor",
                "bak_maps": [{"mapFlag": 4, "add_time": 1747132936}],
            },
            {
                "mapFlag": 123,
                "add_time": 1747132940,
                "length": 0,
                "name": "Second Floor",
                "bak_maps": [{"mapFlag": 5, "add_time": 1747132946}],
            },
        ],
    }
]
MULTI_MAP_LIST_SINGLE_MAP_DATA = [
    {
        "max_multi_map": 1,
        "max_bak_map": 0,
        "multi_map_count": 1,
        "map_info": [
            {
                "mapFlag": 0,
                "add_time": 1747132930,
                "length": 0,
                "name": "Only Floor",
                "bak_maps": [],
            },
        ],
    }
]

ROOM_MAPPING_DATA_MAP_0 = [[16, "2362048"], [17, "2362044"]]
ROOM_MAPPING_DATA_MAP_123 = [[18, "2362041"], [19, "2362042"]]

UPDATED_STATUS_MAP_0 = {
    **mock_data.STATUS,
    "map_status": 0 * 4 + 3,  # Set current map to 0
}

UPDATED_STATUS_MAP_123 = {
    **mock_data.STATUS,
    "map_status": 123 * 4 + 3,  # Set current map to 123
}
MAP_BYTES_RESPONSE_1 = b"<map bytes 1>"
MAP_BYTES_RESPONSE_2 = b"<map bytes 2>"
EMPTY_MAP_BYTES = b"<empty map bytes>"
TEST_IMAGE_CONTENT_1 = b"<image bytes 1>"
TEST_IMAGE_CONTENT_2 = b"<image bytes 2>"
TEST_PARSER_MAP = {
    MAP_BYTES_RESPONSE_1: TEST_IMAGE_CONTENT_1,
    MAP_BYTES_RESPONSE_2: TEST_IMAGE_CONTENT_2,
}


@pytest.fixture(autouse=True)
def no_sleep() -> Iterator[None]:
    """Patch sleep to avoid delays in tests."""
    with patch("roborock.devices.traits.v1.home.asyncio.sleep"):
        yield


@pytest.fixture(name="cache")
def cache_fixture():
    """Create an in-memory cache for testing."""
    return InMemoryCache()


@pytest.fixture(name="device_cache")
def device_cache_fixture(cache: InMemoryCache) -> DeviceCache:
    """Create a DeviceCache instance for testing."""
    return DeviceCache(duid="abc123", cache=cache)


@pytest.fixture(autouse=True)
async def status_trait(mock_rpc_channel: AsyncMock, device: RoborockDevice) -> StatusTrait:
    """Create a StatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    status_trait = device.v1_properties.status

    # Verify initial state
    assert status_trait.current_map is None
    mock_rpc_channel.send_command.side_effect = [UPDATED_STATUS_MAP_0]
    await status_trait.refresh()
    assert status_trait.current_map == 0

    mock_rpc_channel.reset_mock()
    return status_trait


@pytest.fixture
def maps_trait(device: RoborockDevice) -> MapsTrait:
    """Create a MapsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.maps


@pytest.fixture
def map_content_trait(device: RoborockDevice) -> MapContentTrait:
    """Create a MapContentTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.map_content


@pytest.fixture
def rooms_trait(device: RoborockDevice) -> RoomsTrait:
    """Create a RoomsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.rooms


@pytest.fixture
def mock_web_api(web_api_client: AsyncMock) -> AsyncMock:
    """Alias the shared web API fixture for readability in this module."""
    web_api_client.get_rooms.return_value = []
    return web_api_client


@pytest.fixture
def home_trait(
    status_trait: StatusTrait,
    maps_trait: MapsTrait,
    map_content_trait: MapContentTrait,
    rooms_trait: RoomsTrait,
    device_cache: DeviceCache,
) -> HomeTrait:
    """Create a HomeTrait instance with mocked dependencies."""
    return HomeTrait(status_trait, maps_trait, map_content_trait, rooms_trait, device_cache)


@pytest.fixture(autouse=True)
def map_parser_fixture() -> Iterator[None]:
    """Mock MapParser.parse to return predefined test map data."""

    def parse_data(response: bytes) -> ParsedMapData:
        if response == EMPTY_MAP_BYTES:
            map_data = MapData()
            map_data.image = ImageData.create_empty(Image.new("RGB", (1, 1)))
            return ParsedMapData(image_content=b"NO MAP", map_data=map_data)
        if image_content := TEST_PARSER_MAP.get(response):
            map_data = MapData()
            map_data.image = ImageData(1, 0, 0, 1, 1, ImageConfig(), Image.new("RGB", (1, 1)), lambda p: p)
            return ParsedMapData(
                image_content=image_content,
                map_data=map_data,
            )
        raise ValueError(f"Unexpected map bytes {response!r}")

    with patch("roborock.devices.traits.v1.map_content.MapParser.parse", side_effect=parse_data):
        yield


async def test_discover_home_empty_cache(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    device_cache: DeviceCache,
    web_api_client: AsyncMock,
) -> None:
    """Test discovering home when cache is empty."""
    # Setup mocks for the discovery process
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,  # Status right after switching to map 123
        UPDATED_STATUS_MAP_123,  # Status once map 123 has loaded
        ROOM_MAPPING_DATA_MAP_123,  # Rooms for map 123
        UPDATED_STATUS_MAP_0,  # Status right after switching back to map 0
        UPDATED_STATUS_MAP_0,  # Status once map 0 has loaded
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for map 0
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Multi maps list
        {},  # LOAD_MULTI_MAP response for map 123
        {},  # LOAD_MULTI_MAP response back to map 0
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_2,  # Map bytes for 123
        MAP_BYTES_RESPONSE_1,  # Map bytes for 0
    ]
    # We have an empty home data so the room list gets loaded
    web_api_client.get_rooms.return_value = [
        HomeDataRoom(id=2362048, name="Example room 1"),
        HomeDataRoom(id=2362044, name="Example room 2"),
        HomeDataRoom(id=2362041, name="Example room 3"),
    ]

    # Before discovery, no cache should exist
    assert home_trait.home_map_info is None
    assert home_trait.current_map_data is None

    # Perform home discovery
    await home_trait.discover_home()

    # Verify cache is populated
    assert home_trait.home_map_info is not None
    assert len(home_trait.home_map_info) == 2

    # Check map 0 data
    map_0_data = home_trait.home_map_info[0]
    assert map_0_data.map_flag == 0
    assert map_0_data.name == "Ground Floor"
    assert len(map_0_data.rooms) == 2
    assert map_0_data.rooms[0].segment_id == 16
    assert map_0_data.rooms[0].iot_id == "2362048"
    assert map_0_data.rooms[0].name == "Example room 1"
    assert map_0_data.rooms[1].segment_id == 17
    assert map_0_data.rooms[1].iot_id == "2362044"
    assert map_0_data.rooms[1].name == "Example room 2"

    map_0_content = home_trait.home_map_content[0]
    assert map_0_content is not None
    assert map_0_content.image_content == TEST_IMAGE_CONTENT_1
    assert map_0_content.map_data is not None

    # Check map 123 data
    map_123_data = home_trait.home_map_info[123]
    assert map_123_data.map_flag == 123
    assert map_123_data.name == "Second Floor"
    assert len(map_123_data.rooms) == 2
    assert map_123_data.rooms[0].segment_id == 18
    assert map_123_data.rooms[0].iot_id == "2362041"
    assert map_123_data.rooms[0].name == "Example room 3"
    assert map_123_data.rooms[1].segment_id == 19
    assert map_123_data.rooms[1].iot_id == "2362042"
    assert map_123_data.rooms[1].name == "Room 19"  # Not in mock home data

    map_123_content = home_trait.home_map_content[123]
    assert map_123_content is not None
    assert map_123_content.image_content == TEST_IMAGE_CONTENT_2
    assert map_123_content.map_data is not None

    # Verify current map data is accessible
    current_map_data = home_trait.current_map_data
    assert current_map_data is not None
    assert current_map_data.map_flag == 0
    assert current_map_data.name == "Ground Floor"
    assert [room.name for room in home_trait.current_rooms] == [
        "Example room 1",
        "Example room 2",
    ]

    # Verify the persistent cache has been updated
    device_cache_data = await device_cache.get()
    assert device_cache_data.home_map_info is not None
    assert len(device_cache_data.home_map_info) == 2
    assert device_cache_data.home_map_content_base64 is not None
    assert len(device_cache_data.home_map_content_base64) == 2


@pytest.mark.parametrize(
    "device_cache_data",
    [
        DeviceCacheData(
            home_map_info={0: CombinedMapInfo(map_flag=0, name="Dummy", rooms=[])},
            home_map_content_base64={0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode("utf-8")},
        ),
    ],
)
async def test_discover_home_with_existing_cache(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    device_cache_data: DeviceCacheData,
    device_cache: DeviceCache,
) -> None:
    """Test that discovery is skipped when cache already exists."""
    # Pre-populate the cache
    await device_cache.set(device_cache_data)

    # Call discover_home
    await home_trait.discover_home()

    # Verify no RPC calls were made (discovery was skipped)
    assert mock_rpc_channel.send_command.call_count == 0
    assert mock_mqtt_rpc_channel.send_command.call_count == 0

    # Verify cache was loaded from storage
    assert home_trait.home_map_info == {0: CombinedMapInfo(map_flag=0, name="Dummy", rooms=[])}
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0}
    map_0_content = home_trait.home_map_content[0]
    assert map_0_content is not None
    assert map_0_content.image_content == TEST_IMAGE_CONTENT_1
    assert map_0_content.map_data is not None


async def test_existing_home_cache_invalid_bytes(
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test that discovery is skipped when cache already exists."""
    # Pre-populate the cache.
    cache_data = await device_cache.get()
    cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Dummy", rooms=[])}
    # We override the map bytes parser to raise an exception above.
    cache_data.home_map_content_base64 = {0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode("utf-8")}
    await device_cache.set(cache_data)

    # Setup mocks for the discovery process
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for the single map
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,  # Single map list
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,  # Map bytes for the single map
    ]

    # Call discover_home. First attempt raises an exception then loading from the server
    # produes a valid result.
    with patch(
        "roborock.devices.traits.v1.map_content.MapParser.parse",
        side_effect=[
            RoborockException("Invalid map bytes"),
            ParsedMapData(
                image_content=TEST_IMAGE_CONTENT_2,
                map_data=MagicMock(image=MagicMock(is_empty=False)),
            ),
        ],
    ):
        await home_trait.discover_home()

    # Verify cache was loaded from storage. The map was re-fetched from storage.
    assert home_trait.home_map_info
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_info[0].name == "Only Floor"
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0}
    map_0_content = home_trait.home_map_content[0]
    assert map_0_content is not None
    assert map_0_content.image_content == TEST_IMAGE_CONTENT_2
    assert map_0_content.map_data is not None


async def test_discover_home_no_maps(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
) -> None:
    """Test discovery when no maps are available."""
    # Setup mock to return empty maps list
    mock_mqtt_rpc_channel.send_command.side_effect = [
        # Discover home
        [{"max_multi_map": 0, "max_bak_map": 0, "multi_map_count": 0, "map_info": []}],
        # Refresh
        [{"max_multi_map": 0, "max_bak_map": 0, "multi_map_count": 0, "map_info": []}],
    ]

    # Discover home should not change anything
    await home_trait.discover_home()
    assert home_trait.current_map_data is None
    assert home_trait.home_map_info == {}
    assert home_trait.home_map_content == {}
    assert home_trait.current_rooms == []

    # Refresh should not change anything
    await home_trait.refresh()
    assert home_trait.current_map_data is None
    assert home_trait.home_map_info == {}
    assert home_trait.home_map_content == {}
    assert home_trait.current_rooms == []


async def test_refresh_updates_current_map_cache(
    device_cache: DeviceCache,
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test that refresh updates the cache for the current map."""
    # Pre-populate cache with some data
    cache_data = await device_cache.get()
    cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Old Ground Floor", rooms=[])}
    cache_data.home_map_content_base64 = {
        0: base64.b64encode(MAP_BYTES_RESPONSE_2).decode()
    }  # Pre-existing different map bytes
    await device_cache.set(cache_data)
    await home_trait.discover_home()  # Load cache into trait
    # Verify initial cache state
    assert home_trait.home_map_info
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_info[0].name == "Old Ground Floor"
    assert len(home_trait.home_map_info[0].rooms) == 0
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0}
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_2

    # Setup mocks for refresh
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Room mapping refresh
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Maps refresh
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,  # Map bytes refresh
    ]

    # Perform refresh
    await home_trait.refresh()

    # Verify cache was updated for current map
    assert home_trait.home_map_info
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_info[0].name == "Ground Floor"
    assert len(home_trait.home_map_info[0].rooms) == 2
    # Verify map content
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0}
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1


async def test_current_map_data_property(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test current_map_data property returns correct data."""
    # Setup discovery
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,  # Status right after switching to map 123
        UPDATED_STATUS_MAP_123,  # Status once map 123 has loaded
        ROOM_MAPPING_DATA_MAP_123,  # Rooms for map 123
        UPDATED_STATUS_MAP_0,  # Status right after switching back to map 0
        UPDATED_STATUS_MAP_0,  # Status once map 0 has loaded
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for map 0
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Multi maps list
        {},  # LOAD_MULTI_MAP response for map 123
        {},  # LOAD_MULTI_MAP response back to map 0
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_2,  # Map bytes for 123
        MAP_BYTES_RESPONSE_1,  # Map bytes for 0
    ]

    await home_trait.discover_home()

    # Test current map data (should be map 0)
    current_data = home_trait.current_map_data
    assert current_data is not None
    assert current_data.map_flag == 0
    assert current_data.name == "Ground Floor"

    # Test when no cache exists
    home_trait._home_map_info = None
    assert home_trait.current_map_data is None


async def test_discover_home_device_busy_cleaning(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    device_cache: DeviceCache,
) -> None:
    """Test that discovery raises RoborockDeviceBusy when device is cleaning.

    This tests the initial failure scenario during discovery where the device
    is busy, then a retry attempt where the device is still busy, then finally
    a successful attempt to run discovery when the device is idle.
    """
    # Set the status trait state to cleaning
    status_trait.state = RoborockStateCode.cleaning

    # Attempt to discover home while cleaning
    with pytest.raises(RoborockDeviceBusy, match="Cannot perform home discovery while the device is busy"):
        await home_trait.discover_home()

    # Verify no RPC calls were made (discovery was prevented)
    assert mock_rpc_channel.send_command.call_count == 0
    assert mock_mqtt_rpc_channel.send_command.call_count == 0

    # Setup mocks for refresh
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Room mapping refresh
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Maps refresh
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,  # Map bytes refresh
    ]

    # Now attempt to refresh the device while cleaning. This should still fail
    # home discovery but allow refresh to update the current map.
    await home_trait.refresh()

    # Verify the home information is now populated
    current_data = home_trait.current_map_data
    assert current_data is not None
    assert current_data.map_flag == 0
    assert current_data.name == "Ground Floor"
    assert home_trait.home_map_info is not None
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_content is not None
    assert home_trait.home_map_content.keys() == {0}
    assert [room.name for room in home_trait.current_rooms] == [
        "Example room 1",
        "Example room 2",
    ]

    map_0_content = home_trait.home_map_content[0]
    assert map_0_content is not None
    assert map_0_content.image_content == TEST_IMAGE_CONTENT_1
    assert map_0_content.map_data is not None

    # Verify the persistent cache has not been updated since discovery
    # has not fully completed.
    cache_data = await device_cache.get()
    assert not cache_data.home_map_info
    assert not cache_data.home_map_content_base64

    # Set the status trait state to idle which will mean we can attempt discovery
    # on the next refresh. This should have the result of updating the
    # persistent cache which is verified below.
    status_trait.state = RoborockStateCode.idle

    # Setup mocks for the discovery process
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,  # Status right after switching to map 123
        UPDATED_STATUS_MAP_123,  # Status once map 123 has loaded
        ROOM_MAPPING_DATA_MAP_123,  # Rooms for map 123
        UPDATED_STATUS_MAP_0,  # Status right after switching back to map 0
        UPDATED_STATUS_MAP_0,  # Status once map 0 has loaded
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for map 0
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Multi maps list
        {},  # LOAD_MULTI_MAP response for map 123
        {},  # LOAD_MULTI_MAP response back to map 0
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_2,  # Map bytes for 123
        MAP_BYTES_RESPONSE_1,  # Map bytes for 0
    ]

    # Refreshing should now perform discovery successfully
    await home_trait.refresh()

    # Verify we now have all of the information populated from discovery
    assert home_trait.home_map_info is not None
    assert home_trait.home_map_info.keys() == {0, 123}
    assert home_trait.home_map_content is not None
    assert home_trait.home_map_content.keys() == {0, 123}
    assert [room.name for room in home_trait.current_rooms] == [
        "Room 16",
        "Room 17",
    ]

    # Verify the persistent cache has been updated
    device_cache_data = await device_cache.get()
    assert device_cache_data.home_map_info is not None
    assert len(device_cache_data.home_map_info) == 2
    assert device_cache_data.home_map_content_base64 is not None
    assert len(device_cache_data.home_map_content_base64) == 2


async def test_refresh_falls_back_when_map_switch_action_locked(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    device_cache: DeviceCache,
) -> None:
    """Test that refresh falls back to current map when map switching is locked."""
    # Discovery attempt: we can list maps, but switching maps fails with -10007.
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,  # Maps refresh during discover_home()
        RoborockInvalidStatus({"code": -10007, "message": "invalid status"}),  # LOAD_MULTI_MAP action locked
        MULTI_MAP_LIST_DATA,  # Maps refresh during refresh() fallback
    ]

    # Fallback refresh should still be able to refresh the current map.
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for current map
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,  # Map bytes for current map
    ]

    await home_trait.refresh()

    current_data = home_trait.current_map_data
    assert current_data is not None
    assert current_data.map_flag == 0
    assert current_data.name == "Ground Floor"

    assert home_trait.home_map_info is not None
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_content is not None
    assert home_trait.home_map_content.keys() == {0}
    map_0_content = home_trait.home_map_content[0]
    assert map_0_content.image_content == TEST_IMAGE_CONTENT_1

    # Discovery did not complete, so the persistent cache should not be updated.
    cache_data = await device_cache.get()
    assert not cache_data.home_map_info
    assert not cache_data.home_map_content_base64


async def test_single_map_no_switching(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test that single map discovery doesn't trigger map switching."""
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for the single map
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,  # Single map list
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,  # Map bytes for the single map
    ]

    await home_trait.discover_home()

    # Verify cache is populated
    assert home_trait.home_map_info is not None
    assert home_trait.home_map_info.keys() == {0}
    assert home_trait.home_map_content is not None
    assert home_trait.home_map_content.keys() == {0}

    # Verify no LOAD_MULTI_MAP commands were sent (no map switching)
    load_map_calls = [
        call
        for call in mock_mqtt_rpc_channel.send_command.call_args_list
        if call[1].get("command") == RoborockCommand.LOAD_MULTI_MAP
    ]
    assert len(load_map_calls) == 0


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("map_flag", [0, 123])
@pytest.mark.parametrize(
    "state", [RoborockStateCode.idle, RoborockStateCode.charging, RoborockStateCode.charging_complete]
)
async def test_missing_selected_map_recovery(
    cached: bool,
    map_flag: int,
    state: RoborockStateCode,
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Reload a missing selected map before fetching its image, including map flag zero."""
    if cached:
        cache_data = await device_cache.get()
        cache_data.home_map_info = {map_flag: CombinedMapInfo(map_flag=map_flag, name="Only Floor", rooms=[])}
        await device_cache.set(cache_data)
        await home_trait.discover_home()

    status_trait.state = state
    status_trait.map_present = 0
    status_trait.map_status = map_flag * 4 + 3

    def mqtt_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_MULTI_MAPS_LIST:
            return [{"multi_map_count": 1, "map_info": [{"mapFlag": map_flag, "name": "Only Floor"}]}]
        assert command == RoborockCommand.LOAD_MULTI_MAP
        assert params == [map_flag]
        return {}

    def rpc_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_STATUS:
            return {**UPDATED_STATUS_MAP_0, "map_status": map_flag * 4 + 3}
        assert command == RoborockCommand.GET_ROOM_MAPPING
        return ROOM_MAPPING_DATA_MAP_0

    mock_mqtt_rpc_channel.send_command.side_effect = mqtt_response
    mock_rpc_channel.send_command.side_effect = rpc_response

    def map_response(command: RoborockCommand, params: object = None) -> bytes:
        # Model the reported device: the image is a placeholder until LOAD_MULTI_MAP.
        if call(RoborockCommand.LOAD_MULTI_MAP, params=[map_flag]) in mock_mqtt_rpc_channel.send_command.call_args_list:
            return MAP_BYTES_RESPONSE_1
        return MAP_BYTES_RESPONSE_2

    mock_map_rpc_channel.send_command.side_effect = map_response

    await home_trait.refresh()

    assert home_trait.home_map_content
    assert home_trait.home_map_content[map_flag].image_content == TEST_IMAGE_CONTENT_1
    assert home_trait.current_map_data
    assert home_trait.current_map_data.map_flag == map_flag
    mock_mqtt_rpc_channel.send_command.assert_has_calls(
        [call(RoborockCommand.GET_MULTI_MAPS_LIST), call(RoborockCommand.LOAD_MULTI_MAP, params=[map_flag])]
    )
    mock_rpc_channel.send_command.assert_has_calls(
        [call(RoborockCommand.GET_STATUS), call(RoborockCommand.GET_ROOM_MAPPING)]
    )

    # A successful reload refreshes status, so the next poll must not reload again.
    await home_trait.refresh()
    assert (
        mock_mqtt_rpc_channel.send_command.call_args_list.count(call(RoborockCommand.LOAD_MULTI_MAP, params=[map_flag]))
        == 1
    )


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize(
    ("state", "map_present", "in_cleaning", "in_returning", "map_status"),
    [
        (RoborockStateCode.charging, 1, 0, 0, 3),
        (RoborockStateCode.charging, None, 0, 0, 3),
        (RoborockStateCode.charging, 0, 1, 0, 3),
        (RoborockStateCode.charging, 0, 2, 0, 3),
        (RoborockStateCode.charging, 0, 3, 0, 3),
        (RoborockStateCode.charging, 0, 0, 1, 3),
        (RoborockStateCode.cleaning, 0, 0, 0, 3),
        (RoborockStateCode.returning_home, 0, 0, 0, 3),
        (RoborockStateCode.paused, 0, 0, 0, 3),
        (RoborockStateCode.mapping, 0, 0, 0, 3),
        (RoborockStateCode.washing_the_mop, 0, 0, 0, 3),
        (RoborockStateCode.unknown, 0, 0, 0, 3),
        (None, 0, 0, 0, 3),
        (RoborockStateCode.charging, 0, 0, 0, None),
        (RoborockStateCode.charging, 0, 0, 0, 123 * 4 + 3),
    ],
)
async def test_missing_selected_map_recovery_guards(
    cached: bool,
    state: RoborockStateCode | None,
    map_present: int | None,
    in_cleaning: int,
    in_returning: int,
    map_status: int | None,
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Avoid automatic map loading when unnecessary, unsafe, or no saved selection exists."""
    if cached:
        cache_data = await device_cache.get()
        cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Only Floor", rooms=[])}
        await device_cache.set(cache_data)
        await home_trait.discover_home()

    status_trait.state = state
    status_trait.map_present = map_present
    status_trait.in_cleaning = RoborockInCleaning(in_cleaning)
    status_trait.in_returning = in_returning
    status_trait.map_status = map_status
    mock_mqtt_rpc_channel.send_command.side_effect = [MULTI_MAP_LIST_SINGLE_MAP_DATA]
    mock_rpc_channel.send_command.side_effect = [ROOM_MAPPING_DATA_MAP_0]
    mock_map_rpc_channel.send_command.return_value = MAP_BYTES_RESPONSE_1

    await home_trait.refresh()

    mock_mqtt_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_MULTI_MAPS_LIST)
    if map_status == 3:
        # Busy devices can still have their map read without loading it.
        mock_map_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_MAP_V1)
        assert home_trait.home_map_content
        assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1
    else:
        mock_map_rpc_channel.send_command.assert_not_called()


async def test_missing_map_reload_action_locked(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Expose a rejected recovery as a busy device so callers can defer discovery."""
    status_trait.map_present = 0
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,
        RoborockInvalidStatus({"code": -10007, "message": "invalid status"}),
    ]

    with pytest.raises(RoborockDeviceBusy) as exc_info:
        await home_trait.discover_home()

    assert isinstance(exc_info.value.__cause__, RoborockInvalidStatus)
    mock_map_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize("cached", [False, True])
async def test_refresh_missing_map_reload_action_locked(
    cached: bool,
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """A rejected reload falls back to reading without retrying the same command."""
    if cached:
        cache_data = await device_cache.get()
        cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Only Floor", rooms=[])}
        await device_cache.set(cache_data)
        await home_trait.discover_home()

    status_trait.map_present = 0
    responses = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,
        RoborockInvalidStatus({"code": -10007, "message": "invalid status"}),
    ]
    if not cached:
        responses.append(MULTI_MAP_LIST_SINGLE_MAP_DATA)
    mock_mqtt_rpc_channel.send_command.side_effect = responses
    mock_rpc_channel.send_command.side_effect = [ROOM_MAPPING_DATA_MAP_0]
    mock_map_rpc_channel.send_command.return_value = MAP_BYTES_RESPONSE_1

    await home_trait.refresh()

    assert (
        mock_mqtt_rpc_channel.send_command.call_args_list.count(call(RoborockCommand.LOAD_MULTI_MAP, params=[0])) == 1
    )
    mock_map_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_MAP_V1)
    assert home_trait.home_map_content
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("previous_map", [None, MAP_BYTES_RESPONSE_1])
async def test_empty_map_does_not_replace_saved_map(
    cached: bool,
    previous_map: bytes | None,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Discovery and refresh never persist a placeholder in place of a usable map."""
    if cached:
        cache_data = await device_cache.get()
        cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Only Floor", rooms=[])}
        if previous_map is not None:
            cache_data.home_map_content_base64 = {0: base64.b64encode(previous_map).decode()}
        await device_cache.set(cache_data)
        await home_trait.discover_home()

    mock_mqtt_rpc_channel.send_command.side_effect = [MULTI_MAP_LIST_SINGLE_MAP_DATA, MULTI_MAP_LIST_SINGLE_MAP_DATA]
    mock_rpc_channel.send_command.side_effect = [ROOM_MAPPING_DATA_MAP_0, ROOM_MAPPING_DATA_MAP_0]
    mock_map_rpc_channel.send_command.side_effect = [EMPTY_MAP_BYTES, MAP_BYTES_RESPONSE_2]

    await home_trait.refresh()

    cache_data = await device_cache.get()
    expected = {0: base64.b64encode(previous_map).decode()} if cached and previous_map else {}
    assert (cache_data.home_map_content_base64 or {}) == expected
    assert home_trait.home_map_content is not None
    if cached and previous_map:
        assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1
    else:
        assert home_trait.home_map_content == {}

    # A later real map replaces the empty response and is cached normally.
    await home_trait.refresh()
    cache_data = await device_cache.get()
    assert cache_data.home_map_content_base64 == {0: base64.b64encode(MAP_BYTES_RESPONSE_2).decode()}
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_2


@dataclass
class TwoFloorDevice:
    """State of the simulated vacuum set up by `simulate_two_floor_device`."""

    map_bytes: dict[int, bytes]
    status_lags: bool = False
    map_flag: int = 0
    status_stale: bool = False
    loaded_maps: list[int] = field(default_factory=list)

    def load(self, map_flag: int) -> None:
        """Record a LOAD_MULTI_MAP command."""
        self.map_flag = map_flag
        self.status_stale = self.status_lags
        self.loaded_maps.append(map_flag)


def simulate_two_floor_device(
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    map_bytes: dict[int, bytes],
    *,
    status_lags: bool = False,
) -> TwoFloorDevice:
    """Answer commands like a vacuum with floors 0 and 123 that serves the given map bytes per floor.

    With `status_lags` the first status read after a map load still reports no map present,
    as a vacuum can do while the map is loading.
    """
    device = TwoFloorDevice(map_bytes=map_bytes, status_lags=status_lags)

    def mqtt_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_MULTI_MAPS_LIST:
            return MULTI_MAP_LIST_DATA
        assert command == RoborockCommand.LOAD_MULTI_MAP
        assert isinstance(params, list)
        device.load(params[0])
        return {}

    def rpc_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_STATUS:
            map_present = 0 if device.status_stale else 1
            device.status_stale = False
            return {**UPDATED_STATUS_MAP_0, "map_status": device.map_flag * 4 + 3, "map_present": map_present}
        assert command == RoborockCommand.GET_ROOM_MAPPING
        return ROOM_MAPPING_DATA_MAP_0 if device.map_flag == 0 else ROOM_MAPPING_DATA_MAP_123

    def map_response(command: RoborockCommand, params: object = None) -> bytes:
        return device.map_bytes[device.map_flag]

    mock_mqtt_rpc_channel.send_command.side_effect = mqtt_response
    mock_rpc_channel.send_command.side_effect = rpc_response
    mock_map_rpc_channel.send_command.side_effect = map_response
    return device


async def seed_cache_with_placeholder(device_cache: DeviceCache) -> None:
    """Cache two floors the way an older library version left them: floor 0 holds a "NO MAP" placeholder."""
    cache_data = await device_cache.get()
    cache_data.home_map_info = {
        0: CombinedMapInfo(map_flag=0, name="Ground Floor", rooms=[]),
        123: CombinedMapInfo(map_flag=123, name="Second Floor", rooms=[]),
    }
    cache_data.home_map_content_base64 = {
        0: base64.b64encode(EMPTY_MAP_BYTES).decode(),
        123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode(),
    }
    await device_cache.set(cache_data)


async def test_discover_rediscovers_previously_cached_empty_map(
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """A placeholder cached by an earlier library version is replaced by a real map on an idle device."""
    await seed_cache_with_placeholder(device_cache)
    device = simulate_two_floor_device(
        mock_rpc_channel,
        mock_mqtt_rpc_channel,
        mock_map_rpc_channel,
        {0: MAP_BYTES_RESPONSE_1, 123: MAP_BYTES_RESPONSE_2},
    )

    await home_trait.discover_home()

    assert device.loaded_maps == [123, 0]
    assert home_trait.home_map_content
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1
    assert home_trait.home_map_content[123].image_content == TEST_IMAGE_CONTENT_2
    cache_data = await device_cache.get()
    assert cache_data.home_map_content_base64 == {
        0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode(),
        123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode(),
    }


async def test_placeholder_rediscovery_resumes_after_busy(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """A floor cached as a placeholder is rediscovered by the first idle refresh after a busy one."""
    await seed_cache_with_placeholder(device_cache)
    cache_before = copy.deepcopy(await device_cache.get())
    device = simulate_two_floor_device(
        mock_rpc_channel,
        mock_mqtt_rpc_channel,
        mock_map_rpc_channel,
        {0: EMPTY_MAP_BYTES, 123: MAP_BYTES_RESPONSE_2},
    )

    # While cleaning, no map is loaded. The good cached floor stays available, and the
    # saved cache is left exactly as it was so the missing floor is still owed.
    status_trait.state = RoborockStateCode.cleaning
    await home_trait.refresh()

    assert device.loaded_maps == []
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {123}
    assert home_trait.home_map_content[123].image_content == TEST_IMAGE_CONTENT_2
    assert await device_cache.get() == cache_before

    # The next refresh finds the vacuum idle and discovers the missing floor.
    status_trait.state = RoborockStateCode.charging
    device.map_bytes[0] = MAP_BYTES_RESPONSE_1
    await home_trait.refresh()

    assert device.loaded_maps == [123, 0]
    assert home_trait.home_map_content.keys() == {0, 123}
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1
    assert home_trait.home_map_content[123].image_content == TEST_IMAGE_CONTENT_2
    cache_data = await device_cache.get()
    assert cache_data.home_map_content_base64 == {
        0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode(),
        123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode(),
    }

    # Discovery is complete, so later refreshes load nothing.
    await home_trait.refresh()
    assert device.loaded_maps == [123, 0]


async def test_placeholder_rediscovery_waits_for_current_map(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Rediscovery that cannot start for lack of a current map leaves the saved home alone and stays pending."""
    await seed_cache_with_placeholder(device_cache)
    cache_before = copy.deepcopy(await device_cache.get())
    device = simulate_two_floor_device(
        mock_rpc_channel,
        mock_mqtt_rpc_channel,
        mock_map_rpc_channel,
        {0: MAP_BYTES_RESPONSE_1, 123: MAP_BYTES_RESPONSE_2},
    )
    two_floor_response = mock_mqtt_rpc_channel.send_command.side_effect

    # The vacuum temporarily reports no maps. Nothing is loaded and the saved home is untouched.
    mock_mqtt_rpc_channel.send_command.side_effect = None
    mock_mqtt_rpc_channel.send_command.return_value = [
        {"max_multi_map": 0, "max_bak_map": 0, "multi_map_count": 0, "map_info": []}
    ]
    with pytest.raises(RoborockDeviceBusy):
        await home_trait.discover_home()
    await home_trait.refresh()

    assert device.loaded_maps == []
    assert await device_cache.get() == cache_before

    # Floor 123 becomes the current map. The next ordinary refresh rediscovers the other floor.
    mock_mqtt_rpc_channel.send_command.side_effect = two_floor_response
    status_trait.map_status = 123 * 4 + 3
    device.map_flag = 123
    await home_trait.refresh()

    assert device.loaded_maps == [0, 123]
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0, 123}
    assert home_trait.home_map_content[0].image_content == TEST_IMAGE_CONTENT_1
    cache_data = await device_cache.get()
    assert cache_data.home_map_content_base64 == {
        0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode(),
        123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode(),
    }

    # Discovery is complete, so later refreshes load nothing.
    await home_trait.refresh()
    assert device.loaded_maps == [0, 123]


async def test_rediscovery_keeps_good_cached_map_when_device_answers_placeholder(
    home_trait: HomeTrait,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """A floor that answers rediscovery with a placeholder keeps its last good cached image."""
    await seed_cache_with_placeholder(device_cache)
    simulate_two_floor_device(
        mock_rpc_channel,
        mock_mqtt_rpc_channel,
        mock_map_rpc_channel,
        {0: MAP_BYTES_RESPONSE_1, 123: EMPTY_MAP_BYTES},
    )

    await home_trait.discover_home()

    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0, 123}
    assert home_trait.home_map_content[123].image_content == TEST_IMAGE_CONTENT_2
    cache_data = await device_cache.get()
    assert cache_data.home_map_content_base64 == {
        0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode(),
        123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode(),
    }


async def test_missing_map_recovery_reads_status_after_loading(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """The status read right after a reload still shows no map, so a later read must settle it."""
    status_trait.map_present = 0
    still_loading = {**UPDATED_STATUS_MAP_0, "map_present": 0}
    loaded = {**UPDATED_STATUS_MAP_0, "map_present": 1}
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,
        {},  # LOAD_MULTI_MAP
        MULTI_MAP_LIST_SINGLE_MAP_DATA,
    ]
    mock_rpc_channel.send_command.side_effect = [
        still_loading,  # Status right after LOAD_MULTI_MAP
        loaded,  # Status once the map has loaded
        ROOM_MAPPING_DATA_MAP_0,
        ROOM_MAPPING_DATA_MAP_0,
    ]
    mock_map_rpc_channel.send_command.return_value = MAP_BYTES_RESPONSE_1

    await home_trait.refresh()
    assert status_trait.map_present == 1

    await home_trait.refresh()

    assert (
        mock_mqtt_rpc_channel.send_command.call_args_list.count(call(RoborockCommand.LOAD_MULTI_MAP, params=[0])) == 1
    )


async def test_multi_map_discovery_reads_status_after_loading(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Discovery leaves a settled status behind, so the next refresh does not reload the current map."""
    device = simulate_two_floor_device(
        mock_rpc_channel,
        mock_mqtt_rpc_channel,
        mock_map_rpc_channel,
        {0: MAP_BYTES_RESPONSE_1, 123: MAP_BYTES_RESPONSE_2},
        status_lags=True,
    )

    await home_trait.discover_home()
    assert status_trait.map_present == 1

    await home_trait.refresh()

    assert device.loaded_maps == [123, 0]


async def test_multi_map_discovery_does_not_reload_twice(
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """An explicit discovery switch is sufficient even when status still reports no map."""

    def mqtt_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_MULTI_MAPS_LIST:
            return MULTI_MAP_LIST_DATA
        assert command == RoborockCommand.LOAD_MULTI_MAP
        return {}

    def rpc_response(command: RoborockCommand, params: object = None) -> object:
        if command == RoborockCommand.GET_STATUS:
            map_flag = mock_mqtt_rpc_channel.send_command.call_args.kwargs["params"][0]
            return {**UPDATED_STATUS_MAP_0, "map_status": map_flag * 4 + 3, "map_present": 0}
        assert command == RoborockCommand.GET_ROOM_MAPPING
        return ROOM_MAPPING_DATA_MAP_0 if status_trait.current_map == 0 else ROOM_MAPPING_DATA_MAP_123

    mock_mqtt_rpc_channel.send_command.side_effect = mqtt_response
    mock_rpc_channel.send_command.side_effect = rpc_response
    mock_map_rpc_channel.send_command.side_effect = [MAP_BYTES_RESPONSE_2, MAP_BYTES_RESPONSE_1]

    await home_trait.discover_home()

    assert mock_mqtt_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.GET_MULTI_MAPS_LIST),
        call(RoborockCommand.LOAD_MULTI_MAP, params=[123]),
        call(RoborockCommand.LOAD_MULTI_MAP, params=[0]),
    ]
    assert home_trait.home_map_content
    assert home_trait.home_map_content.keys() == {0, 123}


async def test_refresh_map_info_prefers_map_info_names_and_adds_missing_rooms(
    home_trait: HomeTrait,
    rooms_trait: RoomsTrait,
) -> None:
    """Test room merge behavior in _refresh_map_info.

    This test verifies:
    1. Existing map_info room names are preserved.
    2. Missing rooms from RoomsTrait are added.
    3. map_info fallback names are replaced by RoomsTrait names.
    """
    map_info = MultiMapsListMapInfo(
        map_flag=0,
        name="Test Map",
        rooms=[
            MultiMapsListRoom(
                id=16,
                iot_name_id="2362048",
                iot_name="Kitchen from map_info",
            ),
            MultiMapsListRoom(
                id=19,
                iot_name_id="2362042",
                iot_name="Bedroom from map_info",
            ),
            MultiMapsListRoom(
                id=20,
                iot_name_id="9999001",
                iot_name=None,
            ),
        ],
    )

    # Mock rooms_trait to return multiple rooms covering all scenarios:
    # - segment_id 16 with fallback name: exists in map_info, should NOT override
    # - segment_id 19 with valid name: exists in map_info, should NOT override
    # - segment_id 17 with fallback name: not in map_info, should be added
    # - segment_id 18 with valid name: not in map_info, should be added
    # - segment_id 20 with valid name: overrides map_info fallback "Room 20"
    rooms_trait.rooms = [
        NamedRoomMapping(segment_id=16, iot_id="2362048"),  # Will override even with no name
        NamedRoomMapping(
            segment_id=19, iot_id="2362042", raw_name="Updated Bedroom Name"
        ),  # Exists in map_info, should not override
        NamedRoomMapping(segment_id=17, iot_id="2362044"),  # Not in map_info, should be added
        NamedRoomMapping(
            segment_id=18, iot_id="2362041", raw_name="Example room 3"
        ),  # Not in map_info, should be added
        NamedRoomMapping(segment_id=20, iot_id="9999001", raw_name="Office from rooms_trait"),
    ]

    # Mock rooms_trait.refresh to prevent actual device calls
    with patch.object(rooms_trait, "refresh", new_callable=AsyncMock):
        result = await home_trait._refresh_map_info(map_info)

    assert result.map_flag == 0
    assert result.name == "Test Map"
    assert len(result.rooms) == 5

    # Sort rooms by segment_id for consistent assertions
    sorted_rooms = sorted(result.rooms, key=lambda r: r.segment_id)

    # Room 16: from map_info is overridden by rooms_trait
    assert sorted_rooms[0].segment_id == 16
    assert sorted_rooms[0].name == "Room 16"
    assert sorted_rooms[0].iot_id == "2362048"

    # Room 17: from rooms_trait with fallback name, added because not in map_info
    assert sorted_rooms[1].segment_id == 17
    assert sorted_rooms[1].name == "Room 17"
    assert sorted_rooms[1].iot_id == "2362044"

    # Room 18: from rooms_trait with valid name, added because not in map_info
    assert sorted_rooms[2].segment_id == 18
    assert sorted_rooms[2].name == "Example room 3"
    assert sorted_rooms[2].iot_id == "2362041"

    # Room 19: from map_info, kept (not overridden by rooms_trait)
    assert sorted_rooms[3].segment_id == 19
    assert sorted_rooms[3].name == "Updated Bedroom Name"
    assert sorted_rooms[3].iot_id == "2362042"

    # Room 20: map_info fallback name replaced by rooms_trait name
    assert sorted_rooms[4].segment_id == 20
    assert sorted_rooms[4].name == "Office from rooms_trait"
    assert sorted_rooms[4].iot_id == "9999001"


async def test_home_trait_listener_notifications(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    device_cache: DeviceCache,
    web_api_client: AsyncMock,
) -> None:
    """Test that listener callbacks are called when home discovery/updates occur."""
    mock_callback = MagicMock()
    unsub = home_trait.add_update_listener(mock_callback)
    # Callback should NOT be executed immediately on subscription since home_map_info is None
    assert mock_callback.call_count == 0

    # 1. Test notification on empty cache discovery
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,
        UPDATED_STATUS_MAP_123,
        ROOM_MAPPING_DATA_MAP_123,
        UPDATED_STATUS_MAP_0,
        UPDATED_STATUS_MAP_0,
        ROOM_MAPPING_DATA_MAP_0,
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,
        {},
        {},
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_2,
        MAP_BYTES_RESPONSE_1,
    ]
    web_api_client.get_rooms.return_value = [
        HomeDataRoom(id=2362048, name="Example room 1"),
        HomeDataRoom(id=2362044, name="Example room 2"),
    ]

    await home_trait.discover_home()
    # Mock callback should have been called during discovery
    assert mock_callback.call_count > 0
    mock_callback.reset_mock()

    # 2. Test that registering a new listener now (when cache is populated) executes immediately
    mock_callback_immediate = MagicMock()
    unsub_immediate = home_trait.add_update_listener(mock_callback_immediate)
    assert mock_callback_immediate.call_count == 1
    unsub_immediate()

    # 3. Test notification on cached discovery
    # Re-run discover_home (which skips API calls and loads from cache)
    await home_trait.discover_home()
    assert mock_callback.call_count == 1
    mock_callback.reset_mock()

    # 4. Test notification on refresh
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,
    ]
    await home_trait.refresh()
    assert mock_callback.call_count > 0

    # Unsubscribe and verify it is no longer called
    mock_callback.reset_mock()
    unsub()
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_DATA,
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,
    ]
    await home_trait.refresh()
    assert mock_callback.call_count == 0


async def test_home_trait_map_eviction(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    device_cache: DeviceCache,
    web_api_client: AsyncMock,
) -> None:
    """Test that maps deleted from the device are evicted from cache during refresh."""
    # Pre-populate cache with maps 0 and 123
    device_cache_data = DeviceCacheData(
        home_map_info={
            0: CombinedMapInfo(map_flag=0, name="Ground Floor", rooms=[]),
            123: CombinedMapInfo(map_flag=123, name="Second Floor", rooms=[]),
        },
        home_map_content_base64={
            0: base64.b64encode(MAP_BYTES_RESPONSE_1).decode("utf-8"),
            123: base64.b64encode(MAP_BYTES_RESPONSE_2).decode("utf-8"),
        },
    )
    await device_cache.set(device_cache_data)
    await home_trait.discover_home()

    assert home_trait.home_map_info is not None
    assert home_trait.home_map_content is not None
    assert len(home_trait.home_map_info) == 2
    assert len(home_trait.home_map_content) == 2

    # Set up listener callback
    mock_callback = MagicMock()
    home_trait.add_update_listener(mock_callback)
    assert mock_callback.call_count == 1
    mock_callback.reset_mock()

    # Mock maps_trait.refresh so that only map 0 is returned (map 123 deleted)
    mock_mqtt_rpc_channel.send_command.side_effect = [
        MULTI_MAP_LIST_SINGLE_MAP_DATA,  # Only has map 0
    ]
    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,
    ]
    mock_map_rpc_channel.send_command.side_effect = [
        MAP_BYTES_RESPONSE_1,
    ]

    await home_trait.refresh()

    # Verify map 123 is excluded from memory cache
    assert home_trait.home_map_info is not None
    assert home_trait.home_map_content is not None
    assert 123 not in home_trait.home_map_info
    assert 123 not in home_trait.home_map_content
    assert 0 in home_trait.home_map_info

    # Verify listener notified
    assert mock_callback.call_count > 0

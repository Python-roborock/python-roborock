"""Tests for the Home related functionality."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from roborock.data.containers import CombinedMapInfo
from roborock.data.v1.v1_code_mappings import RoborockStateCode
from roborock.devices.cache import InMemoryCache
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.home import HomeTrait
from roborock.devices.traits.v1.map_content import MapContentTrait
from roborock.devices.traits.v1.maps import MapsTrait
from roborock.devices.traits.v1.rooms import RoomsTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockDeviceBusy
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


@pytest.fixture
def cache():
    """Create an in-memory cache for testing."""
    return InMemoryCache()


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
    """Create a MapsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.map_content


@pytest.fixture
def rooms_trait(device: RoborockDevice) -> RoomsTrait:
    """Create a RoomsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.rooms


@pytest.fixture
def home_trait(
    status_trait: StatusTrait, maps_trait: MapsTrait, map_content_trait: MapContentTrait, rooms_trait: RoomsTrait, cache
) -> HomeTrait:
    """Create a HomeTrait instance with mocked dependencies."""
    return HomeTrait(status_trait, maps_trait, map_content_trait, rooms_trait, cache)


@pytest.fixture(autouse=True)
def map_parser_fixture() -> Iterator[None]:
    """Create a MapContentTrait instance with mocked dependencies."""

    def parse_data(response: bytes) -> ParsedMapData:
        if image_content := TEST_PARSER_MAP.get(response):
            return ParsedMapData(
                image_content=image_content,
                map_data=MagicMock(),
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
) -> None:
    """Test discovering home when cache is empty."""
    # Setup mocks for the discovery process
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,  # Status after switching to map 123
        ROOM_MAPPING_DATA_MAP_123,  # Rooms for map 123
        UPDATED_STATUS_MAP_0,  # Status after switching back to map 0
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
    assert map_0_data.rooms[0].name == "Example room 1"
    assert map_0_data.rooms[1].segment_id == 17
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
    assert map_123_data.rooms[0].name == "Example room 3"
    assert map_123_data.rooms[1].segment_id == 19
    assert map_123_data.rooms[1].name == "Unknown"  # Not in mock home data

    map_123_content = home_trait.home_map_content[123]
    assert map_123_content is not None
    assert map_123_content.image_content == TEST_IMAGE_CONTENT_2
    assert map_123_content.map_data is not None

    # Verify current map data is accessible
    current_map_data = home_trait.current_map_data
    assert current_map_data is not None
    assert current_map_data.map_flag == 0
    assert current_map_data.name == "Ground Floor"


async def test_discover_home_with_existing_cache(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
) -> None:
    """Test that discovery is skipped when cache already exists."""
    # Pre-populate the cache
    cache_data = await home_trait._cache.get()
    cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Dummy", rooms=[])}
    cache_data.home_map_content = {0: MAP_BYTES_RESPONSE_1}
    await home_trait._cache.set(cache_data)

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


async def test_discover_home_no_maps(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
) -> None:
    """Test discovery when no maps are available."""
    # Setup mock to return empty maps list
    mock_mqtt_rpc_channel.send_command.side_effect = [
        [{"max_multi_map": 0, "max_bak_map": 0, "multi_map_count": 0, "map_info": []}]
    ]

    with pytest.raises(Exception, match="Cannot perform home discovery without current map info"):
        await home_trait.discover_home()


async def test_refresh_updates_current_map_cache(
    cache: InMemoryCache,
    status_trait: StatusTrait,
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test that refresh updates the cache for the current map."""
    # Pre-populate cache with some data
    cache_data = await cache.get()
    cache_data.home_map_info = {0: CombinedMapInfo(map_flag=0, name="Old Ground Floor", rooms=[])}
    cache_data.home_map_content = {0: MAP_BYTES_RESPONSE_2}  # Pre-existing different map bytes
    await cache.set(cache_data)
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


async def test_refresh_no_cache_no_update(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
) -> None:
    """Test that refresh doesn't update when no cache exists."""
    # Setup mocks for refresh
    # mock_mqtt_rpc_channel.send_command.side_effect = [
    #     MULTI_MAP_LIST_DATA,  # Maps refresh
    # ]
    # Perform refresh without existing cache
    with pytest.raises(Exception, match="Cannot refresh home data without home cache, did you call discover_home()?"):
        await home_trait.refresh()


async def test_current_map_data_property(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test current_map_data property returns correct data."""
    # Setup discovery
    mock_rpc_channel.send_command.side_effect = [
        UPDATED_STATUS_MAP_123,  # Status after switching to map 123
        ROOM_MAPPING_DATA_MAP_123,  # Rooms for map 123
        UPDATED_STATUS_MAP_0,  # Status after switching back to map 0
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
) -> None:
    """Test that discovery raises RoborockDeviceBusy when device is cleaning."""
    # Set the status trait state to cleaning
    status_trait.state = RoborockStateCode.cleaning

    # Attempt to discover home while cleaning
    with pytest.raises(RoborockDeviceBusy, match="Cannot perform home discovery while the device is cleaning"):
        await home_trait.discover_home()

    # Verify no RPC calls were made (discovery was prevented)
    assert mock_rpc_channel.send_command.call_count == 0
    assert mock_mqtt_rpc_channel.send_command.call_count == 0


async def test_single_map_no_switching(
    home_trait: HomeTrait,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
) -> None:
    """Test that single map discovery doesn't trigger map switching."""
    single_map_data = [
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

    mock_rpc_channel.send_command.side_effect = [
        ROOM_MAPPING_DATA_MAP_0,  # Rooms for the single map
    ]
    mock_mqtt_rpc_channel.send_command.side_effect = [
        single_map_data,  # Single map list
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

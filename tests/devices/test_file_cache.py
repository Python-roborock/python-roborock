"""Tests for the FileCache class."""

import json
import pathlib
import pickle
from unittest.mock import AsyncMock, patch

import pytest
from syrupy import SnapshotAssertion

from roborock.data import HomeData
from roborock.data.containers import CombinedMapInfo, NamedRoomMapping
from roborock.data.v1.v1_containers import NetworkInfo
from roborock.devices.cache import CacheData
from roborock.devices.file_cache import FileCache
from tests.mock_data import HOME_DATA_RAW
from tests.mock_data import NETWORK_INFO as NETWORK_INFO_RAW

HOME_DATA = HomeData.from_dict(HOME_DATA_RAW)
NETWORK_INFO = NetworkInfo.from_dict(NETWORK_INFO_RAW)


@pytest.fixture(name="cache_file")
def cache_file_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    """Fixture to provide a temporary cache file path."""
    return tmp_path / "test_cache.bin"


async def test_get_from_non_existent_cache(cache_file: pathlib.Path) -> None:
    """Test getting data when the cache file does not exist."""
    cache = FileCache(cache_file)
    data = await cache.get()
    assert isinstance(data, CacheData)
    assert data == CacheData()


@pytest.mark.parametrize(
    "initial_data",
    [
        CacheData(),
        CacheData(home_data=HOME_DATA),
        CacheData(
            home_data=HOME_DATA,
            network_info={"abc123": NETWORK_INFO},
            home_map_info={
                # Ensure that int keys are serialized and parsed correctly
                1: CombinedMapInfo(
                    map_flag=1,
                    name="Test Map",
                    rooms=[NamedRoomMapping(segment_id=1023, iot_id="4321", name="Living Room")],
                )
            },
        ),
    ],
    ids=["empty_cache", "populated_cache", "multiple_fields_cache"],
)
@pytest.mark.parametrize(
    ("init_args"),
    [
        # Default no arguments
        {},
        # Re-specify the default arguments explicitly
        {
            "serialize_fn": pickle.dumps,
            "deserialize_fn": pickle.loads,
        },
        # Use JSON serialization. We don't use this example directly in this library
        # but we establish it as an approach that can be used by clients with the
        # RoborockBase methods for serialization/deserialization.
        {
            "serialize_fn": lambda x: json.dumps(x.as_dict()).encode("utf-8"),
            "deserialize_fn": lambda b: CacheData.from_dict(json.loads(b.decode("utf-8"))),
        },
    ],
    ids=["default", "pickle", "json"],
)
async def test_set_and_flush_and_get(
    cache_file: pathlib.Path,
    initial_data: CacheData,
    init_args: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setting, flushing, and then getting data from the cache."""
    cache = FileCache(cache_file, **init_args)
    test_data = initial_data
    await cache.set(test_data)
    await cache.flush()

    assert cache_file.exists()

    # Create a new cache instance to ensure data is loaded from the file
    new_cache = FileCache(cache_file, **init_args)
    loaded_data = await new_cache.get()
    assert loaded_data == test_data
    assert await cache.get() == snapshot


async def test_get_caches_in_memory(cache_file: pathlib.Path) -> None:
    """Test that get caches the data in memory and avoids re-reading the file."""
    cache = FileCache(cache_file)
    initial_data = await cache.get()

    with patch("roborock.devices.file_cache.load_value", new_callable=AsyncMock) as mock_load_value:
        # This call should use the in-memory cache
        second_get_data = await cache.get()
        assert second_get_data is initial_data
        mock_load_value.assert_not_called()


async def test_invalid_cache_data(cache_file: pathlib.Path) -> None:
    """Test that a TypeError is raised for invalid cache data."""
    with open(cache_file, "wb") as f:
        pickle.dump("invalid_data", f)

    cache = FileCache(cache_file)
    with pytest.raises(TypeError):
        await cache.get()


async def test_flush_no_data(cache_file: pathlib.Path) -> None:
    """Test that flush does nothing if there is no data to write."""
    cache = FileCache(cache_file)
    await cache.flush()
    assert not cache_file.exists()

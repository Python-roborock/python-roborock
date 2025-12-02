"""Tests for the FileCache class."""

import dataclasses
import pathlib
import pickle
from unittest.mock import AsyncMock, patch

import pytest

from roborock.data import HomeData, NetworkInfo, RoborockProductNickname
from roborock.device_features import DeviceFeatures
from roborock.devices.cache import CacheData
from roborock.devices.file_cache import FileCache
from tests.mock_data import HOME_DATA_RAW, NETWORK_INFO


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


async def test_set_and_flush_and_get(cache_file: pathlib.Path) -> None:
    """Test setting, flushing, and then getting data from the cache."""
    cache = FileCache(cache_file)
    test_data = CacheData(home_data="test_home_data")  # type: ignore
    await cache.set(test_data)
    await cache.flush()

    assert cache_file.exists()

    # Create a new cache instance to ensure data is loaded from the file
    new_cache = FileCache(cache_file)
    loaded_data = await new_cache.get()
    assert loaded_data == test_data


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


def test_serialize_dictionary_cache() -> None:
    data = {
        "home_data": HOME_DATA_RAW,
        "network_info": {"fake_duid": NETWORK_INFO},
        "home_map_info": {
            "0": {
                "map_flag": 0,
                "name": "",
                "rooms": [
                    {"segment_id": 16, "iot_id": "2537178", "name": "Living room"},
                    {"segment_id": 17, "iot_id": "2537175", "name": "Kitchen"},
                ],
            }
        },
        "home_map_content": {},
        "home_map_content_base64": {"0": "fake_bytes"},
        "device_features": dataclasses.asdict(
            DeviceFeatures.from_feature_flags(
                new_feature_info=4499197267967999,
                new_feature_info_str="508A977F7EFEFFFF",
                feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125],
                product_nickname=RoborockProductNickname.TANOS,
            )
        ),
        "trait_data": {"dock_type": 9},
    }
    cache_data = CacheData.from_dict(data)
    assert isinstance(cache_data, CacheData)
    assert isinstance(cache_data.device_features, DeviceFeatures)
    assert isinstance(cache_data.network_info["fake_duid"], NetworkInfo)
    assert isinstance(cache_data.home_data, HomeData)

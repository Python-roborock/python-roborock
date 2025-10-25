"""Tests for the NetworkInfoTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import NetworkInfo
from roborock.devices.cache import Cache
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.network_info import NetworkInfoTrait
from roborock.roborock_typing import RoborockCommand
from tests.mock_data import NETWORK_INFO

DEVICE_UID = "abc123"


@pytest.fixture
def network_info_trait(device: RoborockDevice) -> NetworkInfoTrait:
    """Create a NetworkInfoTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.network_info


async def test_network_info_from_cache(
    network_info_trait: NetworkInfoTrait, roborock_cache: Cache, mock_rpc_channel: AsyncMock
) -> None:
    """Test that network info is read from the cache."""
    cache_data = await roborock_cache.get()
    network_info = NetworkInfo.from_dict(NETWORK_INFO)
    cache_data.network_info[DEVICE_UID] = network_info
    await roborock_cache.set(cache_data)

    await network_info_trait.refresh()

    assert network_info_trait.ip == "1.1.1.1"
    assert network_info_trait.mac == "aa:bb:cc:dd:ee:ff"
    assert network_info_trait.bssid == "aa:bb:cc:dd:ee:ff"
    assert network_info_trait.rssi == -50
    mock_rpc_channel.send_command.assert_not_called()


async def test_network_info_from_device(
    network_info_trait: NetworkInfoTrait, roborock_cache: Cache, mock_rpc_channel: AsyncMock
) -> None:
    """Test that network info is fetched from the device when not in cache."""
    mock_rpc_channel.send_command.return_value = {
        **NETWORK_INFO,
        "ip": "2.2.2.2",
    }

    await network_info_trait.refresh()

    assert network_info_trait.ip == "2.2.2.2"
    assert network_info_trait.mac == "aa:bb:cc:dd:ee:ff"
    assert network_info_trait.bssid == "aa:bb:cc:dd:ee:ff"
    assert network_info_trait.rssi == -50
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_NETWORK_INFO)

    # Verify it's now in the cache
    cache_data = await roborock_cache.get()
    cached_info = cache_data.network_info.get(DEVICE_UID)
    assert cached_info
    assert cached_info.ip == "2.2.2.2"

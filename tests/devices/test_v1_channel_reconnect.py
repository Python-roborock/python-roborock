
import asyncio
import datetime
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.data import NetworkInfo
from roborock.devices.cache import CacheData, InMemoryCache
from roborock.devices.local_channel import LocalSession
from roborock.devices.v1_channel import V1Channel, NETWORK_INFO_REFRESH_INTERVAL
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import SecurityData

from ..conftest import FakeChannel

TEST_DEVICE_UID = "abc123"
TEST_SECURITY_DATA = SecurityData(endpoint="test_endpoint", nonce=b"test_nonce")
TEST_IP = "192.168.1.100"

@pytest.fixture(name="mock_mqtt_channel")
async def setup_mock_mqtt_channel() -> FakeChannel:
    """Mock MQTT channel for testing."""
    channel = FakeChannel()
    await channel.connect()
    # Mock send_command to fail
    channel.send_command = AsyncMock(side_effect=RoborockException("MQTT Failed"))
    return channel

@pytest.fixture(name="mock_local_channel")
async def setup_mock_local_channel() -> FakeChannel:
    """Mock Local channel for testing."""
    channel = FakeChannel()
    return channel

@pytest.fixture(name="mock_local_session")
def setup_mock_local_session(mock_local_channel: Mock) -> Mock:
    """Mock Local session factory for testing."""
    mock_session = Mock(spec=LocalSession)
    mock_session.return_value = mock_local_channel
    return mock_session

@pytest.mark.asyncio
async def test_v1_channel_reconnect_with_stale_cache_and_mqtt_down(
    mock_mqtt_channel: FakeChannel,
    mock_local_session: Mock,
    mock_local_channel: FakeChannel,
):
    """
    Test that when cache is stale (> 12h) and MQTT is down, the system
    falls back to the stale cache instead of failing indefinitely.
    """
    # 1. Setup stale cache
    cache = InMemoryCache()
    cache_data = CacheData()
    stale_network_info = NetworkInfo(ip=TEST_IP, ssid="ssid", bssid="bssid")
    cache_data.network_info[TEST_DEVICE_UID] = stale_network_info
    await cache.set(cache_data)

    v1_channel = V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        cache=cache,
    )

    # Manually set the last refresh to be old to simulate stale cache
    v1_channel._last_network_info_refresh = datetime.datetime.now(datetime.UTC) - (NETWORK_INFO_REFRESH_INTERVAL + datetime.timedelta(hours=1))

    # 2. Mock MQTT RPC channel to fail
    # V1Channel creates _mqtt_rpc_channel in __init__. We need to mock its send_command.
    v1_channel._mqtt_rpc_channel.send_command = AsyncMock(side_effect=RoborockException("MQTT Network Info Failed"))

    # 3. Attempt local connection.
    # Because cache is stale, use_cache will be False.
    # Because MQTT fails, it will trigger fallback to cache.

    # We call _local_connect(use_cache=False) which is what happens in the loop
    # when _should_use_cache returns False (due to stale cache)
    await v1_channel._local_connect(use_cache=False)

    # 4. Assert that we tried to connect to the local IP from the cache
    mock_local_session.assert_called_once_with(TEST_IP)
    mock_local_channel.connect.assert_called_once()

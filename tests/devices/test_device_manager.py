"""Tests for the DeviceManager class."""

import asyncio
import datetime
from collections.abc import Generator, Iterator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.data import HomeData, UserData
from roborock.devices.cache import InMemoryCache
from roborock.devices.device_manager import UserParams, create_device_manager, create_web_api_wrapper
from roborock.exceptions import RoborockException

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
USER_PARAMS = UserParams(username="test_user", user_data=USER_DATA)
NETWORK_INFO = mock_data.NETWORK_INFO


@pytest.fixture(autouse=True, name="mqtt_session")
def setup_mqtt_session() -> Generator[Mock, None, None]:
    """Fixture to set up the MQTT session for the tests."""
    with patch("roborock.devices.device_manager.create_lazy_mqtt_session") as mock_create_session:
        yield mock_create_session


@pytest.fixture(autouse=True, name="mock_rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True)
async def discover_features_fixture(
    mock_rpc_channel: AsyncMock,
) -> None:
    """Fixture to handle device feature discovery."""
    mock_rpc_channel.send_command.side_effect = [
        [mock_data.APP_GET_INIT_STATUS],
        mock_data.STATUS,
    ]


@pytest.fixture(autouse=True)
def channel_fixture(mock_rpc_channel: AsyncMock) -> Generator[Mock, None, None]:
    """Fixture to set up the local session for the tests."""
    with patch("roborock.devices.device_manager.create_v1_channel") as mock_channel:
        mock_unsub = Mock()
        mock_channel.return_value.subscribe = AsyncMock()
        mock_channel.return_value.subscribe.return_value = mock_unsub
        mock_channel.return_value.rpc_channel = mock_rpc_channel
        yield mock_channel


@pytest.fixture(autouse=True)
def mock_sleep() -> Generator[None, None, None]:
    """Mock sleep logic to speed up tests."""
    sleep_time = datetime.timedelta(seconds=0.001)
    with (
        patch("roborock.devices.device.MIN_BACKOFF_INTERVAL", sleep_time),
        patch("roborock.devices.device.MAX_BACKOFF_INTERVAL", sleep_time),
    ):
        yield


@pytest.fixture(name="channel_failure")
def channel_failure_fixture(mock_rpc_channel: AsyncMock) -> Generator[Mock, None, None]:
    """Fixture that makes channel subscribe fail."""
    with patch("roborock.devices.device_manager.create_v1_channel") as mock_channel:
        mock_channel.return_value.subscribe = AsyncMock(side_effect=RoborockException("Connection failed"))
        mock_channel.return_value.is_connected = False
        mock_channel.return_value.rpc_channel = mock_rpc_channel
        yield mock_channel


@pytest.fixture(name="home_data_no_devices")
def home_data_no_devices_fixture() -> Iterator[HomeData]:
    """Mock home data API that returns no devices."""
    with patch("roborock.devices.device_manager.UserWebApiClient.get_home_data") as mock_home_data:
        home_data = HomeData(
            id=1,
            name="Test Home",
            devices=[],
            products=[],
        )
        mock_home_data.return_value = home_data
        yield home_data


@pytest.fixture(name="home_data")
def home_data_fixture() -> Iterator[HomeData]:
    """Mock home data API that returns devices."""
    with patch("roborock.devices.device_manager.UserWebApiClient.get_home_data") as mock_home_data:
        home_data = HomeData.from_dict(mock_data.HOME_DATA_RAW)
        mock_home_data.return_value = home_data
        yield home_data


async def test_no_devices(home_data_no_devices: HomeData) -> None:
    """Test the DeviceManager created with no devices returned from the API."""

    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert devices == []


async def test_with_device(home_data: HomeData) -> None:
    """Test the DeviceManager created with devices returned from the API."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    assert devices[0].duid == "abc123"
    assert devices[0].name == "Roborock S7 MaxV"

    device = await device_manager.get_device("abc123")
    assert device is not None
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"

    await device_manager.close()


async def test_get_non_existent_device(home_data: HomeData) -> None:
    """Test getting a non-existent device."""
    device_manager = await create_device_manager(USER_PARAMS)
    device = await device_manager.get_device("non_existent_duid")
    assert device is None
    await device_manager.close()


async def test_create_home_data_api_exception() -> None:
    """Test that exceptions from the home data API are propagated through the wrapper."""

    with patch("roborock.devices.device_manager.RoborockApiClient.get_home_data_v3") as mock_get_home_data:
        mock_get_home_data.side_effect = RoborockException("Test exception")
        user_params = UserParams(username="test_user", user_data=USER_DATA)
        api = create_web_api_wrapper(user_params)

        with pytest.raises(RoborockException, match="Test exception"):
            await api.get_home_data()


async def test_cache_logic() -> None:
    """Test that the cache logic works correctly."""
    call_count = 0

    async def mock_home_data_with_counter(*args, **kwargs) -> HomeData:
        nonlocal call_count
        call_count += 1
        return HomeData.from_dict(mock_data.HOME_DATA_RAW)

    # First call happens during create_device_manager initialization
    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=mock_home_data_with_counter,
    ):
        device_manager = await create_device_manager(USER_PARAMS, cache=InMemoryCache())
        assert call_count == 1

        # Second call should use cache, not increment call_count
        devices2 = await device_manager.discover_devices()
        assert call_count == 1  # Should still be 1, not 2
        assert len(devices2) == 1

        await device_manager.close()
        assert len(devices2) == 1

        # Ensure closing again works without error
        await device_manager.close()


async def test_start_connect_failure(home_data: HomeData, channel_failure: Mock, mock_sleep: Mock) -> None:
    """Test that start_connect retries when connection fails."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()

    # Wait for the device to attempt to connect
    attempts = 0
    subscribe_mock = channel_failure.return_value.subscribe
    while subscribe_mock.call_count < 1:
        await asyncio.sleep(0.01)
        attempts += 1
        assert attempts < 10, "Device did not connect after multiple attempts"

    # Device should exist but not be connected
    assert len(devices) == 1
    assert not devices[0].is_connected

    # Verify retry attempts
    assert channel_failure.return_value.subscribe.call_count >= 1

    # Reset the mock channel so that it succeeds on the next attempt
    mock_unsub = Mock()
    subscribe_mock = AsyncMock()
    subscribe_mock.return_value = mock_unsub
    channel_failure.return_value.subscribe = subscribe_mock
    channel_failure.return_value.is_connected = True

    # Wait for the device to attempt to connect again
    attempts = 0
    while subscribe_mock.call_count < 1:
        await asyncio.sleep(0.01)
        attempts += 1
        assert attempts < 10, "Device did not connect after multiple attempts"

    assert devices[0].is_connected

    await device_manager.close()
    assert mock_unsub.call_count == 1

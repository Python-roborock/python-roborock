"""Tests for the DeviceManager class."""

import asyncio
import datetime
from collections.abc import Generator, Iterator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.data import HomeData, UserData
from roborock.devices.cache import InMemoryCache
from roborock.devices.device import RoborockDevice
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


@pytest.fixture(name="channel_exception")
def channel_failure_exception_fixture(mock_rpc_channel: AsyncMock) -> Exception:
    """Fixture that provides the exception to be raised by the failing channel."""
    return RoborockException("Connection failed")


@pytest.fixture(name="channel_failure")
def channel_failure_fixture(mock_rpc_channel: AsyncMock, channel_exception: Exception) -> Generator[Mock, None, None]:
    """Fixture that makes channel subscribe fail."""
    with patch("roborock.devices.device_manager.create_v1_channel") as mock_channel:
        mock_channel.return_value.subscribe = AsyncMock(side_effect=channel_exception)
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


@pytest.mark.parametrize(("prefer_cache", "expected_call_count"), [(True, 1), (False, 2)])
async def test_cache_logic(prefer_cache: bool, expected_call_count: int) -> None:
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
        devices2 = await device_manager.discover_devices(prefer_cache=prefer_cache)
        assert call_count == expected_call_count
        assert len(devices2) == 1

        await device_manager.close()
        assert len(devices2) == 1

        # Ensure closing again works without error
        await device_manager.close()


async def test_home_data_api_fails_with_cache_fallback() -> None:
    """Test that home data exceptions may still fall back to use the cache when available."""

    cache = InMemoryCache()
    cache_data = await cache.get()
    cache_data.home_data = HomeData.from_dict(mock_data.HOME_DATA_RAW)
    await cache.set(cache_data)

    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=RoborockException("Test exception"),
    ):
        # This call will skip the API and use the cache
        device_manager = await create_device_manager(USER_PARAMS, cache=cache)

        # This call will hit the API since we're not preferring the cache
        # but will fallback to the cache data on exception
        devices2 = await device_manager.discover_devices(prefer_cache=False)
        assert len(devices2) == 1

        await device_manager.close()


async def test_ready_callback(home_data: HomeData) -> None:
    """Test that the ready callback is invoked when a device connects."""
    ready_devices: list[RoborockDevice] = []
    device_manager = await create_device_manager(USER_PARAMS, ready_callback=ready_devices.append)

    # Callback should be called for the discovered device
    assert len(ready_devices) == 1
    device = ready_devices[0]
    assert device.duid == "abc123"

    # Verify that adding a ready callback to an already connected device will
    # invoke the callback immediately.
    more_ready_device: list[RoborockDevice] = []
    device.add_ready_callback(more_ready_device.append)
    assert len(more_ready_device) == 1
    assert more_ready_device[0].duid == "abc123"

    await device_manager.close()


@pytest.mark.parametrize(
    ("channel_exception"),
    [
        RoborockException("Connection failed"),
    ],
)
async def test_start_connect_failure(home_data: HomeData, channel_failure: Mock, mock_sleep: Mock) -> None:
    """Test that start_connect retries when connection fails."""
    ready_devices: list[RoborockDevice] = []
    device_manager = await create_device_manager(USER_PARAMS, ready_callback=ready_devices.append)
    devices = await device_manager.get_devices()

    # The device should attempt to connect in the background at least once
    # by the time this function returns.
    subscribe_mock = channel_failure.return_value.subscribe
    assert subscribe_mock.call_count > 0

    # Device should exist but not be connected
    assert len(devices) == 1
    assert not devices[0].is_connected
    assert not ready_devices

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
    assert ready_devices
    assert len(ready_devices) == 1

    await device_manager.close()
    assert mock_unsub.call_count == 1


async def test_rediscover_devices(mock_rpc_channel: AsyncMock) -> None:
    """Test that we can discover devices multiple times and discover new devices."""
    raw_devices: list[dict[str, Any]] = mock_data.HOME_DATA_RAW["devices"]
    assert len(raw_devices) > 0
    raw_device_1 = raw_devices[0]

    home_data_responses = [
        HomeData.from_dict(mock_data.HOME_DATA_RAW),
        # New device added on second call. We make a copy and updated fields to simulate
        # a new device.
        HomeData.from_dict(
            {
                **mock_data.HOME_DATA_RAW,
                "devices": [
                    raw_device_1,
                    {
                        **raw_device_1,
                        "duid": "new_device_duid",
                        "name": "New Device",
                        "model": "roborock.newmodel.v1",
                        "mac": "00:11:22:33:44:55",
                    },
                ],
            }
        ),
    ]

    mock_rpc_channel.send_command.side_effect = [
        [mock_data.APP_GET_INIT_STATUS],
        mock_data.STATUS,
        # Device #2
        [mock_data.APP_GET_INIT_STATUS],
        mock_data.STATUS,
    ]

    async def mock_home_data_with_counter(*args, **kwargs) -> HomeData:
        nonlocal home_data_responses
        return home_data_responses.pop(0)

    # First call happens during create_device_manager initialization
    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=mock_home_data_with_counter,
    ):
        device_manager = await create_device_manager(USER_PARAMS, cache=InMemoryCache())
        assert len(await device_manager.get_devices()) == 1

        # Second call should use cache and does not add new device
        await device_manager.discover_devices(prefer_cache=True)
        assert len(await device_manager.get_devices()) == 1

        # Third call should fetch new home data and add the new device
        await device_manager.discover_devices(prefer_cache=False)
        assert len(await device_manager.get_devices()) == 2

        # Verify the two devices exist with correct data
        device_1 = await device_manager.get_device("abc123")
        assert device_1 is not None
        assert device_1.name == "Roborock S7 MaxV"

        new_device = await device_manager.get_device("new_device_duid")
        assert new_device
        assert new_device.name == "New Device"

        # Ensure closing again works without error
        await device_manager.close()


@pytest.mark.parametrize(
    ("channel_exception"),
    [
        Exception("Unexpected error"),
    ],
)
async def test_start_connect_unexpected_error(home_data: HomeData, channel_failure: Mock, mock_sleep: Mock) -> None:
    """Test that some unexpected errors from start_connect are propagated."""
    with pytest.raises(Exception, match="Unexpected error"):
        await create_device_manager(USER_PARAMS)


async def test_diagnostics_collection(home_data: HomeData) -> None:
    """Test that diagnostics are collected correctly in the DeviceManager."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert len(devices) == 1

    diagnostics = device_manager.diagnostic_data()
    assert diagnostics is not None
    assert diagnostics.get("discover_devices") == 1
    assert diagnostics.get("fetch_home_data") == 1

    await device_manager.close()

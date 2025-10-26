"""Tests for the DeviceManager class."""

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


@pytest.fixture(autouse=True)
def channel_fixture() -> Generator[Mock, None, None]:
    """Fixture to set up the local session for the tests."""
    with patch("roborock.devices.device_manager.create_v1_channel") as mock_channel:
        mock_unsub = Mock()
        mock_channel.return_value.subscribe = AsyncMock()
        mock_channel.return_value.subscribe.return_value = mock_unsub
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
        api = _create_web_api_wrapper(user_params)

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

        await device_manager.close()

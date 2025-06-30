"""Tests for the DeviceManager class."""

from unittest.mock import patch

import pytest

from roborock.containers import HomeData, UserData
from roborock.devices.device import DeviceVersion
from roborock.devices.device_manager import create_device_manager, create_home_data_api
from roborock.exceptions import RoborockException

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)


async def home_home_data_no_devices() -> HomeData:
    """Mock home data API that returns no devices."""
    return HomeData(
        id=1,
        name="Test Home",
        devices=[],
        products=[],
    )


async def mock_home_data() -> HomeData:
    """Mock home data API that returns devices."""
    return HomeData.from_dict(mock_data.HOME_DATA_RAW)


async def test_no_devices() -> None:
    """Test the DeviceManager created with no devices returned from the API."""

    device_manager = await create_device_manager(USER_DATA, home_home_data_no_devices)
    devices = await device_manager.get_devices()
    assert devices == []


async def test_with_device() -> None:
    """Test the DeviceManager created with devices returned from the API."""
    device_manager = await create_device_manager(USER_DATA, mock_home_data)
    devices = await device_manager.get_devices()
    assert [(device.duid, device.name, device.device_version) for device in devices] == [
        ("abc123", "Roborock S7 MaxV", DeviceVersion.V1),
    ]

    device = await device_manager.get_device("abc123")
    assert device is not None
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.device_version == DeviceVersion.V1


async def test_get_non_existent_device() -> None:
    """Test getting a non-existent device."""
    device_manager = await create_device_manager(USER_DATA, mock_home_data)
    device = await device_manager.get_device("non_existent_duid")
    assert device is None


async def test_home_data_api_exception() -> None:
    """Test the home data API with an exception."""

    async def home_data_api_exception() -> HomeData:
        raise RoborockException("Test exception")

    with pytest.raises(RoborockException, match="Test exception"):
        await create_device_manager(USER_DATA, home_data_api_exception)


async def test_create_home_data_api_exception() -> None:
    """Test that exceptions from the home data API are propagated through the wrapper."""

    with patch("roborock.devices.device_manager.RoborockApiClient.get_home_data") as mock_get_home_data:
        mock_get_home_data.side_effect = RoborockException("Test exception")
        api = create_home_data_api(USER_DATA, mock_get_home_data)

        with pytest.raises(RoborockException, match="Test exception"):
            await api()

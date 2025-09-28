""""Fixtures for V1 trait tests."""

from unittest.mock import AsyncMock

import pytest

from roborock.containers import HomeData, S7MaxVStatus, UserData
from roborock.devices.device import RoborockDevice
from roborock.devices.traits import v1

from .... import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
STATUS = S7MaxVStatus.from_dict(mock_data.STATUS)


@pytest.fixture(autouse=True, name="channel")
def device_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mock_rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mock_mqtt_rpc_channel")
def mqtt_rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="device")
def device_fixture(channel: AsyncMock, mock_rpc_channel: AsyncMock, mock_mqtt_rpc_channel: AsyncMock) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    return RoborockDevice(
        device_info=HOME_DATA.devices[0],
        channel=channel,
        trait=v1.create(HOME_DATA.products[0], mock_rpc_channel, mock_mqtt_rpc_channel),
    )

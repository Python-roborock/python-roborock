"""Tests for the Device class."""

from unittest.mock import AsyncMock, Mock

import pytest

from roborock.containers import HomeData, S7MaxVStatus, UserData
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.status import StatusTrait
from roborock.devices.traits.trait import Trait

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
STATUS = S7MaxVStatus.from_dict(mock_data.STATUS)


@pytest.fixture(autouse=True, name="channel")
def device_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="device")
def device_fixture(channel: AsyncMock, traits: list[Trait]) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    return RoborockDevice(
        device_info=HOME_DATA.devices[0],
        channel=channel,
        traits=traits,
    )


@pytest.fixture(autouse=True, name="traits")
def traits_fixture(rpc_channel: AsyncMock) -> list[Trait]:
    """Fixture to set up the V1 API for tests."""
    return [
        StatusTrait(
            product_info=HOME_DATA.products[0],
            rpc_channel=rpc_channel,
        )
    ]


async def test_device_connection(device: RoborockDevice, channel: AsyncMock) -> None:
    """Test the Device connection setup."""

    unsub = Mock()
    subscribe = AsyncMock()
    subscribe.return_value = unsub
    channel.subscribe = subscribe

    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"

    assert not subscribe.called

    await device.connect()
    assert subscribe.called
    assert not unsub.called

    await device.close()
    assert unsub.called


async def test_device_get_status_command(device: RoborockDevice, rpc_channel: AsyncMock) -> None:
    """Test the device get_status command."""
    # Mock response for get_status command
    rpc_channel.send_command.return_value = STATUS

    # Test get_status and verify the command was sent
    status_api = device.traits["status"]
    assert isinstance(status_api, StatusTrait)
    assert status_api is not None
    status = await status_api.get_status()
    assert rpc_channel.send_command.called

    # Verify the result
    assert status is not None
    assert status.battery == 100
    assert status.state == 8

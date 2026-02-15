"""Tests for the StatusTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data.v1 import (
    RoborockStateCode,
)
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockCommand
from tests.mock_data import STATUS


@pytest.fixture
def status_trait(device: RoborockDevice) -> StatusTrait:
    """Create a StatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.status


async def test_refresh_status(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test successfully refreshing status."""
    mock_rpc_channel.send_command.return_value = [STATUS]

    await status_trait.refresh()

    assert status_trait.battery == 100
    assert status_trait.state == RoborockStateCode.charging
    assert status_trait.fan_power == 102
    assert status_trait.fan_speed_name == "balanced"
    assert status_trait.fan_speed_name in status_trait.fan_speed_options
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_STATUS)


async def test_refresh_status_dict_response(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test refreshing status when response is a dict instead of list."""
    mock_rpc_channel.send_command.return_value = STATUS

    await status_trait.refresh()

    assert status_trait.battery == 100
    assert status_trait.state == RoborockStateCode.charging
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_STATUS)


async def test_refresh_status_propagates_exception(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from RPC channel are propagated."""
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    with pytest.raises(RoborockException, match="Communication error"):
        await status_trait.refresh()


async def test_refresh_status_invalid_format(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that invalid response format raises ValueError."""
    mock_rpc_channel.send_command.return_value = "invalid"

    with pytest.raises(ValueError, match="Unexpected status format"):
        await status_trait.refresh()


def test_none_values(status_trait: StatusTrait) -> None:
    """Test that none values are returned correctly."""
    status_trait.fan_power = None
    status_trait.water_box_mode = None
    status_trait.mop_mode = None
    assert status_trait.fan_speed_name is None
    assert status_trait.water_mode_name is None
    assert status_trait.mop_route_name is None


def test_options(status_trait: StatusTrait) -> None:
    """Test that fan_speed_options returns a list of options."""
    assert isinstance(status_trait.fan_speed_options, list)
    assert len(status_trait.fan_speed_options) > 0
    assert isinstance(status_trait.water_mode_options, list)
    assert len(status_trait.water_mode_options) > 0
    assert isinstance(status_trait.mop_route_options, list)
    assert len(status_trait.mop_route_options) > 0

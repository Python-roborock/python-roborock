"""Tests for the DoNotDisturbTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import DnDTimer
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.do_not_disturb import DoNotDisturbTrait
from roborock.roborock_typing import RoborockCommand


@pytest.fixture
async def dnd_trait(device: RoborockDevice) -> DoNotDisturbTrait:
    """Create a DoNotDisturbTrait instance with mocked dependencies."""
    assert device.v1_properties
    assert device.v1_properties.dnd
    return device.v1_properties.dnd


@pytest.fixture
def sample_dnd_timer() -> DnDTimer:
    """Create a sample DnDTimer for testing."""
    return DnDTimer(
        start_hour=22,
        start_minute=0,
        end_hour=8,
        end_minute=0,
        enabled=1,
    )


async def test_get_dnd_timer_success(
    dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock, sample_dnd_timer: DnDTimer
) -> None:
    """Test successfully getting DnD timer settings."""
    # Setup mock to return the sample DnD timer
    mock_rpc_channel.send_command.return_value = sample_dnd_timer.as_dict()

    # Call the method
    await dnd_trait.refresh()

    # Verify the result
    assert dnd_trait.start_hour == 22
    assert dnd_trait.start_minute == 0
    assert dnd_trait.end_hour == 8
    assert dnd_trait.end_minute == 0
    assert dnd_trait.enabled == 1
    assert dnd_trait.is_on

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DND_TIMER)


async def test_get_dnd_timer_disabled(dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test getting DnD timer when it's disabled."""
    disabled_timer = DnDTimer(
        start_hour=22,
        start_minute=0,
        end_hour=8,
        end_minute=0,
        enabled=0,
    )
    mock_rpc_channel.send_command.return_value = disabled_timer.as_dict()

    await dnd_trait.refresh()

    assert dnd_trait.enabled == 0
    assert not dnd_trait.is_on
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DND_TIMER)


async def test_set_dnd_timer_success(
    dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock, sample_dnd_timer: DnDTimer
) -> None:
    """Test successfully setting DnD timer settings."""
    # Call the method
    await dnd_trait.set_dnd_timer(sample_dnd_timer)

    # Verify the RPC call was made correctly with dataclass converted to dict

    expected_params = {
        "startHour": 22,
        "startMinute": 0,
        "endHour": 8,
        "endMinute": 0,
        "enabled": 1,
    }
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.SET_DND_TIMER, params=expected_params)


async def test_clear_dnd_timer_success(dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test successfully clearing DnD timer settings."""
    # Call the method
    await dnd_trait.clear_dnd_timer()

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.CLOSE_DND_TIMER)


async def test_get_dnd_timer_propagates_exception(dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from RPC channel are propagated in get_dnd_timer."""
    from roborock.exceptions import RoborockException

    # Setup mock to raise an exception
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    # Verify the exception is propagated
    with pytest.raises(RoborockException, match="Communication error"):
        await dnd_trait.refresh()


async def test_set_dnd_timer_propagates_exception(
    dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock, sample_dnd_timer: DnDTimer
) -> None:
    """Test that exceptions from RPC channel are propagated in set_dnd_timer."""
    from roborock.exceptions import RoborockException

    # Setup mock to raise an exception
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    # Verify the exception is propagated
    with pytest.raises(RoborockException, match="Communication error"):
        await dnd_trait.set_dnd_timer(sample_dnd_timer)


async def test_clear_dnd_timer_propagates_exception(dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from RPC channel are propagated in clear_dnd_timer."""
    from roborock.exceptions import RoborockException

    # Setup mock to raise an exception
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    # Verify the exception is propagated
    with pytest.raises(RoborockException, match="Communication error"):
        await dnd_trait.clear_dnd_timer()

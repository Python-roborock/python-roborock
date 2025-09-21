"""Tests for the DoNotDisturbTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.containers import DnDTimer
from roborock.devices.traits.dnd import DoNotDisturbTrait
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.roborock_typing import RoborockCommand


@pytest.fixture
def mock_rpc_channel() -> AsyncMock:
    """Create a mock RPC channel."""
    mock_channel = AsyncMock(spec=V1RpcChannel)
    # Ensure send_command is an AsyncMock that returns awaitable coroutines
    mock_channel.send_command = AsyncMock()
    return mock_channel


@pytest.fixture
def dnd_trait(mock_rpc_channel: AsyncMock) -> DoNotDisturbTrait:
    """Create a DoNotDisturbTrait instance with mocked dependencies."""
    return DoNotDisturbTrait(mock_rpc_channel)


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


def test_trait_name(dnd_trait: DoNotDisturbTrait) -> None:
    """Test that the trait has the correct name."""
    assert dnd_trait.name == "do_not_disturb"


async def test_get_dnd_timer_success(
    dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock, sample_dnd_timer: DnDTimer
) -> None:
    """Test successfully getting DnD timer settings."""
    # Setup mock to return the sample DnD timer
    mock_rpc_channel.send_command.return_value = sample_dnd_timer

    # Call the method
    result = await dnd_trait.get_dnd_timer()

    # Verify the result
    assert result == sample_dnd_timer
    assert result.start_hour == 22
    assert result.start_minute == 0
    assert result.end_hour == 8
    assert result.end_minute == 0
    assert result.enabled == 1

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DND_TIMER, response_type=DnDTimer)


async def test_get_dnd_timer_disabled(dnd_trait: DoNotDisturbTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test getting DnD timer when it's disabled."""
    disabled_timer = DnDTimer(
        start_hour=22,
        start_minute=0,
        end_hour=8,
        end_minute=0,
        enabled=0,
    )
    mock_rpc_channel.send_command.return_value = disabled_timer

    result = await dnd_trait.get_dnd_timer()

    assert result.enabled == 0
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DND_TIMER, response_type=DnDTimer)


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
        await dnd_trait.get_dnd_timer()


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

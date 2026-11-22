"""Tests for the CommandTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.devices.traits.v1.command import CommandTrait
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockCommand


@pytest.fixture(name="command_trait")
def command_trait_fixture() -> CommandTrait:
    """Create a CommandTrait instance with a mocked RPC channel."""
    trait = CommandTrait()
    trait._rpc_channel = AsyncMock()  # type: ignore[assignment]
    return trait


async def test_send_command_success(command_trait: CommandTrait) -> None:
    """Test successfully sending a command."""
    mock_rpc_channel = command_trait._rpc_channel
    assert mock_rpc_channel is not None
    mock_rpc_channel.send_command.return_value = {"result": "ok"}

    # Call the method
    result = await command_trait.send(RoborockCommand.APP_START)

    # Verify the result
    assert result == {"result": "ok"}

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.APP_START, params=None)


async def test_send_command_with_params(command_trait: CommandTrait) -> None:
    """Test successfully sending a command with parameters."""
    mock_rpc_channel = command_trait._rpc_channel
    assert mock_rpc_channel is not None
    mock_rpc_channel.send_command.return_value = {"result": "ok"}
    params = {"segments": [1, 2, 3]}

    # Call the method
    result = await command_trait.send(RoborockCommand.APP_SEGMENT_CLEAN, params)

    # Verify the result
    assert result == {"result": "ok"}

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.APP_SEGMENT_CLEAN, params=params)


async def test_send_command_propagates_exception(command_trait: CommandTrait) -> None:
    """Test that exceptions from RPC channel are propagated."""
    mock_rpc_channel = command_trait._rpc_channel
    assert mock_rpc_channel is not None
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    # Verify the exception is propagated
    with pytest.raises(RoborockException, match="Communication error"):
        await command_trait.send(RoborockCommand.APP_START)

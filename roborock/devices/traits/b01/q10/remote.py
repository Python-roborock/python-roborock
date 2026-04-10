"""Traits for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    RemoteCommand,
)

from .command import CommandTrait


class RemoteTrait:
    """Trait for sending vacuum commands.

    This is a wrapper around the CommandTrait for sending remote related
    commands to Q10 devices.
    """

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the RemoteTrait."""
        self._command = command

    async def _send_remote(self, action: RemoteCommand) -> None:
        await self._command.send(B01_Q10_DP.COMMON, params={B01_Q10_DP.REMOTE: action.value})

    async def forward(self) -> None:
        """Move forward."""
        await self._send_remote(RemoteCommand.FORWARD)

    async def left(self) -> None:
        """Turn left."""
        await self._send_remote(RemoteCommand.LEFT)

    async def right(self) -> None:
        """Turn right."""
        await self._send_remote(RemoteCommand.RIGHT)

    async def stop(self) -> None:
        """Stop last moving command or start remote control."""
        await self._send_remote(RemoteCommand.STOP)

    async def exit(self) -> None:
        """Exit remote control."""
        await self._send_remote(RemoteCommand.EXIT)

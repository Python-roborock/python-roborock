"""Traits for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP
)
from typing import Any

from .command import CommandTrait

REMOTE_COMMANDS = {
    "forward": 0,
    "left": 2,
    "right": 3,
    "stop": 4,
    "exit": 5,
}

class RemoteTrait:
    """Trait for sending remote control commands.

    This is a wrapper around the CommandTrait for sending vacuum related
    commands to Q10 devices.
    """

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the RemoteTrait."""
        self._command = command

    async def send_common_dp(self, command: B01_Q10_DP, value: Any) -> None:
        await self._command.send(B01_Q10_DP.COMMON, params={command.code: value})

    async def send_remote(self, action: str) -> None:
        await self.send_common_dp(B01_Q10_DP.REMOTE, REMOTE_COMMANDS[action])

    async def forward(self) -> None:
        """Move forward."""
        
        await self.send_remote("forward")

    async def left(self) -> None:
        """Turn left."""
        
        await self.send_remote("left")

    async def right(self) -> None:
        """Turn right."""
        
        await self.send_remote("right")

    async def stop(self) -> None:
        """Stop last moving command or start remote control."""
        
        await self.send_remote("stop")
    
    async def exit(self) -> None:
        """Exit remote control."""
        
        await self.send_remote("exit")

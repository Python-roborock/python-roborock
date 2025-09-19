"""Module for Roborock V1 devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import logging

from roborock.containers import DnDTimer
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.roborock_typing import RoborockCommand

from .trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "DoNotDisturbTrait",
]


class DoNotDisturbTrait(Trait):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    name = "do_not_disturb"

    def __init__(self, rpc_channel: V1RpcChannel) -> None:
        """Initialize the DoNotDisturbTrait."""
        self._rpc_channel = rpc_channel

    async def get_dnd_timer(self) -> DnDTimer:
        """Get the current Do Not Disturb (DND) timer settings of the device."""
        return await self._rpc_channel.send_command(RoborockCommand.GET_DND_TIMER, response_type=DnDTimer)

    async def set_dnd_timer(self, dnd_timer: DnDTimer) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self._rpc_channel.send_command(RoborockCommand.SET_DND_TIMER, params=dnd_timer.as_dict())

    async def clear_dnd_timer(self) -> None:
        """Clear the Do Not Disturb (DND) timer settings of the device."""
        await self._rpc_channel.send_command(RoborockCommand.CLOSE_DND_TIMER)

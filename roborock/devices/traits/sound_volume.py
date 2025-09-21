"""Module for controlling the sound volume of Roborock devices."""

from roborock.devices.traits.trait import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockCommand

__all__ = [
    "SoundVolumeTrait",
]


class SoundVolumeTrait(Trait):
    """Trait for controlling the sound volume of a Roborock device."""

    name = "sound_volume"

    def __init__(self, rpc_channel: V1RpcChannel) -> None:
        """Initialize the SoundVolumeTrait."""
        self._rpc_channel = rpc_channel

    async def get_volume(self) -> int:
        """Get the current sound volume of the device."""
        response = await self._rpc_channel.send_command(RoborockCommand.GET_SOUND_VOLUME)
        if not isinstance(response, list) or not response:
            raise RoborockException(f"Unexpected volume format: {response!r}")
        return int(response[0])

    async def set_volume(self, volume: int) -> None:
        """Set the sound volume of the device."""
        await self._rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params=[volume])

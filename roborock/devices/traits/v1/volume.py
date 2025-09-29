from dataclasses import dataclass, field

from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

# TODO: This is currently the pattern for holding all the commands that hold a
# single value, but it still seems too verbose. Maybe we can generate these
# dynamically or somehow make them less code.


@dataclass
class SoundVolume(common.RoborockValueBase):
    """Dataclass for sound volume."""

    volume: int | None = field(default=None, metadata={"roborock_value": True})
    """Sound volume level (0-100)."""


class SoundVolumeTrait(SoundVolume, common.V1TraitMixin):
    """Trait for controlling the sound volume of a Roborock device."""

    command = RoborockCommand.GET_SOUND_VOLUME

    async def set_volume(self, volume: int) -> None:
        """Set the sound volume of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params=[volume])

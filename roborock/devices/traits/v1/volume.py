from dataclasses import dataclass

from roborock.data.containers import RoborockBase
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


@dataclass
class SoundVolume(RoborockBase):
    """Dataclass for sound volume."""

    volume: int | None = None
    """Sound volume level (0-100)."""


class SoundVolumeTrait(SoundVolume, common.V1TraitMixin):
    """Trait for controlling the sound volume of a Roborock device."""

    command = RoborockCommand.GET_SOUND_VOLUME
    converter = common.SingleValueConverter(SoundVolume, "volume")

    async def set_volume(self, volume: int) -> None:
        """Set the sound volume of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params=[volume])
        self.volume = volume

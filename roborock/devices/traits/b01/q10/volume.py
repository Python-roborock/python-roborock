"""Sound volume trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import SoundVolume
from roborock.devices.traits.common import DpsDataConverter

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class SoundVolumeTrait(SoundVolume, UpdatableTrait):
    """Trait for reading and setting the speaker volume of a Q10 device."""

    _CONVERTER = DpsDataConverter.from_dataclass(SoundVolume)

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the volume trait."""
        SoundVolume.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)

    async def set_volume(self, volume: int) -> None:
        """Set the speaker volume (0-100)."""
        if not 0 <= volume <= 100:
            raise ValueError("volume must be between 0 and 100")
        await self._write(B01_Q10_DP.VOLUME, volume)

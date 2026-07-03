"""Dust collection (dock auto-empty) trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXDeviceDustCollectionFrequency
from roborock.data.b01_q10.b01_q10_containers import DustCollection
from roborock.devices.traits.common import DpsDataConverter

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class DustCollectionTrait(DustCollection, UpdatableTrait):
    """Trait for reading and controlling automatic dust collection at the dock."""

    _CONVERTER = DpsDataConverter.from_dataclass(DustCollection)

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the dust collection trait."""
        DustCollection.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)

    @property
    def is_on(self) -> bool:
        """Return whether automatic dust collection is enabled."""
        return bool(self.dust_switch)

    async def enable(self) -> None:
        """Enable automatic dust collection at the dock."""
        await self._write(B01_Q10_DP.DUST_SWITCH, 1)

    async def disable(self) -> None:
        """Disable automatic dust collection at the dock."""
        await self._write(B01_Q10_DP.DUST_SWITCH, 0)

    async def set_frequency(self, frequency: YXDeviceDustCollectionFrequency) -> None:
        """Set how often the dock empties the bin.

        The value is the interval in cleans, with ``DAILY`` (0) meaning daily.
        """
        await self._write(B01_Q10_DP.DUST_SETTING, frequency.code)

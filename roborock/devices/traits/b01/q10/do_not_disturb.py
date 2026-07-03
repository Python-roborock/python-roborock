"""Do Not Disturb trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import DoNotDisturb
from roborock.devices.traits.common import DpsDataConverter

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class DoNotDisturbTrait(DoNotDisturb, UpdatableTrait):
    """Trait for reading and controlling Do Not Disturb on a Q10 device."""

    _CONVERTER = DpsDataConverter.from_dataclass(DoNotDisturb)

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the Do Not Disturb trait."""
        DoNotDisturb.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)

    @property
    def is_on(self) -> bool:
        """Return whether Do Not Disturb is enabled."""
        return bool(self.not_disturb)

    async def enable(self) -> None:
        """Enable Do Not Disturb."""
        await self._write(B01_Q10_DP.NOT_DISTURB, 1)

    async def disable(self) -> None:
        """Disable Do Not Disturb."""
        await self._write(B01_Q10_DP.NOT_DISTURB, 0)

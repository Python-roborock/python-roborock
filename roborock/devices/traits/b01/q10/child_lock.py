"""Child lock trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import ChildLock
from roborock.devices.traits.common import DpsDataConverter

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class ChildLockTrait(ChildLock, UpdatableTrait):
    """Trait for reading and controlling the child lock of a Q10 device."""

    _CONVERTER = DpsDataConverter.from_dataclass(ChildLock)

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the child lock trait."""
        ChildLock.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)

    @property
    def is_on(self) -> bool:
        """Return whether the child lock is enabled."""
        return bool(self.child_lock)

    async def enable(self) -> None:
        """Enable the child lock."""
        await self._write(B01_Q10_DP.CHILD_LOCK, 1)

    async def disable(self) -> None:
        """Disable the child lock."""
        await self._write(B01_Q10_DP.CHILD_LOCK, 0)

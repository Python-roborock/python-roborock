"""Child lock trait for Q10 devices."""

from dataclasses import dataclass

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10ChildLock
from roborock.devices.traits.b01.q10.common import Q10TraitMixin


@dataclass
class Q10ChildLockTrait(Q10ChildLock, Q10TraitMixin):
    """Trait for managing the child lock of Q10 devices."""

    dps_field_map = {
        B01_Q10_DP.CHILD_LOCK: ("enabled", bool),
    }

    async def set_child_lock(self, enabled: bool) -> None:
        """Set the child lock of the device."""
        await self.send_dp(B01_Q10_DP.CHILD_LOCK, int(enabled))
        self.enabled = enabled

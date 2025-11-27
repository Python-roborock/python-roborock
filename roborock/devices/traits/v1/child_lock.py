from roborock.data import ChildLockStatus
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_STATUS_PARAM = "lock_status"


class ChildLockTrait(ChildLockStatus, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for controlling the child lock of a Roborock device."""

    command = RoborockCommand.GET_CHILD_LOCK_STATUS
    requires_feature = "is_set_child_supported"

    @property
    def is_on(self) -> bool:
        """Return whether the child lock is enabled."""
        return self.lock_status == 1

    async def enable(self) -> None:
        """Enable the child lock."""
        await self.rpc_channel.send_command(RoborockCommand.SET_CHILD_LOCK_STATUS, params={_STATUS_PARAM: 1})
        # Optimistic update to avoid an extra refresh
        self.lock_status = 1

    async def disable(self) -> None:
        """Disable the child lock."""
        await self.rpc_channel.send_command(RoborockCommand.SET_CHILD_LOCK_STATUS, params={_STATUS_PARAM: 0})
        # Optimistic update to avoid an extra refresh
        self.lock_status = 0

"""Trait for the dock mop dryer."""

from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.status import StatusTrait
from roborock.roborock_typing import RoborockCommand

_STATUS_PARAM = "status"


def _supports_mop_dryer(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_dryable


class MopDryerTrait(common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for controlling the dock mop dryer.

    The dryer has no dedicated query command. Whether a drying cycle is running
    is reported as ``dry_status`` on the device status, so this trait reads its
    state from the status trait and refreshes through it.
    """

    requires_dock_features = _supports_mop_dryer

    def __init__(self, status_trait: StatusTrait) -> None:
        super().__init__()
        self._status_trait = status_trait

    async def refresh(self) -> None:
        """Refresh the dryer state, which is reported through the device status."""
        await self._status_trait.refresh()

    @property
    def is_on(self) -> bool:
        """Return whether a drying cycle is currently running."""
        return bool(self._status_trait.dry_status)

    async def enable(self) -> None:
        """Start drying the mop."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_STATUS, params={_STATUS_PARAM: 1})
        # Optimistic update to avoid an extra refresh
        self._status_trait.dry_status = 1

    async def disable(self) -> None:
        """Stop drying the mop."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_STATUS, params={_STATUS_PARAM: 0})
        # Optimistic update to avoid an extra refresh
        self._status_trait.dry_status = 0

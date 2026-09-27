"""Trait for the dock mop dryer."""

from roborock.data import MopDryerSetting
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_STATUS_PARAM = "status"


def _supports_mop_dryer(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_dryable


class MopDryerTrait(MopDryerSetting, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for the dock mop dryer.

    The switch controls the auto mop-drying setting, i.e. whether the dock
    dries the mop after washing. ``start_dry`` and ``stop_dry`` control a
    drying cycle directly. Whether a cycle is currently running is reported
    as ``dry_status`` on the device status.
    """

    command = RoborockCommand.APP_GET_DRYER_SETTING
    converter = common.DefaultConverter(MopDryerSetting)
    requires_dock_features = _supports_mop_dryer

    @property
    def is_on(self) -> bool:
        """Return whether auto mop drying is enabled."""
        return self.status == 1

    async def enable(self) -> None:
        """Enable auto mop drying."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_SETTING, params={_STATUS_PARAM: 1})
        # Optimistic update to avoid an extra refresh
        self.status = 1

    async def disable(self) -> None:
        """Disable auto mop drying."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_SETTING, params={_STATUS_PARAM: 0})
        # Optimistic update to avoid an extra refresh
        self.status = 0

    async def start_dry(self) -> None:
        """Start a mop drying cycle."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_STATUS, params={_STATUS_PARAM: 1})

    async def stop_dry(self) -> None:
        """Stop the running mop drying cycle."""
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_DRYER_STATUS, params={_STATUS_PARAM: 0})

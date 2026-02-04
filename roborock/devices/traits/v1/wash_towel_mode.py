"""Trait for wash towel mode."""

from functools import cached_property

from roborock.data import WashTowelMode, WashTowelModes, get_wash_towel_modes
from roborock.device_features import is_wash_n_fill_dock
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.roborock_typing import RoborockCommand


class WashTowelModeTrait(WashTowelMode, common.V1TraitMixin):
    """Trait for wash towel mode."""

    command = RoborockCommand.GET_WASH_TOWEL_MODE
    requires_dock_type = is_wash_n_fill_dock

    def __init__(
        self,
        device_feature_trait: DeviceFeaturesTrait | None = None,
        wash_mode: WashTowelModes | None = None,
    ) -> None:
        self.device_feature_trait = device_feature_trait
        self.wash_mode = wash_mode

    @cached_property
    def wash_towel_mode_options(self) -> list[WashTowelModes]:
        if self.device_feature_trait is None:
            return []
        return get_wash_towel_modes(self.device_feature_trait)

    async def set_wash_towel_mode(self, mode: WashTowelModes) -> None:
        """Set the wash towel mode."""
        await self.rpc_channel.send_command(RoborockCommand.SET_WASH_TOWEL_MODE, params={"wash_mode": mode.code})

    async def start_wash(self) -> None:
        """Start washing the mop."""
        await self.rpc_channel.send_command(RoborockCommand.APP_START_WASH)

    async def stop_wash(self) -> None:
        """Stop washing the mop."""
        await self.rpc_channel.send_command(RoborockCommand.APP_STOP_WASH)

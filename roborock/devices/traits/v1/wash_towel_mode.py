"""Trait for wash towel mode."""

from functools import cached_property
from typing import Self

from roborock.data import WashTowelMode, WashTowelModes, get_wash_towel_modes
from roborock.device_features import is_wash_n_fill_dock
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.roborock_typing import RoborockCommand


class WashTowelModeTrait(WashTowelMode, common.V1TraitMixin):
    """Trait for wash towel mode."""

    command = RoborockCommand.GET_WASH_TOWEL_MODE
    converter = common.DefaultConverter(WashTowelMode)
    requires_dock_type = is_wash_n_fill_dock

    def __init__(
        self,
        device_feature_trait: DeviceFeaturesTrait,
    ) -> None:
        super().__init__()
        self.device_feature_trait = device_feature_trait

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a WashTowelMode object."""
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict):
            return WashTowelMode.from_dict(response)
        raise ValueError(f"Unexpected wash towel mode format: {response!r}")

    @cached_property
    def wash_towel_mode_options(self) -> list[WashTowelModes]:
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

"""Trait for smart wash parameters."""

from roborock.data import RoborockDockSmartWashModeCode, SmartWashParams
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_WASH_INTERVAL_OPTIONS = [600, 900, 1200, 1500]


def _supports_smart_wash_params(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_washable


class SmartWashParamsTrait(SmartWashParams, common.V1TraitMixin):
    """When the dock washes the mop during a clean (app: mop wash frequency)."""

    command = RoborockCommand.GET_SMART_WASH_PARAMS
    converter = common.DefaultConverter(SmartWashParams)
    requires_dock_features = _supports_smart_wash_params

    def __init__(self, device_feature_trait: DeviceFeaturesTrait) -> None:
        super().__init__()
        self.device_feature_trait = device_feature_trait

    @property
    def smart_wash_mode_options(self) -> list[RoborockDockSmartWashModeCode]:
        """Return the mop wash modes offered by the device."""
        options = [RoborockDockSmartWashModeCode.by_time, RoborockDockSmartWashModeCode.by_room]
        if self.device_feature_trait.is_back_wash_new_smart_supported:
            options.append(RoborockDockSmartWashModeCode.new_smart)
        return options

    @property
    def wash_interval_options(self) -> list[int]:
        """Return the mop wash intervals in seconds offered by the app."""
        return list(_WASH_INTERVAL_OPTIONS)

    async def set_smart_wash_params(self, mode: RoborockDockSmartWashModeCode, wash_interval: int) -> None:
        """Set the mop wash mode and the interval in seconds used when washing by time."""
        if mode not in self.smart_wash_mode_options:
            raise RoborockUnsupportedFeature(f"Smart wash mode {mode.name} is not supported")
        if wash_interval not in self.wash_interval_options:
            raise RoborockUnsupportedFeature(f"Wash interval {wash_interval} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_SMART_WASH_PARAMS, params={"smart_wash": mode.value, "wash_interval": wash_interval}
        )
        # Optimistic update to avoid an extra refresh
        self.smart_wash = mode
        self.wash_interval = wash_interval

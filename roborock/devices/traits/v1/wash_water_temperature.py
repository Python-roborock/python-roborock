"""Trait for the mop wash water temperature."""

from roborock.data import RoborockDockWashWaterTemperatureCode, WashWaterTemperature
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand


def get_wash_water_temperatures(dock_features: RoborockDockFeatures) -> list[RoborockDockWashWaterTemperatureCode]:
    """Return the wash water temperatures the app offers for a dock, in app order.

    Warm is offered by high temperature docks and by docks without steam; steam only
    by steam docks. Pet steam is never offered.
    """
    options = [RoborockDockWashWaterTemperatureCode.room_temperature]
    if dock_features.is_high_tmp_water_supported or not dock_features.is_steam_wash_supported:
        options.append(RoborockDockWashWaterTemperatureCode.warm)
    options.append(RoborockDockWashWaterTemperatureCode.hot)
    if dock_features.is_steam_wash_supported:
        options.append(RoborockDockWashWaterTemperatureCode.steam)
    return options


def _supports_wash_water_temperature(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_washable


class WashWaterTemperatureTrait(WashWaterTemperature, common.V1TraitMixin):
    """Water temperature the dock uses to wash the mop (app: water temperature).

    Created only for washing docks on devices with ``is_hot_wash_towel_supported``.
    """

    command = RoborockCommand.GET_WASH_WATER_TEMPERATURE
    converter = common.DefaultConverter(WashWaterTemperature)
    requires_dock_features = _supports_wash_water_temperature

    def __init__(self, device_feature_trait: DeviceFeaturesTrait) -> None:
        super().__init__()
        self.device_feature_trait = device_feature_trait

    @property
    def wash_water_temperature_options(self) -> list[RoborockDockWashWaterTemperatureCode]:
        """Return the wash water temperatures offered by the dock."""
        return get_wash_water_temperatures(self.device_feature_trait.dock_features)

    async def set_wash_water_temperature(self, temperature: RoborockDockWashWaterTemperatureCode) -> None:
        """Set the mop wash water temperature."""
        if temperature not in self.wash_water_temperature_options:
            raise RoborockUnsupportedFeature(f"Wash water temperature {temperature.name} is not supported")
        # The device reads back "wash_water_temperature" but expects the new value under "values".
        await self.rpc_channel.send_command(
            RoborockCommand.SET_WASH_WATER_TEMPERATURE, params={"values": temperature.value}
        )
        # Optimistic update to avoid an extra refresh
        self.wash_water_temperature = temperature

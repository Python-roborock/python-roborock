from functools import cached_property
from typing import Self

from roborock import CleanRoutes, StatusV2, VacuumModes, WaterModes, get_clean_modes, get_clean_routes, get_water_modes
from roborock.roborock_typing import RoborockCommand

from . import common
from .device_features import DeviceFeaturesTrait


class StatusTrait(StatusV2, common.V1TraitMixin):
    """Trait for managing the status of Roborock devices.

    The StatusTrait gives you the access to the state of a Roborock vacuum.
    The various attribute options on state change per each device.
    Values like fan speed, mop mode, etc. have different options for every device
    and are dynamically determined.

    Usage:
        Before accessing status properties, you should call `refresh()` to fetch
        the latest data from the device. You must pass in the device feature trait
        to this trait so that the dynamic attributes can be pre-determined.

    The current dynamic attributes are:
    - Fan Speed
    - Water Mode
    - Mop Route

    You should call the _options() version of the attribute to know which are supported for your device
    (i.e. fan_speed_options())
    Then you can call the _mapping to convert an int value to the actual Enum. (i.e. fan_speed_mapping())
    You can call the _name property to get the str value of the enum. (i.e. fan_speed_name)

    """

    command = RoborockCommand.GET_STATUS

    def __init__(self, device_feature_trait: DeviceFeaturesTrait, region: str | None = None) -> None:
        """Initialize the StatusTrait."""
        super().__init__()
        self._device_features_trait = device_feature_trait
        self._region = region

    @cached_property
    def fan_speed_options(self) -> list[VacuumModes]:
        return get_clean_modes(self._device_features_trait)

    @cached_property
    def fan_speed_mapping(self) -> dict[int, str]:
        return {fan.code: fan.value for fan in self.fan_speed_options}

    @cached_property
    def water_mode_options(self) -> list[WaterModes]:
        return get_water_modes(self._device_features_trait)

    @cached_property
    def water_mode_mapping(self) -> dict[int, str]:
        return {mop.code: mop.value for mop in self.water_mode_options}

    @cached_property
    def mop_route_options(self) -> list[CleanRoutes]:
        return get_clean_routes(self._device_features_trait, self._region or "us")

    @cached_property
    def mop_route_mapping(self) -> dict[int, str]:
        return {route.code: route.value for route in self.mop_route_options}

    @property
    def fan_speed_name(self) -> str | None:
        if self.fan_power is None:
            return None
        return self.fan_speed_mapping.get(self.fan_power)

    @property
    def water_mode_name(self) -> str | None:
        if self.water_box_mode is None:
            return None
        return self.water_mode_mapping.get(self.water_box_mode)

    @property
    def mop_route_name(self) -> str | None:
        if self.mop_mode is None:
            return None
        return self.mop_route_mapping.get(self.mop_mode)

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a StatusV2-based status object."""
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict):
            return StatusV2.from_dict(response)
        raise ValueError(f"Unexpected status format: {response!r}")

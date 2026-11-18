import logging
from functools import cached_property
from typing import Any

from roborock import (
    CleaningMode,
    CleaningSetting,
    CleanRoutes,
    RoborockDockState,
    StatusV2,
    VacuumModes,
    WaterModes,
    get_adjustable_settings,
    get_clean_modes,
    get_clean_routes,
    get_cleaning_mode_codes,
    get_cleaning_mode_options,
    get_current_cleaning_mode,
    get_display_options,
    get_dock_state,
    get_fan_speed_name,
    get_mop_route_name,
    get_motor_mode_commands,
    get_reported_special_mode,
    get_setting_change_codes,
    get_supported_settings,
    get_water_mode_mapping,
    get_water_mode_name,
    get_water_modes,
    resolve_cleaning_mode,
)
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockDataProtocol
from roborock.roborock_typing import RoborockCommand

from . import common
from .device_features import DeviceFeaturesTrait

_LOGGER = logging.getLogger(__name__)

_DPS_CONVERTER = DpsDataConverter.from_dataclass(StatusV2)


class StatusTrait(StatusV2, common.V1TraitMixin, TraitUpdateListener):
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

    The _options and _mapping versions of the attribute (i.e. fan_speed_options,
    fan_speed_mapping) hold only the user-selectable values, i.e. what you can
    write to the device. They do not include SmartPlan or custom codes.
    Use the _name property (i.e. fan_speed_name), or get_fan_speed_name,
    get_water_mode_name and get_mop_route_name, to name the current value,
    including SmartPlan and custom codes.

    """

    command = RoborockCommand.GET_STATUS
    converter = common.DefaultConverter(StatusV2)

    def __init__(self, device_feature_trait: DeviceFeaturesTrait, region: str | None = None) -> None:
        """Initialize the StatusTrait."""
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._device_features_trait = device_feature_trait
        self._region = region

    @property
    def dock_state(self) -> RoborockDockState:
        """Return the feature-aware dock state used by the Roborock app."""
        return get_dock_state(
            state=self.state,
            battery=self.battery,
            charge_status=self.charge_status,
            is_supported_valley_electricity=self._device_features_trait.is_supported_valley_electricity,
        )

    @property
    def is_battery_charging(self) -> bool:
        """Return whether the battery is actively charging."""
        return self.dock_state == RoborockDockState.charging

    @cached_property
    def fan_speed_options(self) -> list[VacuumModes]:
        return get_clean_modes(self._device_features_trait)

    @cached_property
    def fan_speed_mapping(self) -> dict[int, str]:
        return {fan.code: fan.value for fan in self.fan_speed_options}

    @property
    def supported_cleaning_settings(self) -> frozenset[CleaningSetting]:
        """The cleaning settings this model has at all, independent of the current cleaning mode.

        Use it to decide which settings to offer. Whether a setting can be changed right
        now is is_fan_speed_adjustable, is_water_mode_adjustable and is_mop_route_adjustable.
        The options and mapping of a setting the model does not have are empty. The cleaning
        mode has no entry here: it exists exactly when cleaning_mode_options is not empty,
        which is the case for models with a mop (is_support_water_mode).
        """
        return get_supported_settings(self._device_features_trait)

    @cached_property
    def water_mode_options(self) -> list[WaterModes]:
        if CleaningSetting.WATER_MODE not in self.supported_cleaning_settings:
            return []
        return get_water_modes(self._device_features_trait)

    @cached_property
    def water_mode_mapping(self) -> dict[int, str]:
        if CleaningSetting.WATER_MODE not in self.supported_cleaning_settings:
            return {}
        return get_water_mode_mapping(self._device_features_trait)

    @cached_property
    def mop_route_options(self) -> list[CleanRoutes]:
        if CleaningSetting.MOP_ROUTE not in self.supported_cleaning_settings:
            return []
        return get_clean_routes(self._device_features_trait, self._region or "us")

    @cached_property
    def mop_route_mapping(self) -> dict[int, str]:
        return {route.code: route.display_name for route in self.mop_route_options}

    @cached_property
    def cleaning_mode_options(self) -> list[CleaningMode]:
        return get_cleaning_mode_options(self._device_features_trait)

    @property
    def fan_speed_name(self) -> str | None:
        if self.fan_power is None:
            return None
        return get_fan_speed_name(self.fan_power, self._device_features_trait)

    @property
    def water_mode_name(self) -> str | None:
        if self.water_box_mode is None:
            return None
        return get_water_mode_name(self.water_box_mode, self._device_features_trait)

    @property
    def mop_route_name(self) -> str | None:
        if self.mop_mode is None:
            return None
        return get_mop_route_name(self.mop_mode, self._device_features_trait, self._region or "us")

    @property
    def current_cleaning_mode(self) -> CleaningMode | None:
        return get_current_cleaning_mode(
            clean_mode=self.fan_power,
            water_mode=self.water_box_mode,
            mop_mode=self.mop_mode,
            features=self._device_features_trait,
        )

    @property
    def current_cleaning_mode_name(self) -> str | None:
        if (cleaning_mode := self.current_cleaning_mode) is None:
            return None
        return cleaning_mode.value

    @property
    def _rules_mode(self) -> CleaningMode | None:
        """The mode the adjustable, display and setter rules use.

        A reported SmartPlan or custom state counts even when the model lacks the support
        flags that would make current_cleaning_mode report it.
        """
        special = get_reported_special_mode(
            self.fan_power, self.water_box_mode, self.mop_mode, self._device_features_trait
        )
        return special or self.current_cleaning_mode

    @property
    def is_fan_speed_adjustable(self) -> bool:
        """Whether the fan speed can be changed in the current cleaning mode."""
        adjustable = get_adjustable_settings(self._rules_mode, self._device_features_trait)
        return CleaningSetting.FAN_SPEED in adjustable

    @property
    def is_water_mode_adjustable(self) -> bool:
        """Whether the water mode can be changed in the current cleaning mode."""
        adjustable = get_adjustable_settings(self._rules_mode, self._device_features_trait)
        return CleaningSetting.WATER_MODE in adjustable

    @property
    def is_mop_route_adjustable(self) -> bool:
        """Whether the mop route can be changed in the current cleaning mode."""
        adjustable = get_adjustable_settings(self._rules_mode, self._device_features_trait)
        return CleaningSetting.MOP_ROUTE in adjustable

    @property
    def fan_speed_display_options(self) -> list[VacuumModes]:
        """Fan speeds to show for the current cleaning mode."""
        return get_display_options(
            CleaningSetting.FAN_SPEED, self._rules_mode, self._device_features_trait, self.fan_speed_options
        )

    @property
    def water_mode_display_options(self) -> list[WaterModes]:
        """Water modes to show for the current cleaning mode."""
        return get_display_options(
            CleaningSetting.WATER_MODE, self._rules_mode, self._device_features_trait, self.water_mode_options
        )

    @property
    def mop_route_display_options(self) -> list[CleanRoutes]:
        """Mop routes to show for the current cleaning mode."""
        return get_display_options(
            CleaningSetting.MOP_ROUTE, self._rules_mode, self._device_features_trait, self.mop_route_options
        )

    async def set_cleaning_mode(self, cleaning_mode: str | CleaningMode) -> None:
        """Set the preferred high-level cleaning mode for the device."""
        fan_power, water_box_mode, mop_mode = get_cleaning_mode_codes(
            resolve_cleaning_mode(cleaning_mode), self._device_features_trait, self.mop_mode
        )
        await self._apply_motor_mode(fan_power, water_box_mode, mop_mode)

    async def set_fan_speed(self, mode: VacuumModes) -> None:
        """Set the fan speed while keeping the water mode and mop route."""
        await self._set_cleaning_setting(CleaningSetting.FAN_SPEED, mode.code)

    async def set_water_mode(self, mode: WaterModes) -> None:
        """Set the water mode while keeping the fan speed and mop route."""
        await self._set_cleaning_setting(CleaningSetting.WATER_MODE, mode.code)

    async def set_mop_route(self, route: CleanRoutes) -> None:
        """Set the mop route while keeping the fan speed and water mode."""
        await self._set_cleaning_setting(CleaningSetting.MOP_ROUTE, route.code)

    async def _set_cleaning_setting(self, setting: CleaningSetting, code: int) -> None:
        features = self._device_features_trait
        # A device without a mop has no water mode, so only the fan power has to be loaded.
        if self.fan_power is None or (features.is_support_water_mode and self.water_box_mode is None):
            raise RoborockException("Status is not loaded, call refresh() first")
        fan_power, water_box_mode, mop_mode = get_setting_change_codes(
            setting,
            code,
            self._rules_mode,
            features,
            self._region or "us",
            fan_power=self.fan_power,
            water_box_mode=self.water_box_mode,
            mop_mode=self.mop_mode,
        )
        await self._apply_motor_mode(fan_power, water_box_mode, mop_mode)

    async def _apply_motor_mode(self, fan_power: int, water_box_mode: int | None, mop_mode: int | None) -> None:
        """Send the codes in the order the model needs, then update the cached status.

        The cached fields are updated and listeners are notified once, only after all
        commands have succeeded. A None water mode or mop route leaves that field as it is.
        """
        commands = get_motor_mode_commands(fan_power, water_box_mode, mop_mode, self._device_features_trait)
        for command, params in commands:
            await self.rpc_channel.send_command(command, params=params)
        self.fan_power = fan_power
        if water_box_mode is not None:
            self.water_box_mode = water_box_mode
        if mop_mode is not None:
            self.mop_mode = mop_mode
        self._notify_update()

    async def resolve_error(self, error_code: int | None = None) -> None:
        """Resolve an error, like tapping "Resolved" in the Roborock app.

        Without an explicit code this resolves the current dock error if there is one,
        otherwise the current robot error. A dock error such as water_empty stays latched
        on the device until it is resolved, even after the cause has been fixed.
        """
        if error_code is None:
            if self.dock_error_status:
                error_code = int(self.dock_error_status)
            elif self.error_code:
                error_code = int(self.error_code)
            else:
                return
        await self.rpc_channel.send_command(RoborockCommand.RESOLVE_ERROR, params={"error_code": error_code})
        await self.refresh()

    def update_from_dps(self, decoded_dps: dict[RoborockDataProtocol, Any]) -> None:
        """Update the trait from data protocol push message data.

        This handles unsolicited status updates pushed by the device
        via RoborockDataProtocol codes (e.g. STATE=121, BATTERY=122).
        """
        if _DPS_CONVERTER.update_from_dps(self, decoded_dps):
            self._notify_update()

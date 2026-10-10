import logging
from functools import cached_property
from typing import Any

from roborock import (
    CleaningMode,
    CleanRoutes,
    StatusV2,
    VacuumModes,
    WaterModes,
    get_clean_modes,
    get_clean_routes,
    get_cleaning_mode_options,
    get_cleaning_mode_parameters,
    get_current_cleaning_mode,
    get_water_mode_mapping,
    get_water_modes,
    get_water_slide_mode_name,
    resolve_cleaning_mode,
)
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_message import RoborockDataProtocol
from roborock.roborock_typing import RoborockCommand

from . import common
from .device_features import DeviceFeaturesTrait

_LOGGER = logging.getLogger(__name__)

_DPS_CONVERTER = DpsDataConverter.from_dataclass(StatusV2)

_SEQ_TYPE_CLEAN_THEN_MOP = 1


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
    - Clean then mop (``clean_then_mop``, independent of the cleaning mode)

    You should use the _options version of the attribute to know which are
    supported for your device (i.e. fan_speed_options)
    Then you can use the _mapping to convert an int value to the actual Enum.
    (i.e. fan_speed_mapping)
    You can use the _name property to get the str value of the enum. (i.e. fan_speed_name)

    """

    command = RoborockCommand.GET_STATUS
    converter = common.DefaultConverter(StatusV2)

    def __init__(self, device_feature_trait: DeviceFeaturesTrait, region: str | None = None) -> None:
        """Initialize the StatusTrait."""
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)
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
        return get_water_mode_mapping(self._device_features_trait)

    @cached_property
    def mop_route_options(self) -> list[CleanRoutes]:
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
        return self.fan_speed_mapping.get(self.fan_power)

    @property
    def water_mode_name(self) -> str | None:
        if self.water_box_mode is None:
            return None
        if self._device_features_trait.is_water_slide_mode_supported:
            return get_water_slide_mode_name(self.water_box_mode)
        return self.water_mode_mapping.get(self.water_box_mode)

    @property
    def mop_route_name(self) -> str | None:
        if self.mop_mode is None:
            return None
        return self.mop_route_mapping.get(self.mop_mode)

    @property
    def clean_then_mop(self) -> bool | None:
        """Whether each room is vacuumed fully before it is mopped.

        Reported by the device as ``seq_type`` and persisted on the device: it
        tracks the "vacuum then mop" toggle in the vendor app, also while docked.

        This is a separate axis from ``current_cleaning_mode``. The cleaning
        mode is derived from ``fan_power``, ``water_box_mode`` and ``mop_mode``
        and describes *what* the robot does in a room (vacuum, mop, both). This
        flag describes the *order* when it does both. Changing one leaves the
        other untouched; set it with ``set_clean_then_mop``.

        ``None`` means the device does not support the feature.
        """
        if self.seq_type is None:
            return None
        return self.seq_type == _SEQ_TYPE_CLEAN_THEN_MOP

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

    async def set_cleaning_mode(self, cleaning_mode: str | CleaningMode) -> None:
        """Set the preferred high-level cleaning mode for the device."""
        await self.rpc_channel.send_command(
            RoborockCommand.SET_CLEAN_MOTOR_MODE,
            params=get_cleaning_mode_parameters(resolve_cleaning_mode(cleaning_mode), self._device_features_trait),
        )

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

    async def set_clean_then_mop(self, enabled: bool) -> None:
        """Set whether each room is vacuumed fully before it is mopped.

        Independent of ``set_cleaning_mode``. The firmware requires the current
        motor-mode values in this request, so they are echoed back unchanged.
        """
        if not self._device_features_trait.is_clean_then_mop_mode_supported:
            raise RoborockUnsupportedFeature("Clean then mop is not supported")
        seq_type = _SEQ_TYPE_CLEAN_THEN_MOP if enabled else 0
        params: dict[str, int | None] = {
            "type": seq_type,
            "fan_power": self.fan_power,
            "water_box_mode": self.water_box_mode,
        }
        if self.mop_mode is not None:
            params["mop_mode"] = self.mop_mode
        if enabled and self._device_features_trait.is_ctm_with_repeat_supported:
            params["repeat"] = 1
        await self.rpc_channel.send_command(RoborockCommand.APP_SET_CLEAN_SEQUENCE_TYPE, params=params)
        self.seq_type = seq_type

    def update_from_dps(self, decoded_dps: dict[RoborockDataProtocol, Any]) -> None:
        """Update the trait from data protocol push message data.

        This handles unsolicited status updates pushed by the device
        via RoborockDataProtocol codes (e.g. STATE=121, BATTERY=122).
        """
        if _DPS_CONVERTER.update_from_dps(self, decoded_dps):
            self._notify_update()

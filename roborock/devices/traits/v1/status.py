import asyncio
import logging
from functools import cached_property
from typing import Any

from roborock import (
    CleaningMode,
    CleanRoutes,
    RoborockDockErrorCode,
    RoborockDockState,
    RoborockErrorCode,
    StatusV2,
    VacuumModes,
    WaterModes,
    get_clean_modes,
    get_clean_routes,
    get_cleaning_mode_options,
    get_cleaning_mode_parameters,
    get_current_cleaning_mode,
    get_dock_state,
    get_water_mode_mapping,
    get_water_modes,
    get_water_slide_mode_name,
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

# Delay before reading status back after a fan power or water mode push. The
# robot never pushes the mop mode, so a read-back is needed to get it right.
_STATUS_REFRESH_DELAY = 1.0

# Non-slider codes that water-slide devices report as valid (custom and smart mode).
_WATER_MODE_CODES_KEPT = frozenset({WaterModes.CUSTOMIZED.code, WaterModes.SMART_MODE.code})


def _drop_unresolvable_water_level(decoded_dps: dict[RoborockDataProtocol, Any]) -> dict[RoborockDataProtocol, Any]:
    """Return the pushed data without a water code a water-slide device cannot name.

    Water-slide devices push legacy codes (201-203, 208) that get_status never
    returns. Only slider codes, off, smart water, smart mode and custom are kept.
    """
    if RoborockDataProtocol.WATER_BOX_MODE not in decoded_dps:
        return decoded_dps
    # The pushed value is raw JSON, so narrow it to an integer before resolving it.
    raw = decoded_dps[RoborockDataProtocol.WATER_BOX_MODE]
    code: int | None = None
    if isinstance(raw, int) and not isinstance(raw, bool):
        code = raw
    elif isinstance(raw, str):
        try:
            code = int(raw)
        except ValueError:
            code = None
    if code is not None and (code in _WATER_MODE_CODES_KEPT or get_water_slide_mode_name(code) is not None):
        return decoded_dps
    return {key: value for key, value in decoded_dps.items() if key != RoborockDataProtocol.WATER_BOX_MODE}


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
        # A single task serializes the status read-backs after pushes; the flag
        # records that a push still needs one. The task reference is kept so it
        # is not garbage collected and can be cancelled in close().
        self._status_refresh_needed = False
        self._status_refresh_task: asyncio.Task[None] | None = None

    def close(self) -> None:
        """Cancel any pending or running status read-back."""
        self._status_refresh_needed = False
        if self._status_refresh_task:
            self._status_refresh_task.cancel()
            self._status_refresh_task = None

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
        on the device until it is resolved, even after the cause has been fixed. Error
        codes this library does not recognize are not resolved automatically.
        """
        if error_code is None:
            if self.dock_error_status and self.dock_error_status != RoborockDockErrorCode.unknown:
                error_code = int(self.dock_error_status)
            elif self.error_code and self.error_code != RoborockErrorCode.unknown:
                error_code = int(self.error_code)
            else:
                return
        await self.rpc_channel.send_command(RoborockCommand.RESOLVE_ERROR, params={"error_code": error_code})
        await self.refresh()

    def update_from_dps(self, decoded_dps: dict[RoborockDataProtocol, Any]) -> None:
        """Update the trait from data protocol push message data.

        This handles unsolicited status updates pushed by the device
        via RoborockDataProtocol codes (e.g. STATE=121, BATTERY=122).

        A push of the fan power or water mode also schedules a debounced status
        read-back, since the device never pushes the mop mode. This needs a
        running event loop.
        """
        # Decide on the raw push, before the water code filter below rebinds it.
        needs_read_back = (
            RoborockDataProtocol.FAN_POWER in decoded_dps or RoborockDataProtocol.WATER_BOX_MODE in decoded_dps
        )
        # Water-slide devices push legacy codes (e.g. 201-203, 208) while get_status
        # returns slider codes, so a pushed legacy code would overwrite the real value.
        if self._device_features_trait.is_water_slide_mode_supported:
            decoded_dps = _drop_unresolvable_water_level(decoded_dps)
        if _DPS_CONVERTER.update_from_dps(self, decoded_dps):
            self._notify_update()
        if needs_read_back:
            self._schedule_status_refresh()

    def _schedule_status_refresh(self) -> None:
        """Request a debounced status read-back, starting the worker if it is idle."""
        self._status_refresh_needed = True
        # At most one read-back per delay window, and never two at once.
        if self._status_refresh_task and not self._status_refresh_task.done():
            return
        # Look up the loop first so a missing loop raises before a coroutine is created.
        loop = asyncio.get_running_loop()
        self._status_refresh_task = loop.create_task(self._refresh_status_after_push())

    async def _refresh_status_after_push(self) -> None:
        """Read status back after a short delay to pick up values that are not pushed."""
        while self._status_refresh_needed:
            await asyncio.sleep(_STATUS_REFRESH_DELAY)
            # Clear before reading so a push during the read-back requests another one.
            self._status_refresh_needed = False
            try:
                await self.refresh_and_notify()
            except RoborockException as err:
                _LOGGER.warning("Failed to refresh status after a push: %s", err)

    async def refresh_and_notify(self) -> None:
        """Refresh the status and notify update listeners if any value changed."""
        before = self.as_dict()
        await self.refresh()
        if self.as_dict() != before:
            self._notify_update()

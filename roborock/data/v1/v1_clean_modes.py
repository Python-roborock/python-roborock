from __future__ import annotations

import typing
from enum import StrEnum
from typing import TypeVar

from ...exceptions import RoborockUnsupportedFeature
from ..code_mappings import RoborockModeEnum

if typing.TYPE_CHECKING:
    from roborock.device_features import DeviceFeatures


class VacuumModes(RoborockModeEnum):
    GENTLE = ("gentle", 105)
    OFF = ("off", 105)
    QUIET = ("quiet", 101)
    BALANCED = ("balanced", 102)
    TURBO = ("turbo", 103)
    MAX = ("max", 104)
    MAX_PLUS = ("max_plus", 108)
    OFF_RAISE_MAIN_BRUSH = ("off_raise_main_brush", 109)
    CUSTOMIZED = ("custom", 106)
    SMART_MODE = ("smart_mode", 110)


class CleanRoutes(RoborockModeEnum):
    STANDARD = ("standard", 300)
    DEEP = ("deep", 301)
    DEEP_PLUS = ("deep_plus", 303)
    FAST = ("fast", 304)
    DEEP_PLUS_CN = ("deep_plus", 305)
    SMART_MODE = ("smart_mode", 306)
    CUSTOMIZED = ("custom", 302)


class VacuumModesOld(RoborockModeEnum):
    QUIET = ("quiet", 38)
    BALANCED = ("balanced", 60)
    TURBO = ("turbo", 75)
    MAX = ("max", 100)


class WaterModes(RoborockModeEnum):
    OFF = ("off", 200)
    LOW = ("low", 201)
    MILD = ("mild", 201)
    MEDIUM = ("medium", 202)
    STANDARD = ("standard", 202)
    HIGH = ("high", 203)
    INTENSE = ("intense", 203)
    MIN = ("min", 205)
    MAX = ("max", 206)
    CUSTOMIZED = ("custom", 204)
    CUSTOM = ("custom_water_flow", 207)
    EXTREME = ("extreme", 208)
    SMART_MODE = ("smart_mode", 209)
    PURE_WATER_FLOW_START = ("slight", 221)
    PURE_WATER_FLOW_SMALL = ("low", 225)
    PURE_WATER_FLOW_MIDDLE = ("medium", 235)
    PURE_WATER_FLOW_LARGE = ("moderate", 245)
    PURE_WATER_SUPER_BEGIN = ("high", 248)
    PURE_WATER_FLOW_END = ("extreme", 250)


class WashTowelModes(RoborockModeEnum):
    SMART = ("smart", 10)
    LIGHT = ("light", 0)
    BALANCED = ("balanced", 1)
    DEEP = ("deep", 2)
    SUPER_DEEP = ("super_deep", 8)


class CleaningMode(StrEnum):
    """High-level cleaning intent derived from the lower-level motor settings.

    Prefer this abstraction when you want to present or switch between the
    user-facing cleaning behaviors exposed by the app. The lower-level
    `VacuumModes`, `WaterModes`, and `CleanRoutes` enums are still useful for
    fine-grained selection.
    """

    VACUUM = "vacuum"
    VAC_AND_MOP = "vac_and_mop"
    MOP = "mop"
    CUSTOM = "custom"
    SMART_MODE = "smart_mode"


WATER_SLIDE_MODE_MAPPING: dict[int, WaterModes] = {
    200: WaterModes.OFF,
    221: WaterModes.PURE_WATER_FLOW_START,
    225: WaterModes.PURE_WATER_FLOW_SMALL,
    235: WaterModes.PURE_WATER_FLOW_MIDDLE,
    245: WaterModes.PURE_WATER_FLOW_LARGE,
    248: WaterModes.PURE_WATER_SUPER_BEGIN,
    250: WaterModes.PURE_WATER_FLOW_END,
}

ModeEnumT = TypeVar("ModeEnumT", bound=RoborockModeEnum)


def get_wash_towel_modes(features: DeviceFeatures) -> list[WashTowelModes]:
    """Get the valid wash towel modes for the device"""
    modes = [WashTowelModes.LIGHT, WashTowelModes.BALANCED, WashTowelModes.DEEP]
    if features.is_super_deep_wash_supported and not features.is_dirty_replenish_clean_supported:
        modes.append(WashTowelModes.SUPER_DEEP)
    elif features.is_dirty_replenish_clean_supported:
        modes.append(WashTowelModes.SMART)
    return modes


def get_clean_modes(features: DeviceFeatures) -> list[VacuumModes]:
    """Get the valid clean modes for the device - also known as 'fan power' or 'suction mode'"""
    modes = [VacuumModes.QUIET, VacuumModes.BALANCED, VacuumModes.TURBO, VacuumModes.MAX]
    if features.is_max_plus_mode_supported or features.is_none_pure_clean_mop_with_max_plus:
        # If the vacuum has max plus mode supported
        modes.append(VacuumModes.MAX_PLUS)
    if features.is_pure_clean_mop_supported:
        # If the vacuum is capable of 'pure mop clean' aka no vacuum
        if features.is_support_main_brush_up_down_supported:
            modes.append(VacuumModes.OFF_RAISE_MAIN_BRUSH)
        else:
            modes.append(VacuumModes.OFF)
    else:
        # If not, we can add gentle
        modes.append(VacuumModes.GENTLE)
    if features.is_smart_clean_mode_set_supported:
        modes.append(VacuumModes.SMART_MODE)
    if features.is_customized_clean_supported:
        modes.append(VacuumModes.CUSTOMIZED)
    return modes


def get_clean_routes(features: DeviceFeatures, region: str) -> list[CleanRoutes]:
    """The routes that the vacuum will take while mopping"""
    if features.is_none_pure_clean_mop_with_max_plus:
        return [CleanRoutes.FAST, CleanRoutes.STANDARD]
    supported = [CleanRoutes.STANDARD, CleanRoutes.DEEP]
    if features.is_careful_slow_mop_supported:
        if not (
            features.is_corner_clean_mode_supported
            and features.is_clean_route_deep_slow_plus_supported
            and region == "cn"
        ):
            # for some reason there is a china specific deep plus mode
            supported.append(CleanRoutes.DEEP_PLUS_CN)
        else:
            supported.append(CleanRoutes.DEEP_PLUS)

    if features.is_clean_route_fast_mode_supported:
        supported.append(CleanRoutes.FAST)
    if features.is_smart_clean_mode_set_supported:
        supported.append(CleanRoutes.SMART_MODE)
    if features.is_customized_clean_supported:
        supported.append(CleanRoutes.CUSTOMIZED)

    return supported


def get_water_modes(features: DeviceFeatures) -> list[WaterModes]:
    """Get the valid water modes for the device - also known as 'water flow' or 'water level'"""
    # Water slide mode supports a separate set of water flow codes.
    if features.is_water_slide_mode_supported:
        return list(WATER_SLIDE_MODE_MAPPING.values())

    supported_modes = [WaterModes.OFF]
    if features.is_mop_shake_module_supported:
        # For mops that have the vibrating mop pad, they do mild standard intense
        supported_modes.extend([WaterModes.MILD, WaterModes.STANDARD, WaterModes.INTENSE])
    else:
        supported_modes.extend([WaterModes.LOW, WaterModes.MEDIUM, WaterModes.HIGH])
    if features.is_custom_water_box_distance_supported:
        # This is for devices that allow you to set a custom water flow from 0-100
        supported_modes.append(WaterModes.CUSTOM)
    if features.is_mop_shake_module_supported and features.is_mop_shake_water_max_supported:
        supported_modes.append(WaterModes.EXTREME)
    if features.is_smart_clean_mode_set_supported:
        supported_modes.append(WaterModes.SMART_MODE)
    if features.is_customized_clean_supported:
        supported_modes.append(WaterModes.CUSTOMIZED)

    return supported_modes


def get_water_mode_mapping(features: DeviceFeatures) -> dict[int, str]:
    """Get water mode mapping by supported feature set.

    WaterModes contains aliases for multiple codes that share the same value
    string (e.g. low can be 201 or 225). For water slide mode devices we need
    explicit code mapping to preserve those slide-specific codes.
    """
    if features.is_water_slide_mode_supported:
        return {code: mode.value for code, mode in WATER_SLIDE_MODE_MAPPING.items()}
    return {mode.code: mode.value for mode in get_water_modes(features)}


def get_cleaning_mode_options(features: DeviceFeatures) -> list[CleaningMode]:
    """Return the supported high-level cleaning modes for the device.

    These options are the preferred user-facing choices because they bundle the
    correct fan, water, and mop-route settings together for the device. Callers
    should generally present these instead of mixing lower-level mode enums
    unless they explicitly need fine-grained control.
    """
    if not features.is_support_water_mode:
        return []

    supported_water_modes = get_water_modes(features)
    options = [CleaningMode.VACUUM, CleaningMode.VAC_AND_MOP]
    if features.is_pure_clean_mop_supported:
        options.append(CleaningMode.MOP)
    if features.is_customized_clean_supported and WaterModes.CUSTOMIZED in supported_water_modes:
        options.append(CleaningMode.CUSTOM)
    if features.is_smart_clean_mode_set_supported and WaterModes.SMART_MODE in supported_water_modes:
        options.append(CleaningMode.SMART_MODE)
    return options


def get_mop_only_vacuum_mode(features: DeviceFeatures) -> VacuumModes:
    """Determine the vacuum mode to use when you just want to mop.

    There are three cases that must be handled:
    1. The device does not support only mopping.
    2. The device supports raising the vacuum brush while mopping
    3. All other cases.
    """
    if not features.is_pure_clean_mop_supported:
        raise RoborockUnsupportedFeature("Mop-only cleaning is not supported")
    if features.is_support_main_brush_up_down_supported:
        return VacuumModes.OFF_RAISE_MAIN_BRUSH
    return VacuumModes.OFF


def _get_default_mopping_water_mode(features: DeviceFeatures) -> WaterModes:
    """Pick a sensible default water mode when mopping for the device."""
    # Water-slide devices use a disjoint set of water codes; pick a mid-flow
    # slide code instead of the standard 202, which they don't accept.
    if features.is_water_slide_mode_supported:
        return WaterModes.PURE_WATER_FLOW_MIDDLE
    return WaterModes.STANDARD


def _get_clean_motor_mode_params(
    mode: CleaningMode,
    features: DeviceFeatures,
) -> tuple[VacuumModes, WaterModes, CleanRoutes]:
    """Return (fan_power, water_box_mode, mop_mode) enums for the high-level mode."""
    if mode == CleaningMode.VACUUM:
        return (VacuumModes.BALANCED, WaterModes.OFF, CleanRoutes.STANDARD)
    if mode == CleaningMode.VAC_AND_MOP:
        return (VacuumModes.BALANCED, _get_default_mopping_water_mode(features), CleanRoutes.STANDARD)
    if mode == CleaningMode.MOP:
        return (
            get_mop_only_vacuum_mode(features),
            _get_default_mopping_water_mode(features),
            CleanRoutes.STANDARD,
        )
    if mode == CleaningMode.CUSTOM:
        return (VacuumModes.CUSTOMIZED, WaterModes.CUSTOMIZED, CleanRoutes.CUSTOMIZED)
    if mode == CleaningMode.SMART_MODE:
        return (VacuumModes.SMART_MODE, WaterModes.SMART_MODE, CleanRoutes.SMART_MODE)
    raise RoborockUnsupportedFeature(f"Cleaning mode {mode.value!r} is not supported")


def resolve_cleaning_mode(cleaning_mode: str | CleaningMode) -> CleaningMode:
    """Resolve a string or enum into a CleaningMode value."""
    if isinstance(cleaning_mode, CleaningMode):
        return cleaning_mode
    try:
        return CleaningMode(cleaning_mode)
    except ValueError as err:
        raise RoborockUnsupportedFeature(f"Cleaning mode {cleaning_mode!r} is not supported") from err


def get_cleaning_mode_parameters(cleaning_mode: CleaningMode, features: DeviceFeatures) -> list[dict[str, int]]:
    """Get the RPC payload for switching the high-level cleaning mode."""
    if cleaning_mode not in get_cleaning_mode_options(features):
        raise RoborockUnsupportedFeature(f"Cleaning mode {cleaning_mode.value!r} is not supported")

    fan_power, water_box_mode, mop_mode = _get_clean_motor_mode_params(cleaning_mode, features)
    params: dict[str, int] = {"fan_power": fan_power.code, "water_box_mode": water_box_mode.code}
    if features.is_clean_route_setting_supported:
        params["mop_mode"] = mop_mode.code
    return [params]


def _resolve_mode_code(value: int | ModeEnumT | None, mode_cls: type[ModeEnumT]) -> ModeEnumT | None:
    """Resolve a raw code or enum into a RoborockModeEnum."""
    if value is None:
        return None
    if isinstance(value, mode_cls):
        return value
    return mode_cls.from_code_optional(int(value))


def _resolve_clean_mode(value: int | VacuumModes | None, features: DeviceFeatures) -> VacuumModes | None:
    """Resolve a vacuum mode code, accounting for feature-specific code aliases."""
    if value is None or isinstance(value, VacuumModes):
        return value
    if value == VacuumModes.OFF.code:
        if features.is_pure_clean_mop_supported:
            return get_mop_only_vacuum_mode(features)
        return VacuumModes.GENTLE
    return VacuumModes.from_code_optional(value)


def get_current_cleaning_mode(
    clean_mode: int | VacuumModes | None,
    water_mode: int | WaterModes | None,
    mop_mode: int | CleanRoutes | None,
    features: DeviceFeatures,
) -> CleaningMode | None:
    """Classify the current high-level cleaning mode from individual mode codes."""
    if not features.is_support_water_mode:
        return None
    clean_mode_enum = _resolve_clean_mode(clean_mode, features)
    water_mode_enum = _resolve_mode_code(water_mode, WaterModes)
    mop_mode_enum = _resolve_mode_code(mop_mode, CleanRoutes)
    if clean_mode_enum is None or water_mode_enum is None:
        return None

    if is_smart_mode_set(water_mode_enum, clean_mode_enum, mop_mode_enum):
        return CleaningMode.SMART_MODE
    if is_mode_customized(clean_mode_enum, water_mode_enum, mop_mode_enum):
        return CleaningMode.CUSTOM
    if water_mode_enum != WaterModes.OFF:
        try:
            if clean_mode_enum == get_mop_only_vacuum_mode(features):
                return CleaningMode.MOP
        except RoborockUnsupportedFeature:
            pass
    if water_mode_enum == WaterModes.OFF:
        return CleaningMode.VACUUM
    return CleaningMode.VAC_AND_MOP


def is_mode_customized(
    clean_mode: VacuumModes | None,
    water_mode: WaterModes | None,
    mop_mode: CleanRoutes | None,
) -> bool:
    """Check if any of the cleaning modes are set to a custom value."""
    return (
        clean_mode == VacuumModes.CUSTOMIZED
        or water_mode == WaterModes.CUSTOMIZED
        or mop_mode == CleanRoutes.CUSTOMIZED
    )


def is_smart_mode_set(
    water_mode: WaterModes | None,
    clean_mode: VacuumModes | None,
    mop_mode: CleanRoutes | None,
) -> bool:
    """Check if the smart mode is set for the given water mode and clean mode"""
    return (
        water_mode == WaterModes.SMART_MODE
        or clean_mode == VacuumModes.SMART_MODE
        or mop_mode == CleanRoutes.SMART_MODE
    )

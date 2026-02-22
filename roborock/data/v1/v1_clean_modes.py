from __future__ import annotations

import typing

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
    CARPET = ("carpet", 107)
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
    if features.is_carpet_deep_clean_supported:
        modes.append(VacuumModes.CARPET)
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
    # If the device supports water slide mode, it uses a completely different set of modes. Technically, it can even
    # support values in between. But for now we will just support the main values.
    if features.is_water_slide_mode_supported:
        return [
            WaterModes.PURE_WATER_FLOW_START,
            WaterModes.PURE_WATER_FLOW_SMALL,
            WaterModes.PURE_WATER_FLOW_MIDDLE,
            WaterModes.PURE_WATER_FLOW_LARGE,
            WaterModes.PURE_WATER_SUPER_BEGIN,
            WaterModes.PURE_WATER_FLOW_END,
        ]

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


def is_mode_customized(clean_mode: VacuumModes, water_mode: WaterModes, mop_mode: CleanRoutes) -> bool:
    """Check if any of the cleaning modes are set to a custom value."""
    return (
        clean_mode == VacuumModes.CUSTOMIZED
        or water_mode == WaterModes.CUSTOMIZED
        or mop_mode == CleanRoutes.CUSTOMIZED
    )


def is_smart_mode_set(water_mode: WaterModes, clean_mode: VacuumModes, mop_mode: CleanRoutes) -> bool:
    """Check if the smart mode is set for the given water mode and clean mode"""
    return (
        water_mode == WaterModes.SMART_MODE
        or clean_mode == VacuumModes.SMART_MODE
        or mop_mode == CleanRoutes.SMART_MODE
    )

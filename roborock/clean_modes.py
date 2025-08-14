from __future__ import annotations

from roborock import DeviceFeatures

from .code_mappings import RoborockModeEnum


class CleanModes(RoborockModeEnum):
    GENTLE = ("gentle", 105)
    OFF = ("off", 105)
    QUIET = ("quiet", 101)
    BALANCED = ("balanced", 102)
    TURBO = ("turbo", 103)
    MAX = ("max", 104)
    MAX_PLUS = ("max_plus", 108)
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


class CleanModesOld(RoborockModeEnum):
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
    CUSTOMIZED = ("custom", 204)
    CUSTOM = ("custom_water_flow", 207)
    EXTREME = ("extreme", 208)
    SMART_MODE = ("smart_mode", 209)


def get_clean_modes(features: DeviceFeatures) -> list[CleanModes]:
    """Get the valid clean modes for the device - also known as 'fan power' or 'suction mode'"""
    modes = [CleanModes.QUIET, CleanModes.BALANCED, CleanModes.TURBO, CleanModes.MAX]
    if features.is_max_plus_mode_supported or features.is_none_pure_clean_mop_with_max_plus:
        # If the vacuum has max plus mode supported
        modes.append(CleanModes.MAX_PLUS)
    if features.is_pure_clean_mop_supported:
        # If the vacuum is capable of 'pure mop clean' aka no vacuum
        modes.append(CleanModes.OFF)
    else:
        # If not, we can add gentle
        modes.append(CleanModes.GENTLE)
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
            and region == "CN"
        ):
            # for some reason there is a china specific deep plus mode
            supported.append(CleanRoutes.DEEP_PLUS_CN)
        else:
            supported.append(CleanRoutes.DEEP_PLUS)

    if features.is_clean_route_fast_mode_supported:
        supported.append(CleanRoutes.FAST)
    return supported


def get_water_modes(features: DeviceFeatures) -> list[WaterModes]:
    """Get the valid water modes for the device - also known as 'water flow' or 'water level'"""
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
    return supported_modes

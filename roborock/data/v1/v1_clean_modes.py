from __future__ import annotations

import typing
from enum import StrEnum
from typing import TypeVar, cast

from ...exceptions import RoborockUnsupportedFeature
from ...roborock_typing import RoborockCommand
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
    DEEP_PLUS_CN = ("deep_plus_cn", 305, "deep_plus")
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
    SMART_WATER = ("smart_water", 210)
    PURE_WATER_FLOW_START = ("slight", 221)
    PURE_WATER_FLOW_SMALL = ("pure_water_flow_small", 225, "low")
    PURE_WATER_FLOW_GENTLE = ("gentle", 230)
    PURE_WATER_FLOW_MIDDLE = ("pure_water_flow_middle", 235, "medium")
    PURE_WATER_FLOW_LARGE = ("moderate", 240)
    PURE_WATER_SUPER_BEGIN = ("pure_water_super_begin", 245, "high")
    PURE_WATER_FLOW_END = ("pure_water_flow_end", 250, "extreme")


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


_WATER_SLIDE_MODES: tuple[WaterModes, ...] = (
    WaterModes.OFF,
    WaterModes.PURE_WATER_FLOW_START,
    WaterModes.PURE_WATER_FLOW_SMALL,
    WaterModes.PURE_WATER_FLOW_GENTLE,
    WaterModes.PURE_WATER_FLOW_MIDDLE,
    WaterModes.PURE_WATER_FLOW_LARGE,
    WaterModes.PURE_WATER_SUPER_BEGIN,
    WaterModes.PURE_WATER_FLOW_END,
)

# Water slide devices report the raw slider position (1-30) as 220 + position.
# The app groups positions into named ranges, keyed here by their last position.
_WATER_SLIDE_RANGES: tuple[tuple[int, WaterModes], ...] = (
    (3, WaterModes.PURE_WATER_FLOW_START),
    (7, WaterModes.PURE_WATER_FLOW_SMALL),
    (12, WaterModes.PURE_WATER_FLOW_GENTLE),
    (17, WaterModes.PURE_WATER_FLOW_MIDDLE),
    (22, WaterModes.PURE_WATER_FLOW_LARGE),
    (27, WaterModes.PURE_WATER_SUPER_BEGIN),
    (30, WaterModes.PURE_WATER_FLOW_END),
)

ModeEnumT = TypeVar("ModeEnumT", bound=RoborockModeEnum)


class CleaningSetting(StrEnum):
    """A cleaning setting that can be changed independently of the high-level mode."""

    FAN_SPEED = "fan_speed"
    WATER_MODE = "water_mode"
    MOP_ROUTE = "mop_route"


# SmartPlan and custom values of each setting, shown while the cleaning mode locks the setting.
_SMART_AND_CUSTOM_VALUES: dict[CleaningSetting, tuple[RoborockModeEnum, RoborockModeEnum]] = {
    CleaningSetting.FAN_SPEED: (VacuumModes.SMART_MODE, VacuumModes.CUSTOMIZED),
    CleaningSetting.WATER_MODE: (WaterModes.SMART_MODE, WaterModes.CUSTOMIZED),
    CleaningSetting.MOP_ROUTE: (CleanRoutes.SMART_MODE, CleanRoutes.CUSTOMIZED),
}


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
    if features.is_soft_clean_mode_supported:
        modes.append(VacuumModes.GENTLE)
    return modes


def get_clean_routes(features: DeviceFeatures, region: str) -> list[CleanRoutes]:
    """The routes that the vacuum will take while mopping"""
    if not features.is_clean_route_setting_supported:
        return []
    if features.is_none_pure_clean_mop_with_max_plus:
        return [CleanRoutes.FAST, CleanRoutes.STANDARD]
    supported = [CleanRoutes.STANDARD]
    if not features.is_clean_efficiency_supported:
        supported.append(CleanRoutes.DEEP)
    if features.is_careful_slow_mop_supported:
        if (
            not features.is_corner_clean_mode_supported
            and features.is_clean_route_deep_slow_plus_supported
            and region == "cn"
        ):
            supported.append(CleanRoutes.DEEP_PLUS_CN)
        else:
            supported.append(CleanRoutes.DEEP_PLUS)

    if features.is_clean_route_fast_mode_supported:
        supported.append(CleanRoutes.FAST)

    return supported


def get_water_modes(features: DeviceFeatures) -> list[WaterModes]:
    """Get the valid water modes for the device - also known as 'water flow' or 'water level'"""
    # Water slide mode supports a separate set of water flow codes.
    if features.is_water_slide_mode_supported:
        return list(_WATER_SLIDE_MODES)

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


def get_adjustable_settings(mode: CleaningMode | None, features: DeviceFeatures) -> frozenset[CleaningSetting]:
    """Return the cleaning settings the user can change while the given cleaning mode is active.

    SmartPlan and custom modes decide every setting themselves. A mode of None means
    the current mode is unknown: devices without a mop only have the fan speed,
    otherwise the cleaning mode has to be chosen first. The mop route
    needs the shake module (only those models offer a route choice), and outside mopping only also the fast route.
    """
    if mode is None:
        return frozenset() if features.is_support_water_mode else frozenset({CleaningSetting.FAN_SPEED})
    if mode in (CleaningMode.SMART_MODE, CleaningMode.CUSTOM):
        return frozenset()
    settings: set[CleaningSetting] = set()
    if mode in (CleaningMode.VACUUM, CleaningMode.VAC_AND_MOP):
        settings.add(CleaningSetting.FAN_SPEED)
    # Models without a mop-only mode have one general setting group that includes water in every regular mode.
    has_water_tab = mode in (CleaningMode.VAC_AND_MOP, CleaningMode.MOP) or not features.is_pure_clean_mop_supported
    if has_water_tab and features.is_support_water_mode:
        settings.add(CleaningSetting.WATER_MODE)
    if features.is_shake_mop_set_supported and (
        mode == CleaningMode.MOP
        or (features.is_clean_route_fast_mode_supported and features.is_clean_route_setting_supported)
    ):
        settings.add(CleaningSetting.MOP_ROUTE)
    return frozenset(settings)


def get_mode_options(
    setting: CleaningSetting,
    mode: CleaningMode | None,
    features: DeviceFeatures,
    options: list[ModeEnumT],
) -> list[ModeEnumT]:
    """Return the values of a setting that are offered in the given cleaning mode.

    The options are the values the model supports for the setting (the *_options lists).
    This keeps the values valid in that mode: Max+ only in vacuum only (or on devices
    without tabs, by the other flag), the short route list outside mopping only, and no water
    off on devices that have a mop-only tab. The result is empty when the setting cannot be
    changed in the mode. It is also the list of values the setters accept.
    """
    if setting not in get_adjustable_settings(mode, features):
        return []
    if setting == CleaningSetting.FAN_SPEED:
        return [option for option in options if _is_fan_speed_offered(option.code, mode, features)]
    if setting == CleaningSetting.WATER_MODE:
        if features.is_pure_clean_mop_supported:
            return [option for option in options if option.code != WaterModes.OFF.code]
        return list(options)
    if _offers_all_routes(mode, features):
        return list(options)
    return [option for option in options if option.code in (CleanRoutes.FAST.code, CleanRoutes.STANDARD.code)]


def _is_fan_speed_offered(code: int, mode: CleaningMode | None, features: DeviceFeatures) -> bool:
    """Whether the fan speed is offered in the mode: only Max+ depends on it."""
    if code != VacuumModes.MAX_PLUS.code or mode is None:
        return True
    if not features.is_pure_clean_mop_supported:
        return features.is_none_pure_clean_mop_with_max_plus
    return mode == CleaningMode.VACUUM and features.is_max_plus_mode_supported


def _offers_all_routes(mode: CleaningMode | None, features: DeviceFeatures) -> bool:
    """Whether the mop route list of the mode is the model's full list."""
    return (
        features.is_none_pure_clean_mop_with_max_plus  # the model list is only fast and standard
        or features.is_clean_efficiency_supported
        or mode == CleaningMode.MOP
        or not features.is_pure_clean_mop_supported
    )


def get_display_options(
    setting: CleaningSetting,
    mode: CleaningMode | None,
    features: DeviceFeatures,
    options: list[ModeEnumT],
) -> list[ModeEnumT]:
    """Return the values of a setting to show for the current cleaning mode.

    In SmartPlan only its SmartPlan value is shown and in custom mode only its custom value.
    A setting that can be changed shows the values of the mode (see get_mode_options)
    and any other setting shows nothing.
    A setting the device does not have (no options) always shows nothing, and so does the
    mop route without the shake module, SmartPlan and custom values included.
    """
    if not options:
        return []
    if setting == CleaningSetting.MOP_ROUTE and not features.is_shake_mop_set_supported:
        return []
    smart_value, custom_value = _SMART_AND_CUSTOM_VALUES[setting]
    if mode == CleaningMode.SMART_MODE:
        return [cast(ModeEnumT, smart_value)]
    if mode == CleaningMode.CUSTOM:
        return [cast(ModeEnumT, custom_value)]
    return get_mode_options(setting, mode, features, options)


def get_fan_speed_name(code: int, features: DeviceFeatures) -> str | None:
    """Name a fan power code: selectable modes first, then SmartPlan, custom and code 105."""
    for mode in get_clean_modes(features):
        if mode.code == code:
            return mode.value
    if code == VacuumModes.SMART_MODE.code:
        return VacuumModes.SMART_MODE.value
    if code == VacuumModes.CUSTOMIZED.code:
        return VacuumModes.CUSTOMIZED.value
    if code == VacuumModes.GENTLE.code:
        # 105 is the mop-only code on pure-mop devices and "gentle" elsewhere.
        return VacuumModes.OFF.value if features.is_pure_clean_mop_supported else VacuumModes.GENTLE.value
    return None


def get_water_mode_name(code: int, features: DeviceFeatures) -> str | None:
    """Name a water box code: selectable modes (or slide ranges) first, then SmartPlan and custom."""
    if features.is_water_slide_mode_supported:
        slide_mode = _resolve_water_slide_mode(code)
        if slide_mode is not None:
            return slide_mode.display_name
    else:
        for mode in get_water_modes(features):
            if mode.code == code:
                return mode.display_name
    if code == WaterModes.SMART_MODE.code:
        return WaterModes.SMART_MODE.display_name
    if code == WaterModes.CUSTOMIZED.code:
        return WaterModes.CUSTOMIZED.display_name
    return None


def get_mop_route_name(code: int, features: DeviceFeatures, region: str) -> str | None:
    """Name a mop route code: selectable routes first, then SmartPlan and custom."""
    for route in get_clean_routes(features, region):
        if route.code == code:
            return route.display_name
    if code == CleanRoutes.SMART_MODE.code:
        return CleanRoutes.SMART_MODE.display_name
    if code == CleanRoutes.CUSTOMIZED.code:
        return CleanRoutes.CUSTOMIZED.display_name
    return None


def get_water_slide_mode_name(code: int) -> str | None:
    """Get the app's range name for a water slide code, or None if out of range."""
    mode = _resolve_water_slide_mode(code)
    return mode.display_name if mode is not None else None


def _resolve_water_slide_mode(code: int) -> WaterModes | None:
    """Resolve a raw slider code to the water mode for its app range."""
    if code == 200:
        return WaterModes.OFF
    if code == WaterModes.SMART_WATER.code:
        return WaterModes.SMART_WATER
    position = code - 220
    if position < 1:
        return None
    for last_position, mode in _WATER_SLIDE_RANGES:
        if position <= last_position:
            return mode
    return None


def get_water_mode_mapping(features: DeviceFeatures) -> dict[int, str]:
    """Get water mode mapping by supported feature set.

    Water slide modes share user-facing names with legacy modes (e.g. "low" is
    201 or 225), so the mapping uses display_name rather than the enum value.
    """
    return {mode.code: mode.display_name for mode in get_water_modes(features)}


def get_cleaning_mode_options(features: DeviceFeatures) -> list[CleaningMode]:
    """Return the supported high-level cleaning modes for the device.

    These options are the preferred user-facing choices because they bundle the
    correct fan, water, and mop-route settings together for the device. Callers
    should generally present these instead of mixing lower-level mode enums
    unless they explicitly need fine-grained control.
    """
    if not features.is_support_water_mode:
        return []

    options = [CleaningMode.VACUUM, CleaningMode.VAC_AND_MOP]
    if features.is_pure_clean_mop_supported:
        options.append(CleaningMode.MOP)
    # The customized-clean flag stays required until the app's custom switch
    # condition is verified; without it electronic-mop models would gain CUSTOM.
    if features.is_custom_mode_supported and features.is_customized_clean_supported:
        options.append(CleaningMode.CUSTOM)
    if features.is_smart_clean_mode_set_supported:
        options.append(CleaningMode.SMART_MODE)
    return options


def get_mop_only_vacuum_mode(features: DeviceFeatures) -> VacuumModes:
    """Return the vacuum mode used by the app for mop-only cleaning."""
    if not features.is_pure_clean_mop_supported:
        raise RoborockUnsupportedFeature("Mop-only cleaning is not supported")
    # Main-brush lift is a device capability, not an alternate fan-power
    # command. The app still sends CleanModeZero (105) for mop-only cleaning.
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


MotorModeCommand = tuple[RoborockCommand, list[int] | list[dict[str, int]]]


def get_cleaning_mode_codes(
    mode: CleaningMode,
    features: DeviceFeatures,
    current_mop_mode: int | None,
) -> tuple[int, int, int | None]:
    """Return the (fan_power, water_box_mode, mop_mode) codes that switch to a cleaning mode.

    The mop route is None when there is nothing to send: the device has no route
    setting or no shake module (the route is only sent with it) and its current
    route does not need to change. When the current route is
    SmartPlan (306) or custom (302) it is reset to standard (300), so the robot is not
    still recognized as being in that mode, unless the target mode is the one that
    owns the current route (SmartPlan for 306, custom for 302).
    """
    if mode not in get_cleaning_mode_options(features):
        raise RoborockUnsupportedFeature(f"Cleaning mode {mode.value!r} is not supported")

    fan_power, water_box_mode, mop_mode = _get_clean_motor_mode_params(mode, features)
    if features.is_clean_route_setting_supported and features.is_shake_mop_set_supported:
        route: int | None = mop_mode.code
    elif current_mop_mode == CleanRoutes.SMART_MODE.code and mode != CleaningMode.SMART_MODE:
        route = CleanRoutes.STANDARD.code
    elif current_mop_mode == CleanRoutes.CUSTOMIZED.code and mode != CleaningMode.CUSTOM:
        route = CleanRoutes.STANDARD.code
    else:
        route = None
    return fan_power.code, water_box_mode.code, route


def get_cleaning_mode_parameters(cleaning_mode: CleaningMode, features: DeviceFeatures) -> list[dict[str, int]]:
    """Get the combined set_clean_motor_mode payload for switching the high-level cleaning mode.

    This does not reflect the per-model command sequencing or the reset of the current
    route; see get_motor_mode_commands and get_cleaning_mode_codes for what is sent.
    """
    if cleaning_mode not in get_cleaning_mode_options(features):
        raise RoborockUnsupportedFeature(f"Cleaning mode {cleaning_mode.value!r} is not supported")
    # Unlike get_cleaning_mode_codes this keeps the route of every model with a route setting.
    fan_power, water_box_mode, mop_mode = _get_clean_motor_mode_params(cleaning_mode, features)
    params: dict[str, int] = {"fan_power": fan_power.code, "water_box_mode": water_box_mode.code}
    if features.is_clean_route_setting_supported:
        params["mop_mode"] = mop_mode.code
    return [params]


def get_motor_mode_commands(
    fan_power: int,
    water_box_mode: int | None,
    mop_mode: int | None,
    features: DeviceFeatures,
) -> list[MotorModeCommand]:
    """Return the commands, in order, that apply the codes in the order the model needs.

    A device without a mop (no water mode support) only has a fan speed, so it only gets
    set_custom_mode. The water mode is None only for such devices.
    """
    if not features.is_support_water_mode or water_box_mode is None:
        return [(RoborockCommand.SET_CUSTOM_MODE, [fan_power])]
    if features.is_shake_mop_set_supported:
        params = {"fan_power": fan_power, "water_box_mode": water_box_mode}
        if mop_mode is not None:
            params["mop_mode"] = mop_mode
        return [(RoborockCommand.SET_CLEAN_MOTOR_MODE, [params])]
    if features.is_set_clean_motor_mode_supported:
        commands: list[MotorModeCommand] = [
            (RoborockCommand.SET_CLEAN_MOTOR_MODE, [{"fan_power": fan_power, "water_box_mode": water_box_mode}])
        ]
    else:
        commands = [
            (RoborockCommand.SET_CUSTOM_MODE, [fan_power]),
            (RoborockCommand.SET_WATER_BOX_CUSTOM_MODE, [water_box_mode]),
        ]
    if mop_mode is not None:
        commands.append((RoborockCommand.SET_MOP_MODE, [mop_mode]))
    return commands


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


def _resolve_water_mode(value: int | WaterModes | None, features: DeviceFeatures) -> WaterModes | None:
    """Resolve a water mode code, mapping raw slider positions on water slide devices."""
    if value is None or isinstance(value, WaterModes):
        return value
    if features.is_water_slide_mode_supported:
        return _resolve_water_slide_mode(value) or WaterModes.from_code_optional(value)
    return WaterModes.from_code_optional(value)


def get_current_cleaning_mode(
    clean_mode: int | VacuumModes | None,
    water_mode: int | WaterModes | None,
    mop_mode: int | CleanRoutes | None,
    features: DeviceFeatures,
) -> CleaningMode | None:
    """Classify the current high-level cleaning mode from individual mode codes.

    The result is None when the classified mode is not in get_cleaning_mode_options(features).
    """
    if not features.is_support_water_mode:
        return None
    clean_mode_enum = _resolve_clean_mode(clean_mode, features)
    water_mode_enum = _resolve_water_mode(water_mode, features)
    mop_mode_enum = _resolve_mode_code(mop_mode, CleanRoutes)
    if clean_mode_enum is None or water_mode_enum is None:
        return None

    mode = _classify_cleaning_mode(clean_mode_enum, water_mode_enum, mop_mode_enum, features)
    if mode not in get_cleaning_mode_options(features):
        return None
    return mode


def _classify_cleaning_mode(
    clean_mode: VacuumModes,
    water_mode: WaterModes,
    mop_mode: CleanRoutes | None,
    features: DeviceFeatures,
) -> CleaningMode:
    """Classify resolved mode enums, checking custom before SmartPlan like the app."""
    if is_mode_customized(clean_mode, water_mode, mop_mode):
        return CleaningMode.CUSTOM
    if is_smart_mode_set(water_mode, clean_mode, mop_mode):
        return CleaningMode.SMART_MODE
    if water_mode != WaterModes.OFF:
        try:
            if clean_mode == get_mop_only_vacuum_mode(features):
                return CleaningMode.MOP
        except RoborockUnsupportedFeature:
            pass
    if water_mode == WaterModes.OFF:
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

"""Tests for the pure V1 cleaning mode helpers."""

import itertools

import pytest

from roborock.data.v1.v1_clean_modes import (
    CleaningMode,
    CleaningSetting,
    CleanRoutes,
    MotorModeCommand,
    VacuumModes,
    WaterModes,
    get_adjustable_settings,
    get_clean_modes,
    get_clean_routes,
    get_cleaning_mode_codes,
    get_cleaning_mode_options,
    get_display_options,
    get_motor_mode_commands,
    get_reported_special_mode,
    get_setting_change_codes,
    get_supported_settings,
    get_water_modes,
)
from roborock.device_features import DeviceFeatures
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand


def _features(**overrides: bool) -> DeviceFeatures:
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=0, new_feature_info_str="", feature_info=[], product_nickname=None
    )
    features.is_support_water_mode = True
    features.is_clean_route_setting_supported = True
    features.is_shake_mop_set_supported = True
    features.is_clean_route_fast_mode_supported = True
    for name, value in overrides.items():
        setattr(features, name, value)
    return features


_ALL = frozenset(CleaningSetting)


@pytest.mark.parametrize(
    ("mode", "overrides", "expected"),
    [
        (CleaningMode.SMART_MODE, {}, frozenset()),
        (CleaningMode.CUSTOM, {}, frozenset()),
        (CleaningMode.VACUUM, {}, frozenset({CleaningSetting.FAN_SPEED, CleaningSetting.MOP_ROUTE})),
        (CleaningMode.VAC_AND_MOP, {}, _ALL),
        (CleaningMode.VAC_AND_MOP, {"is_clean_route_setting_supported": False}, _ALL - {CleaningSetting.MOP_ROUTE}),
        (CleaningMode.MOP, {}, _ALL - {CleaningSetting.FAN_SPEED}),
        # The route needs the shake module in every mode.
        (CleaningMode.VACUUM, {"is_shake_mop_set_supported": False}, frozenset({CleaningSetting.FAN_SPEED})),
        (
            CleaningMode.VAC_AND_MOP,
            {"is_shake_mop_set_supported": False},
            frozenset({CleaningSetting.FAN_SPEED, CleaningSetting.WATER_MODE}),
        ),
        (CleaningMode.MOP, {"is_shake_mop_set_supported": False}, frozenset({CleaningSetting.WATER_MODE})),
        # Without the fast route the route is only adjustable while mopping only.
        (CleaningMode.VACUUM, {"is_clean_route_fast_mode_supported": False}, frozenset({CleaningSetting.FAN_SPEED})),
        (
            CleaningMode.VAC_AND_MOP,
            {"is_clean_route_fast_mode_supported": False},
            frozenset({CleaningSetting.FAN_SPEED, CleaningSetting.WATER_MODE}),
        ),
        (CleaningMode.MOP, {"is_clean_route_fast_mode_supported": False}, _ALL - {CleaningSetting.FAN_SPEED}),
        (None, {}, frozenset()),
        (None, {"is_support_water_mode": False}, frozenset({CleaningSetting.FAN_SPEED})),
    ],
)
def test_get_adjustable_settings(
    mode: CleaningMode | None, overrides: dict[str, bool], expected: frozenset[CleaningSetting]
) -> None:
    features = _features(**{"is_pure_clean_mop_supported": True, **overrides})
    assert get_adjustable_settings(mode, features) == expected


@pytest.mark.parametrize(
    ("mode", "overrides", "expected"),
    [
        # Without mode tabs the robot has one general setting group: water is offered even when the water is off.
        (CleaningMode.VACUUM, {}, _ALL),
        (CleaningMode.VAC_AND_MOP, {}, _ALL),
        (CleaningMode.VACUUM, {"is_shake_mop_set_supported": False}, _ALL - {CleaningSetting.MOP_ROUTE}),
        (
            CleaningMode.VACUUM,
            {"is_clean_route_fast_mode_supported": False},
            _ALL - {CleaningSetting.MOP_ROUTE},
        ),
        (
            CleaningMode.VACUUM,
            {"is_support_water_mode": False},
            _ALL - {CleaningSetting.WATER_MODE},
        ),
        (CleaningMode.SMART_MODE, {}, frozenset()),
        (CleaningMode.CUSTOM, {}, frozenset()),
    ],
)
def test_get_adjustable_settings_without_mode_tabs(
    mode: CleaningMode, overrides: dict[str, bool], expected: frozenset[CleaningSetting]
) -> None:
    features = _features(**{"is_pure_clean_mop_supported": False, **overrides})
    assert get_adjustable_settings(mode, features) == expected


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CleaningMode.SMART_MODE, [VacuumModes.SMART_MODE]),
        (CleaningMode.CUSTOM, [VacuumModes.CUSTOMIZED]),
        (CleaningMode.VACUUM, [VacuumModes.QUIET, VacuumModes.BALANCED]),
        (CleaningMode.MOP, []),
    ],
)
def test_get_display_options_kinds(mode: CleaningMode, expected: list[VacuumModes]) -> None:
    options = [VacuumModes.QUIET, VacuumModes.BALANCED]
    assert get_display_options(CleaningSetting.FAN_SPEED, mode, _features(), options) == expected


@pytest.mark.parametrize("mode", [CleaningMode.SMART_MODE, CleaningMode.CUSTOM, CleaningMode.VACUUM, None])
def test_get_display_options_empty_options_show_nothing(mode: CleaningMode | None) -> None:
    """A setting the device does not have shows nothing, even in SmartPlan or custom mode."""
    assert get_display_options(CleaningSetting.MOP_ROUTE, mode, _features(), []) == []


@pytest.mark.parametrize(
    ("shake", "f118", "mop", "expected"),
    [
        (
            True,
            False,
            300,
            [(RoborockCommand.SET_CLEAN_MOTOR_MODE, [{"fan_power": 102, "water_box_mode": 202, "mop_mode": 300}])],
        ),
        (True, True, None, [(RoborockCommand.SET_CLEAN_MOTOR_MODE, [{"fan_power": 102, "water_box_mode": 202}])]),
        (False, True, None, [(RoborockCommand.SET_CLEAN_MOTOR_MODE, [{"fan_power": 102, "water_box_mode": 202}])]),
        (
            False,
            True,
            300,
            [
                (RoborockCommand.SET_CLEAN_MOTOR_MODE, [{"fan_power": 102, "water_box_mode": 202}]),
                (RoborockCommand.SET_MOP_MODE, [300]),
            ],
        ),
        (
            False,
            False,
            None,
            [(RoborockCommand.SET_CUSTOM_MODE, [102]), (RoborockCommand.SET_WATER_BOX_CUSTOM_MODE, [202])],
        ),
        (
            False,
            False,
            300,
            [
                (RoborockCommand.SET_CUSTOM_MODE, [102]),
                (RoborockCommand.SET_WATER_BOX_CUSTOM_MODE, [202]),
                (RoborockCommand.SET_MOP_MODE, [300]),
            ],
        ),
    ],
)
def test_get_motor_mode_commands(shake: bool, f118: bool, mop: int | None, expected: list[MotorModeCommand]) -> None:
    features = _features(is_shake_mop_set_supported=shake, is_set_clean_motor_mode_supported=f118)
    assert get_motor_mode_commands(102, 202, mop, features) == expected


@pytest.mark.parametrize("mop", [None, 300])
@pytest.mark.parametrize(("shake", "f118"), [(False, False), (True, False), (False, True), (True, True)])
def test_get_motor_mode_commands_vacuum_only(shake: bool, f118: bool, mop: int | None) -> None:
    """Devices without a mop only ever get the fan command."""
    features = _features(
        is_support_water_mode=False, is_shake_mop_set_supported=shake, is_set_clean_motor_mode_supported=f118
    )
    assert get_motor_mode_commands(104, None, mop, features) == [(RoborockCommand.SET_CUSTOM_MODE, [104])]


@pytest.mark.parametrize(
    ("mode", "overrides", "current_mop_mode", "expected"),
    [
        (CleaningMode.VACUUM, {}, None, (102, 200, 300)),
        (CleaningMode.VAC_AND_MOP, {}, 302, (102, 202, 300)),
        (CleaningMode.MOP, {}, None, (105, 202, 300)),
        (CleaningMode.CUSTOM, {}, None, (106, 204, 302)),
        (CleaningMode.SMART_MODE, {"is_smart_clean_mode_set_supported": True}, None, (110, 209, 306)),
        (CleaningMode.VAC_AND_MOP, {"is_water_slide_mode_supported": True}, None, (102, 235, 300)),
        # Without a route setting the route is only sent to leave SmartPlan or custom.
        (CleaningMode.VACUUM, {"is_clean_route_setting_supported": False}, None, (102, 200, None)),
        (CleaningMode.VACUUM, {"is_clean_route_setting_supported": False}, 300, (102, 200, None)),
        (CleaningMode.VACUUM, {"is_clean_route_setting_supported": False}, 302, (102, 200, 300)),
        (CleaningMode.VAC_AND_MOP, {"is_clean_route_setting_supported": False}, 306, (102, 202, 300)),
        (CleaningMode.VAC_AND_MOP, {"is_clean_route_setting_supported": False}, 302, (102, 202, 300)),
        # The route of the mode is only sent with the shake module; without it only the reset remains.
        (CleaningMode.VAC_AND_MOP, {"is_shake_mop_set_supported": False}, None, (102, 202, None)),
        (CleaningMode.VAC_AND_MOP, {"is_shake_mop_set_supported": False}, 301, (102, 202, None)),
        (CleaningMode.VAC_AND_MOP, {"is_shake_mop_set_supported": False}, 306, (102, 202, 300)),
        (CleaningMode.MOP, {"is_shake_mop_set_supported": False}, 302, (105, 202, 300)),
        (CleaningMode.CUSTOM, {"is_shake_mop_set_supported": False}, None, (106, 204, None)),
        (CleaningMode.CUSTOM, {"is_shake_mop_set_supported": False}, 302, (106, 204, None)),
    ],
)
def test_get_cleaning_mode_codes(
    mode: CleaningMode,
    overrides: dict[str, bool],
    current_mop_mode: int | None,
    expected: tuple[int, int, int | None],
) -> None:
    features = _features(is_pure_clean_mop_supported=True, is_customized_clean_supported=True, **overrides)
    features.is_custom_mode_supported = True
    assert get_cleaning_mode_codes(mode, features, current_mop_mode) == expected


@pytest.mark.parametrize(
    ("mode", "fan_water", "current_mop_mode", "expected_route"),
    [
        (CleaningMode.SMART_MODE, (110, 209), None, None),
        (CleaningMode.SMART_MODE, (110, 209), 300, None),
        (CleaningMode.SMART_MODE, (110, 209), 302, 300),
        (CleaningMode.SMART_MODE, (110, 209), 306, None),
        (CleaningMode.CUSTOM, (106, 204), None, None),
        (CleaningMode.CUSTOM, (106, 204), 300, None),
        (CleaningMode.CUSTOM, (106, 204), 302, None),
        (CleaningMode.CUSTOM, (106, 204), 306, 300),
    ],
)
def test_get_cleaning_mode_codes_special_targets_without_route_setting(
    mode: CleaningMode,
    fan_water: tuple[int, int],
    current_mop_mode: int | None,
    expected_route: int | None,
) -> None:
    """SmartPlan and custom keep the route they already own and only reset the other special one."""
    features = _features(
        is_pure_clean_mop_supported=True,
        is_customized_clean_supported=True,
        is_custom_mode_supported=True,
        is_smart_clean_mode_set_supported=True,
        is_clean_route_setting_supported=False,
    )
    assert get_cleaning_mode_codes(mode, features, current_mop_mode) == (*fan_water, expected_route)


def test_get_cleaning_mode_codes_unsupported_mode() -> None:
    with pytest.raises(RoborockUnsupportedFeature, match="not supported"):
        get_cleaning_mode_codes(CleaningMode.SMART_MODE, _features(), None)


@pytest.mark.parametrize(
    ("setting", "code", "mode", "status", "overrides", "expected"),
    [
        (CleaningSetting.FAN_SPEED, 104, CleaningMode.VAC_AND_MOP, (102, 202, 300), {}, (104, 202, 300)),
        (CleaningSetting.WATER_MODE, 203, CleaningMode.MOP, (105, 202, 300), {}, (105, 203, 300)),
        (CleaningSetting.MOP_ROUTE, 301, CleaningMode.MOP, (105, 202, 300), {}, (105, 202, 301)),
        # Without a route setting the route is not sent.
        (
            CleaningSetting.FAN_SPEED,
            103,
            CleaningMode.VACUUM,
            (102, 200, 300),
            {"is_clean_route_setting_supported": False},
            (103, 200, None),
        ),
        # Without the shake module the route is not sent either.
        (
            CleaningSetting.FAN_SPEED,
            103,
            CleaningMode.VACUUM,
            (102, 200, 300),
            {"is_shake_mop_set_supported": False},
            (103, 200, None),
        ),
        # Water slide devices accept every slider position.
        (
            CleaningSetting.WATER_MODE,
            233,
            CleaningMode.VAC_AND_MOP,
            (102, 225, 300),
            {"is_water_slide_mode_supported": True},
            (102, 233, 300),
        ),
    ],
)
def test_get_setting_change_codes(
    setting: CleaningSetting,
    code: int,
    mode: CleaningMode,
    status: tuple[int, int, int],
    overrides: dict[str, bool],
    expected: tuple[int, int, int | None],
) -> None:
    features = _features(is_pure_clean_mop_supported=True, **overrides)
    assert (
        get_setting_change_codes(
            setting, code, mode, features, "us", fan_power=status[0], water_box_mode=status[1], mop_mode=status[2]
        )
        == expected
    )


@pytest.mark.parametrize(
    ("setting", "code", "mode", "overrides"),
    [
        (CleaningSetting.FAN_SPEED, 104, CleaningMode.SMART_MODE, {}),
        (CleaningSetting.FAN_SPEED, 104, CleaningMode.CUSTOM, {}),
        (CleaningSetting.FAN_SPEED, 104, None, {}),
        (CleaningSetting.FAN_SPEED, 104, CleaningMode.MOP, {}),
        (CleaningSetting.WATER_MODE, 203, CleaningMode.VACUUM, {}),
        (CleaningSetting.FAN_SPEED, 110, CleaningMode.VAC_AND_MOP, {}),
        (CleaningSetting.FAN_SPEED, 999, CleaningMode.VAC_AND_MOP, {}),
        (CleaningSetting.WATER_MODE, 220, CleaningMode.VAC_AND_MOP, {"is_water_slide_mode_supported": True}),
        (CleaningSetting.WATER_MODE, 251, CleaningMode.VAC_AND_MOP, {"is_water_slide_mode_supported": True}),
        (CleaningSetting.MOP_ROUTE, 302, CleaningMode.VAC_AND_MOP, {}),
        # Mopping without water is not mopping.
        (CleaningSetting.WATER_MODE, 200, CleaningMode.MOP, {}),
    ],
)
def test_get_setting_change_codes_refused(
    setting: CleaningSetting, code: int, mode: CleaningMode | None, overrides: dict[str, bool]
) -> None:
    features = _features(is_pure_clean_mop_supported=True, **overrides)
    with pytest.raises(RoborockUnsupportedFeature):
        get_setting_change_codes(setting, code, mode, features, "us", fan_power=102, water_box_mode=202, mop_mode=300)


@pytest.mark.parametrize("route_supported", [True, False])
def test_get_setting_change_codes_vacuum_only(route_supported: bool) -> None:
    """Without a mop there is no water mode or route to carry along."""
    features = _features(is_support_water_mode=False, is_clean_route_setting_supported=route_supported)
    assert get_setting_change_codes(
        CleaningSetting.FAN_SPEED, 104, None, features, "us", fan_power=102, water_box_mode=None, mop_mode=None
    ) == (104, None, None)


_SAROS_10R = {
    "is_soft_clean_mode_supported": False,
    "is_pure_clean_mop_supported": True,
    "is_shake_mop_set_supported": True,
    "is_clean_route_setting_supported": True,
    "is_clean_route_fast_mode_supported": True,
    "is_careful_slow_mop_supported": True,
    "is_max_plus_mode_supported": True,
    "is_water_slide_mode_supported": True,
}
_FAN_BASE = [VacuumModes.QUIET, VacuumModes.BALANCED, VacuumModes.TURBO, VacuumModes.MAX]
_ROUTES_FULL = {CleanRoutes.STANDARD, CleanRoutes.DEEP, CleanRoutes.DEEP_PLUS, CleanRoutes.FAST}
_ROUTES_SHORT = {CleanRoutes.FAST, CleanRoutes.STANDARD}
_ROUTES_EFFICIENCY = {CleanRoutes.STANDARD, CleanRoutes.DEEP_PLUS, CleanRoutes.FAST}


def _mode_display_options(
    setting: CleaningSetting, mode: CleaningMode, overrides: dict[str, bool]
) -> list[VacuumModes] | list[WaterModes] | list[CleanRoutes]:
    """The display options of a setting for a device with the Saros 10R flags changed by overrides."""
    features = _features(**{**_SAROS_10R, **overrides})
    if setting == CleaningSetting.FAN_SPEED:
        return get_display_options(setting, mode, features, get_clean_modes(features))
    if setting == CleaningSetting.WATER_MODE:
        return get_display_options(setting, mode, features, get_water_modes(features))
    return get_display_options(setting, mode, features, get_clean_routes(features, "us"))


@pytest.mark.parametrize(
    ("mode", "overrides", "expected"),
    [
        (CleaningMode.VAC_AND_MOP, {}, _FAN_BASE),
        (CleaningMode.VACUUM, {}, [*_FAN_BASE, VacuumModes.MAX_PLUS]),
        (CleaningMode.MOP, {}, []),
        # Max+ in the vacuum tab needs is_max_plus_mode_supported; the other flag alone does not add it.
        (
            CleaningMode.VACUUM,
            {"is_max_plus_mode_supported": False, "is_none_pure_clean_mop_with_max_plus": True},
            _FAN_BASE,
        ),
        # Without sub-tabs the other flag decides.
        (
            CleaningMode.VAC_AND_MOP,
            {
                "is_pure_clean_mop_supported": False,
                "is_max_plus_mode_supported": False,
                "is_none_pure_clean_mop_with_max_plus": True,
            },
            [*_FAN_BASE, VacuumModes.MAX_PLUS],
        ),
        (CleaningMode.VACUUM, {"is_pure_clean_mop_supported": False}, _FAN_BASE),
        (CleaningMode.VAC_AND_MOP, {"is_soft_clean_mode_supported": True}, [*_FAN_BASE, VacuumModes.GENTLE]),
    ],
)
def test_fan_speed_display_options_per_mode(
    mode: CleaningMode, overrides: dict[str, bool], expected: list[VacuumModes]
) -> None:
    assert _mode_display_options(CleaningSetting.FAN_SPEED, mode, overrides) == expected


@pytest.mark.parametrize(
    ("mode", "overrides", "expected"),
    [
        (CleaningMode.VAC_AND_MOP, {}, _ROUTES_SHORT),
        (CleaningMode.VACUUM, {}, _ROUTES_SHORT),
        (CleaningMode.MOP, {}, _ROUTES_FULL),
        # Efficiency devices show the full list without deep in every mode.
        (CleaningMode.VAC_AND_MOP, {"is_clean_efficiency_supported": True}, _ROUTES_EFFICIENCY),
        (CleaningMode.MOP, {"is_clean_efficiency_supported": True}, _ROUTES_EFFICIENCY),
        (CleaningMode.MOP, {"is_none_pure_clean_mop_with_max_plus": True}, _ROUTES_SHORT),
        (CleaningMode.VAC_AND_MOP, {"is_none_pure_clean_mop_with_max_plus": True}, _ROUTES_SHORT),
        # Without sub-tabs the full list is shown.
        (CleaningMode.VAC_AND_MOP, {"is_pure_clean_mop_supported": False}, _ROUTES_FULL),
        (CleaningMode.VAC_AND_MOP, {"is_clean_route_fast_mode_supported": False}, set()),
        (CleaningMode.VACUUM, {"is_clean_route_fast_mode_supported": False}, set()),
        (CleaningMode.MOP, {"is_clean_route_fast_mode_supported": False}, _ROUTES_FULL - {CleanRoutes.FAST}),
        (CleaningMode.VAC_AND_MOP, {"is_shake_mop_set_supported": False}, set()),
        (CleaningMode.VACUUM, {"is_shake_mop_set_supported": False}, set()),
        (CleaningMode.MOP, {"is_shake_mop_set_supported": False}, set()),
    ],
)
def test_mop_route_display_options_per_mode(
    mode: CleaningMode, overrides: dict[str, bool], expected: set[CleanRoutes]
) -> None:
    assert set(_mode_display_options(CleaningSetting.MOP_ROUTE, mode, overrides)) == expected


@pytest.mark.parametrize("mode", [CleaningMode.VAC_AND_MOP, CleaningMode.MOP])
@pytest.mark.parametrize("slide", [True, False])
def test_water_mode_display_options_without_off_when_pure_mop(mode: CleaningMode, slide: bool) -> None:
    options = _mode_display_options(CleaningSetting.WATER_MODE, mode, {"is_water_slide_mode_supported": slide})
    assert options
    assert WaterModes.OFF not in options


def test_water_mode_display_options_keep_off_without_sub_tabs() -> None:
    options = _mode_display_options(
        CleaningSetting.WATER_MODE, CleaningMode.VAC_AND_MOP, {"is_pure_clean_mop_supported": False}
    )
    assert WaterModes.OFF in options


@pytest.mark.parametrize(
    ("setting", "code", "mode", "overrides"),
    [
        (CleaningSetting.MOP_ROUTE, 301, CleaningMode.VAC_AND_MOP, {}),
        (CleaningSetting.MOP_ROUTE, 303, CleaningMode.VACUUM, {}),
        (CleaningSetting.FAN_SPEED, 108, CleaningMode.VAC_AND_MOP, {}),
        (CleaningSetting.FAN_SPEED, 108, CleaningMode.VACUUM, {"is_max_plus_mode_supported": False}),
        (CleaningSetting.WATER_MODE, 200, CleaningMode.VAC_AND_MOP, {}),
        (CleaningSetting.MOP_ROUTE, 300, CleaningMode.VAC_AND_MOP, {"is_shake_mop_set_supported": False}),
    ],
)
def test_get_setting_change_codes_refuses_values_outside_mode_list(
    setting: CleaningSetting, code: int, mode: CleaningMode, overrides: dict[str, bool]
) -> None:
    features = _features(**{**_SAROS_10R, **overrides})
    with pytest.raises(RoborockUnsupportedFeature):
        get_setting_change_codes(setting, code, mode, features, "us", fan_power=102, water_box_mode=235, mop_mode=300)


@pytest.mark.parametrize(
    ("setting", "code", "mode", "status", "expected", "overrides"),
    [
        (CleaningSetting.FAN_SPEED, 108, CleaningMode.VACUUM, (102, 200, 300), (108, 200, 300), {}),
        (CleaningSetting.MOP_ROUTE, 304, CleaningMode.VACUUM, (108, 200, 300), (108, 200, 304), {}),
        (CleaningSetting.MOP_ROUTE, 301, CleaningMode.MOP, (105, 235, 300), (105, 235, 301), {}),
        # A route or fan speed set in another tab by an older client is not carried along.
        (CleaningSetting.WATER_MODE, 240, CleaningMode.VAC_AND_MOP, (102, 235, 301), (102, 240, 300), {}),
        (CleaningSetting.WATER_MODE, 240, CleaningMode.VAC_AND_MOP, (108, 235, 300), (102, 240, 300), {}),
        (CleaningSetting.MOP_ROUTE, 304, CleaningMode.VAC_AND_MOP, (108, 235, 300), (102, 235, 304), {}),
        (CleaningSetting.WATER_MODE, 240, CleaningMode.MOP, (105, 235, 301), (105, 240, 301), {}),
        # The mop-only fan code left behind outside mopping only becomes balanced, like Max+.
        (CleaningSetting.MOP_ROUTE, 304, CleaningMode.VACUUM, (105, 200, 300), (102, 200, 304), {}),
        (CleaningSetting.WATER_MODE, 240, CleaningMode.VAC_AND_MOP, (105, 235, 300), (102, 240, 300), {}),
        # Gentle is on the fan list of soft-clean models, so code 105 stays there.
        (
            CleaningSetting.WATER_MODE,
            240,
            CleaningMode.VAC_AND_MOP,
            (105, 235, 300),
            (105, 240, 300),
            {"is_soft_clean_mode_supported": True},
        ),
        # A leftover route is replaced even when the mode has no adjustable route.
        (
            CleaningSetting.WATER_MODE,
            240,
            CleaningMode.VAC_AND_MOP,
            (102, 235, 301),
            (102, 240, 300),
            {"is_clean_route_fast_mode_supported": False},
        ),
        # Fast is on the tab's short list and stays.
        (
            CleaningSetting.WATER_MODE,
            240,
            CleaningMode.VAC_AND_MOP,
            (102, 235, 304),
            (102, 240, 304),
            {"is_clean_route_fast_mode_supported": False},
        ),
    ],
)
def test_get_setting_change_codes_replaces_values_outside_mode_list(
    setting: CleaningSetting,
    code: int,
    mode: CleaningMode,
    status: tuple[int, int, int],
    expected: tuple[int, int, int],
    overrides: dict[str, bool],
) -> None:
    features = _features(**{**_SAROS_10R, **overrides})
    assert (
        get_setting_change_codes(
            setting, code, mode, features, "us", fan_power=status[0], water_box_mode=status[1], mop_mode=status[2]
        )
        == expected
    )


@pytest.mark.parametrize("mode", [CleaningMode.SMART_MODE, CleaningMode.CUSTOM])
@pytest.mark.parametrize("shake", [True, False])
def test_get_display_options_route_special_values_need_shake(mode: CleaningMode, shake: bool) -> None:
    features = _features(is_shake_mop_set_supported=shake)
    options = get_clean_routes(features, "us")
    assert options
    shown = get_display_options(CleaningSetting.MOP_ROUTE, mode, features, options)
    assert bool(shown) is shake


def test_water_mode_display_options_include_off_when_turning_water_on_without_mode_tabs() -> None:
    options = _mode_display_options(
        CleaningSetting.WATER_MODE, CleaningMode.VACUUM, {"is_pure_clean_mop_supported": False}
    )
    assert WaterModes.OFF in options
    assert len(options) > 1


def test_get_setting_change_codes_turns_water_on_without_mode_tabs() -> None:
    features = _features(**{**_SAROS_10R, "is_pure_clean_mop_supported": False})
    assert get_setting_change_codes(
        CleaningSetting.WATER_MODE,
        240,
        CleaningMode.VACUUM,
        features,
        "us",
        fan_power=102,
        water_box_mode=200,
        mop_mode=300,
    ) == (102, 240, 300)


def test_fan_speed_display_options_keep_full_list_without_a_mop() -> None:
    """Devices without a mop have no mode tabs at all and keep every fan speed the model lists, Max+ included."""
    features = _features(is_support_water_mode=False, is_max_plus_mode_supported=True)
    options = get_clean_modes(features)
    assert VacuumModes.MAX_PLUS in options
    assert get_display_options(CleaningSetting.FAN_SPEED, None, features, options) == options


_FAN = CleaningSetting.FAN_SPEED
_WATER = CleaningSetting.WATER_MODE
_ROUTE = CleaningSetting.MOP_ROUTE


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        # Vacuum-only: no mop module, so only the fan speed.
        ({"is_support_water_mode": False}, frozenset({_FAN})),
        # Saros-like: shake module with fast route, mop-only tab and water slide.
        (
            {"is_pure_clean_mop_supported": True, "is_water_slide_mode_supported": True},
            frozenset({_FAN, _WATER, _ROUTE}),
        ),
        # Shake module without fast route but with a mop-only tab: the route exists in mop mode.
        (
            {"is_pure_clean_mop_supported": True, "is_clean_route_fast_mode_supported": False},
            frozenset({_FAN, _WATER, _ROUTE}),
        ),
        # Shake module without mop-only tab and without fast route: the route is never adjustable.
        (
            {"is_pure_clean_mop_supported": False, "is_clean_route_fast_mode_supported": False},
            frozenset({_FAN, _WATER}),
        ),
        # Spin or roller mop: route setting without the shake module.
        ({"is_shake_mop_set_supported": False, "is_pure_clean_mop_supported": True}, frozenset({_FAN, _WATER})),
        ({"is_shake_mop_set_supported": False}, frozenset({_FAN, _WATER})),
        # Clean efficiency only changes the route values.
        (
            {"is_pure_clean_mop_supported": True, "is_clean_efficiency_supported": True},
            frozenset({_FAN, _WATER, _ROUTE}),
        ),
        # Max+ without a mop-only tab only changes the route values.
        ({"is_none_pure_clean_mop_with_max_plus": True}, frozenset({_FAN, _WATER, _ROUTE})),
    ],
)
def test_get_supported_settings(overrides: dict[str, bool], expected: frozenset[CleaningSetting]) -> None:
    assert get_supported_settings(_features(**overrides)) == expected


_GRID_FLAGS = (
    "is_shake_mop_set_supported",
    "is_clean_route_fast_mode_supported",
    "is_pure_clean_mop_supported",
    "is_support_water_mode",
    "is_clean_route_setting_supported",
    "is_clean_efficiency_supported",
    "is_none_pure_clean_mop_with_max_plus",
)


@pytest.mark.parametrize("values", list(itertools.product((False, True), repeat=len(_GRID_FLAGS))))
def test_supported_settings_match_adjustable_settings(values: tuple[bool, ...]) -> None:
    """A setting is supported exactly when it can be adjusted in at least one reachable cleaning mode."""
    features = _features(**dict(zip(_GRID_FLAGS, values, strict=True)))
    reachable: list[CleaningMode | None] = [
        mode
        for mode in get_cleaning_mode_options(features)
        if mode not in (CleaningMode.SMART_MODE, CleaningMode.CUSTOM)
    ] or [None]
    adjustable_somewhere: set[CleaningSetting] = set()
    for mode in reachable:
        adjustable_somewhere |= get_adjustable_settings(mode, features)
    assert get_supported_settings(features) == adjustable_somewhere


@pytest.mark.parametrize(
    ("fan", "water", "route", "expected"),
    [
        # Custom wins over SmartPlan when both are reported.
        (106, 202, 300, CleaningMode.CUSTOM),
        (102, 204, 300, CleaningMode.CUSTOM),
        (102, 202, 302, CleaningMode.CUSTOM),
        (106, 209, 300, CleaningMode.CUSTOM),
        (110, 202, 300, CleaningMode.SMART_MODE),
        (102, 209, 300, CleaningMode.SMART_MODE),
        (102, 202, 306, CleaningMode.SMART_MODE),
        # Regular codes, including a water slide position and the fast route, are not special.
        (102, 202, 300, None),
        (102, 235, 304, None),
    ],
)
def test_get_reported_special_mode(fan: int, water: int, route: int, expected: CleaningMode | None) -> None:
    features = _features(is_pure_clean_mop_supported=True)
    assert get_reported_special_mode(fan, water, route, features) == expected


@pytest.mark.parametrize(
    ("fan", "water", "route", "expected"),
    [
        # Without a mop only the fan power is read, so water and route codes do not count.
        (102, 204, 300, None),
        (102, 209, 306, None),
        (110, 204, 302, CleaningMode.SMART_MODE),
        (106, 209, 306, CleaningMode.CUSTOM),
    ],
)
def test_get_reported_special_mode_ignores_water_and_route_without_mop(
    fan: int, water: int, route: int, expected: CleaningMode | None
) -> None:
    features = _features(is_support_water_mode=False)
    assert get_reported_special_mode(fan, water, route, features) == expected

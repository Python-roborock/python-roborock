"""Tests for the pure V1 cleaning mode helpers."""

import pytest

from roborock.data.v1.v1_clean_modes import (
    CleaningMode,
    CleaningSetting,
    CleanRoutes,
    VacuumModes,
    WaterModes,
    get_adjustable_settings,
    get_clean_modes,
    get_clean_routes,
    get_display_options,
    get_water_modes,
)
from roborock.device_features import DeviceFeatures


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


def test_fan_speed_display_options_keep_full_list_without_a_mop() -> None:
    """Devices without a mop have no mode tabs at all and keep every fan speed the model lists, Max+ included."""
    features = _features(is_support_water_mode=False, is_max_plus_mode_supported=True)
    options = get_clean_modes(features)
    assert VacuumModes.MAX_PLUS in options
    assert get_display_options(CleaningSetting.FAN_SPEED, None, features, options) == options

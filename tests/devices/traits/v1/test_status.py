"""Tests for the StatusTrait class."""

import asyncio
import warnings
from typing import cast
from unittest.mock import AsyncMock, call

import pytest

from roborock import (
    CleaningMode,
    CleaningSetting,
    CleanRoutes,
    VacuumModes,
    WaterModes,
    get_cleaning_mode_parameters,
    get_current_cleaning_mode,
    resolve_cleaning_mode,
)
from roborock.data import SHORT_MODEL_TO_ENUM, HomeDataDevice, RoborockProductNickname
from roborock.data.v1 import (
    RoborockChargeStatus,
    RoborockDockErrorCode,
    RoborockDockState,
    RoborockDockTypeCode,
    RoborockErrorCode,
    RoborockStateCode,
)
from roborock.device_features import DeviceFeatures
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockException, RoborockParsingException, RoborockUnsupportedFeature
from roborock.roborock_message import RoborockDataProtocol
from roborock.roborock_typing import RoborockCommand
from tests import mock_data
from tests.mock_data import STATUS


@pytest.fixture
def status_trait(device: RoborockDevice) -> StatusTrait:
    """Create a StatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.status


def _create_cleaning_mode_status_trait(**feature_overrides: bool) -> StatusTrait:
    """Create a status trait with mop-capable V1 features for cleaning mode tests."""
    short_model = mock_data.A27_PRODUCT_DATA["model"].split(".")[-1]
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=SHORT_MODEL_TO_ENUM[short_model],
    )
    features.is_support_water_mode = True
    features.is_pure_clean_mop_supported = True
    features.is_customized_clean_supported = True
    features.is_clean_route_setting_supported = True
    features.is_shake_mop_set_supported = True
    features.is_clean_route_fast_mode_supported = True
    for feature_name, value in feature_overrides.items():
        if not hasattr(features, feature_name):
            raise AttributeError(f"Unknown DeviceFeatures override: {feature_name}")
        setattr(features, feature_name, value)
    return StatusTrait(cast(DeviceFeaturesTrait, features), region="us")


async def test_refresh_status(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test successfully refreshing status."""
    mock_rpc_channel.send_command.return_value = [STATUS]

    await status_trait.refresh()

    assert status_trait.battery == 100
    assert status_trait.state == RoborockStateCode.charging
    assert status_trait.fan_power == 102
    assert status_trait.fan_speed_name == "balanced"
    assert status_trait.fan_speed_name in status_trait.fan_speed_options
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_STATUS)


async def test_refresh_status_dict_response(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test refreshing status when response is a dict instead of list."""
    mock_rpc_channel.send_command.return_value = STATUS

    await status_trait.refresh()

    assert status_trait.battery == 100
    assert status_trait.state == RoborockStateCode.charging
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_STATUS)


@pytest.mark.parametrize("device_info", [HomeDataDevice.from_dict(mock_data.P30_PRO_DEVICE_DATA)])
@pytest.mark.parametrize(
    ("water_box_mode", "expected_name"),
    [(210, "smart_water"), (230, "gentle")],
)
async def test_refresh_status_p30_pro(
    device_info: HomeDataDevice,
    discover_features_fixture: None,
    status_trait: StatusTrait,
    mock_rpc_channel: AsyncMock,
    water_box_mode: int,
    expected_name: str,
) -> None:
    """Test refreshing P30 Pro status with smart water or a manual slider value."""
    mock_rpc_channel.send_command.return_value = [
        {**STATUS, "fan_power": 103, "water_box_mode": water_box_mode, "mop_mode": 300, "dock_type": 49}
    ]

    await status_trait.refresh()

    assert status_trait.fan_speed_name == "turbo"
    assert status_trait.water_box_mode == water_box_mode
    assert status_trait.water_mode_name == expected_name
    assert status_trait.mop_route_name == "standard"
    assert status_trait.current_cleaning_mode == CleaningMode.VAC_AND_MOP
    assert status_trait.dock_type == RoborockDockTypeCode.type_49_dock
    mock_rpc_channel.send_command.assert_awaited_once_with(RoborockCommand.GET_STATUS)


@pytest.mark.parametrize(
    "device_info",
    [mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_qrevo_2_pro.json"][0]],
)
@pytest.mark.parametrize(
    ("fan_power", "water_box_mode", "mop_mode", "expected_water_mode", "expected_mop_route"),
    [
        (102, 235, 300, "medium", "standard"),
        (104, 243, 303, "high", "deep_plus"),
    ],
)
async def test_refresh_status_qrevo_2_pro(
    device_info: HomeDataDevice,
    discover_features_fixture: None,
    status_trait: StatusTrait,
    mock_rpc_channel: AsyncMock,
    fan_power: int,
    water_box_mode: int,
    mop_mode: int,
    expected_water_mode: str,
    expected_mop_route: str,
) -> None:
    """Test captured Qrevo 2 Pro water levels and mop routes after discovery."""
    mock_rpc_channel.send_command.return_value = [
        {
            **STATUS,
            "fan_power": fan_power,
            "water_box_mode": water_box_mode,
            "mop_mode": mop_mode,
            "dock_type": RoborockDockTypeCode.f1_dock,
        }
    ]

    await status_trait.refresh()

    assert status_trait.water_mode_name == expected_water_mode
    assert status_trait.mop_route_name == expected_mop_route
    mock_rpc_channel.send_command.assert_awaited_once_with(RoborockCommand.GET_STATUS)


async def test_refresh_status_propagates_exception(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from RPC channel are propagated."""
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    with pytest.raises(RoborockException, match="Communication error"):
        await status_trait.refresh()


async def test_resolve_error_explicit_code(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test resolving an explicitly given error code."""
    mock_rpc_channel.send_command.side_effect = ["ok", STATUS]

    await status_trait.resolve_error(38)

    assert mock_rpc_channel.send_command.mock_calls == [
        call(RoborockCommand.RESOLVE_ERROR, params={"error_code": 38}),
        call(RoborockCommand.GET_STATUS),
    ]
    assert status_trait.dock_error_status == RoborockDockErrorCode.ok


async def test_resolve_error_defaults_to_dock_error(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that the current dock error is resolved when no code is given."""
    mock_rpc_channel.send_command.side_effect = [
        {**STATUS, "dock_error_status": RoborockDockErrorCode.water_empty.value, "error_code": 38},
        "ok",
        STATUS,
    ]
    await status_trait.refresh()
    assert status_trait.dock_error_status == RoborockDockErrorCode.water_empty

    await status_trait.resolve_error()

    assert mock_rpc_channel.send_command.mock_calls[1:] == [
        call(RoborockCommand.RESOLVE_ERROR, params={"error_code": 38}),
        call(RoborockCommand.GET_STATUS),
    ]
    assert status_trait.dock_error_status == RoborockDockErrorCode.ok


async def test_resolve_error_defaults_to_robot_error(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that the robot error is resolved when there is no dock error."""
    mock_rpc_channel.send_command.side_effect = [
        {**STATUS, "error_code": RoborockErrorCode.clear_water_box_exception.value},
        "ok",
        STATUS,
    ]
    await status_trait.refresh()

    await status_trait.resolve_error()

    assert mock_rpc_channel.send_command.mock_calls[1:] == [
        call(RoborockCommand.RESOLVE_ERROR, params={"error_code": RoborockErrorCode.clear_water_box_exception.value}),
        call(RoborockCommand.GET_STATUS),
    ]


async def test_resolve_error_no_error(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that nothing is sent when there is no error to resolve."""
    mock_rpc_channel.send_command.return_value = STATUS
    await status_trait.refresh()

    await status_trait.resolve_error()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_STATUS)


async def test_resolve_error_propagates_exception(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from the RPC channel are propagated."""
    mock_rpc_channel.send_command.side_effect = RoborockException("invalid params")

    with pytest.raises(RoborockException, match="invalid params"):
        await status_trait.resolve_error(38)


async def test_refresh_status_invalid_format(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that invalid response format raises RoborockParsingException."""
    mock_rpc_channel.send_command.return_value = "invalid"

    with pytest.raises(RoborockParsingException, match="Unexpected StatusV2 response format"):
        await status_trait.refresh()


def test_none_values(status_trait: StatusTrait) -> None:
    """Test that none values are returned correctly."""
    status_trait.fan_power = None
    status_trait.water_box_mode = None
    status_trait.mop_mode = None
    assert status_trait.fan_speed_name is None
    assert status_trait.water_mode_name is None
    assert status_trait.mop_route_name is None


@pytest.mark.parametrize(
    (
        "is_supported_valley_electricity",
        "charge_status",
        "battery",
        "expected_dock_state",
        "expected_is_battery_charging",
    ),
    [
        (False, RoborockChargeStatus.charge_waiting, 50, RoborockDockState.charging, True),
        (False, None, 50, RoborockDockState.charging, True),
        (True, RoborockChargeStatus.charge_waiting, 50, RoborockDockState.off_peak_waiting, False),
        (True, RoborockChargeStatus.charging, 50, RoborockDockState.charging, True),
        (True, RoborockChargeStatus.charging, 100, RoborockDockState.full, False),
    ],
)
def test_feature_aware_dock_and_charging_state(
    is_supported_valley_electricity: bool,
    charge_status: RoborockChargeStatus | None,
    battery: int,
    expected_dock_state: RoborockDockState,
    expected_is_battery_charging: bool,
) -> None:
    """Test dock and charging state against the V1 app's feature-gated logic."""
    status_trait = _create_cleaning_mode_status_trait(is_supported_valley_electricity=is_supported_valley_electricity)
    status_trait.state = RoborockStateCode.charging
    status_trait.charge_status = charge_status
    status_trait.battery = battery

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert status_trait.dock_state == expected_dock_state
        assert status_trait.is_battery_charging is expected_is_battery_charging


@pytest.mark.parametrize(
    ("fan", "water", "mop", "expected"),
    [
        (110, 209, 306, (False, False, False)),
        (106, 204, 302, (False, False, False)),
        (102, 200, 300, (True, False, True)),
        (102, 202, 300, (True, True, True)),
        (105, 202, 300, (False, True, True)),
    ],
)
def test_adjustable_settings_per_mode(fan: int, water: int, mop: int, expected: tuple[bool, bool, bool]) -> None:
    trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True, is_shake_mop_set_supported=True)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = fan, water, mop
    assert (trait.is_fan_speed_adjustable, trait.is_water_mode_adjustable, trait.is_mop_route_adjustable) == expected


@pytest.mark.parametrize(
    ("route_flag", "shake", "expected_options", "expected_adjustable"),
    [
        (True, True, True, True),
        (False, True, False, True),
        # The route is only offered with the shake module, even when the model lists routes.
        (True, False, False, False),
        (False, False, False, False),
    ],
)
def test_mop_route_needs_shake_module(
    route_flag: bool, shake: bool, expected_options: bool, expected_adjustable: bool
) -> None:
    trait = _create_cleaning_mode_status_trait(
        is_shake_mop_set_supported=shake, is_clean_route_setting_supported=route_flag
    )
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 105, 202, 300  # MOP
    assert trait.is_mop_route_adjustable is expected_adjustable
    assert bool(trait.mop_route_options) is expected_options
    assert bool(trait.mop_route_display_options) is (expected_adjustable and expected_options)


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        ((110, 209, 306), ([VacuumModes.SMART_MODE], [WaterModes.SMART_MODE], [CleanRoutes.SMART_MODE])),
        ((106, 204, 302), ([VacuumModes.CUSTOMIZED], [WaterModes.CUSTOMIZED], [CleanRoutes.CUSTOMIZED])),
    ],
)
def test_display_options_locked_in_special_modes(
    codes: tuple[int, int, int],
    expected: tuple[list[VacuumModes], list[WaterModes], list[CleanRoutes]],
) -> None:
    trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True, is_custom_mode_supported=True)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes
    assert (
        trait.fan_speed_display_options,
        trait.water_mode_display_options,
        trait.mop_route_display_options,
    ) == expected
    # The current value's name is among the options to show (HA SelectEntity.state).
    assert trait.water_mode_name in {m.display_name for m in trait.water_mode_display_options}


def test_display_options_regular_and_hidden() -> None:
    trait = _create_cleaning_mode_status_trait()
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 200, 300  # VACUUM
    assert trait.fan_speed_display_options == trait.fan_speed_options
    assert trait.water_mode_display_options == []


@pytest.mark.parametrize("codes", [(110, 209, 306), (106, 204, 302)])
def test_mop_route_display_options_empty_without_route_setting(codes: tuple[int, int, int]) -> None:
    """A device without a route setting shows no routes, even in SmartPlan or custom mode."""
    trait = _create_cleaning_mode_status_trait(
        is_smart_clean_mode_set_supported=True,
        is_custom_mode_supported=True,
        is_clean_route_setting_supported=False,
    )
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes
    assert trait.mop_route_display_options == []
    assert trait.water_mode_display_options != []


def test_vacuum_only_device_fan_adjustable() -> None:
    trait = _create_cleaning_mode_status_trait(is_support_water_mode=False)
    trait.fan_power = 102
    assert (trait.is_fan_speed_adjustable, trait.is_water_mode_adjustable) == (True, False)


def test_options(status_trait: StatusTrait) -> None:
    """Test that fan_speed_options returns a list of options."""
    features = status_trait._device_features_trait
    features.is_support_water_mode = True
    features.is_shake_mop_set_supported = True
    features.is_pure_clean_mop_supported = True
    features.is_clean_route_setting_supported = True
    assert isinstance(status_trait.fan_speed_options, list)
    assert len(status_trait.fan_speed_options) > 0
    assert isinstance(status_trait.water_mode_options, list)
    assert len(status_trait.water_mode_options) > 0
    assert isinstance(status_trait.mop_route_options, list)
    assert len(status_trait.mop_route_options) > 0


def test_s6_maxv_has_no_mop_route_options() -> None:
    """Test S6 MaxV does not expose the unsupported mop-route selector."""
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=10738169343,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=SHORT_MODEL_TO_ENUM["a10"],
    )
    status_trait = StatusTrait(cast(DeviceFeaturesTrait, features), region="us")

    assert not features.is_shake_mop_set_supported
    assert status_trait.mop_route_options == []
    assert status_trait.mop_route_mapping == {}
    assert get_cleaning_mode_parameters(CleaningMode.VAC_AND_MOP, features) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.STANDARD.code,
        }
    ]


def test_s7_has_mop_route_options() -> None:
    """Test S7 exposes its supported mop routes."""
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=636084721975295,
        new_feature_info_str="0000000000002000",
        feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125],
        product_nickname=SHORT_MODEL_TO_ENUM["a15"],
    )
    status_trait = StatusTrait(cast(DeviceFeaturesTrait, features), region="us")

    assert features.is_shake_mop_set_supported
    assert CleanRoutes.STANDARD in status_trait.mop_route_options
    assert CleanRoutes.DEEP in status_trait.mop_route_options
    assert get_cleaning_mode_parameters(CleaningMode.VAC_AND_MOP, features) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.STANDARD.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]


def test_spin_mop_without_runtime_shake_has_mop_route_options() -> None:
    """Test spin-mop models retain routes without the runtime shake bit."""
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="42BA8D587EDAFFFE",
        feature_info=[],
        product_nickname=SHORT_MODEL_TO_ENUM["a123"],
    )
    status_trait = StatusTrait(cast(DeviceFeaturesTrait, features), region="us")

    assert not features.is_shake_mop_set_supported
    assert features.is_clean_route_setting_supported
    # Without the shake module the route is never offered, so no route list is reported.
    assert status_trait.mop_route_options == []
    assert status_trait.mop_route_mapping == {}
    assert CleaningSetting.MOP_ROUTE not in status_trait.supported_cleaning_settings
    assert get_cleaning_mode_parameters(CleaningMode.VAC_AND_MOP, features)[0]["mop_mode"] == 300


def test_clean_efficiency_device_omits_deep_route() -> None:
    """Test Saros 20-style clean-efficiency devices do not expose route 301."""
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=4499197267967999,
        new_feature_info_str="0000000000099518CCFF7EFDA8E93EDDDBFF8F7F7EFEFFFF",
        feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125],
        product_nickname=RoborockProductNickname.PEARLPLUS,
    )
    status_trait = StatusTrait(cast(DeviceFeaturesTrait, features), region="us")

    assert features.is_clean_efficiency_supported
    assert features.is_clean_route_setting_supported
    assert CleanRoutes.STANDARD in status_trait.mop_route_options
    assert CleanRoutes.DEEP not in status_trait.mop_route_options
    assert CleanRoutes.DEEP_PLUS in status_trait.mop_route_options
    assert CleanRoutes.FAST in status_trait.mop_route_options


@pytest.mark.parametrize(
    ("is_corner_clean_mode_supported", "is_clean_route_deep_slow_plus_supported", "region", "expected_code"),
    [
        (False, False, "us", 303),
        (False, True, "us", 303),
        (True, True, "us", 303),
        (False, False, "cn", 303),
        (True, True, "cn", 303),
        (False, True, "cn", 305),
    ],
)
def test_deep_plus_route_matches_rr_api(
    is_corner_clean_mode_supported: bool,
    is_clean_route_deep_slow_plus_supported: bool,
    region: str,
    expected_code: int,
) -> None:
    """Test route 305 is limited to its RR_API China-only feature combination."""
    status_trait = _create_cleaning_mode_status_trait(
        is_careful_slow_mop_supported=True,
        is_corner_clean_mode_supported=is_corner_clean_mode_supported,
        is_clean_route_deep_slow_plus_supported=is_clean_route_deep_slow_plus_supported,
    )
    status_trait._region = region

    route_codes = [route.code for route in status_trait.mop_route_options]
    assert expected_code in route_codes
    assert ({303, 305} - {expected_code}).isdisjoint(route_codes)
    assert status_trait.mop_route_mapping[expected_code] == "deep_plus"


def test_cleaning_mode_options() -> None:
    """Test the high-level cleaning mode options for the device."""
    status_trait = _create_cleaning_mode_status_trait()
    assert status_trait.cleaning_mode_options == [
        CleaningMode.VACUUM,
        CleaningMode.VAC_AND_MOP,
        CleaningMode.MOP,
        CleaningMode.CUSTOM,
    ]


@pytest.mark.parametrize(
    ("fan_power", "water_box_mode", "mop_mode", "expected_mode"),
    [
        (
            VacuumModes.BALANCED.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningMode.VAC_AND_MOP,
        ),
        (
            VacuumModes.BALANCED.code,
            WaterModes.OFF.code,
            CleanRoutes.STANDARD.code,
            CleaningMode.VACUUM,
        ),
        (
            VacuumModes.OFF.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningMode.MOP,
        ),
        (
            VacuumModes.CUSTOMIZED.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningMode.CUSTOM,
        ),
        (
            VacuumModes.BALANCED.code,
            WaterModes.SMART_MODE.code,
            CleanRoutes.STANDARD.code,
            CleaningMode.SMART_MODE,
        ),
    ],
)
def test_current_cleaning_mode(
    fan_power: int,
    water_box_mode: int,
    mop_mode: int,
    expected_mode: CleaningMode,
) -> None:
    """Test the current high-level cleaning mode classification."""
    status_trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)
    status_trait.fan_power = fan_power
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = mop_mode

    assert status_trait.current_cleaning_mode == expected_mode
    assert status_trait.current_cleaning_mode_name == expected_mode.value


def test_current_cleaning_mode_with_main_brush_lift() -> None:
    """Test mop-only classification on a device with main-brush lift."""
    status_trait = _create_cleaning_mode_status_trait(
        is_support_main_brush_up_down_supported=True,
        is_water_slide_mode_supported=True,
    )
    status_trait.fan_power = VacuumModes.OFF.code
    status_trait.water_box_mode = 235
    status_trait.mop_mode = CleanRoutes.STANDARD.code

    assert status_trait.current_cleaning_mode == CleaningMode.MOP


def test_current_cleaning_mode_accepts_enums() -> None:
    """Test direct enum inputs are resolved before classification."""
    status_trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)

    assert (
        get_current_cleaning_mode(
            clean_mode=VacuumModes.BALANCED,
            water_mode=WaterModes.SMART_MODE,
            mop_mode=CleanRoutes.STANDARD,
            features=status_trait._device_features_trait,
        )
        == CleaningMode.SMART_MODE
    )


def test_current_cleaning_mode_none() -> None:
    """Test that incomplete status values do not classify a cleaning mode."""
    status_trait = _create_cleaning_mode_status_trait()
    status_trait.fan_power = None
    assert status_trait.current_cleaning_mode is None
    assert status_trait.current_cleaning_mode_name is None


def test_current_cleaning_mode_without_mop_route_status() -> None:
    """Test older V1 devices can classify cleaning mode without mop route status."""
    status_trait = _create_cleaning_mode_status_trait(
        is_clean_route_setting_supported=False,
        is_customized_clean_supported=False,
    )
    status_trait.fan_power = VacuumModes.BALANCED.code
    status_trait.water_box_mode = WaterModes.OFF.code
    status_trait.mop_mode = None

    assert status_trait.current_cleaning_mode == CleaningMode.VACUUM


def test_get_cleaning_mode_parameters() -> None:
    """Test payload generation for supported high-level cleaning modes."""
    status_trait = _create_cleaning_mode_status_trait()
    assert get_cleaning_mode_parameters(CleaningMode.VACUUM, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert get_cleaning_mode_parameters(resolve_cleaning_mode("custom"), status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.CUSTOMIZED.code,
            "water_box_mode": WaterModes.CUSTOMIZED.code,
            "mop_mode": CleanRoutes.CUSTOMIZED.code,
        }
    ]


def test_get_cleaning_mode_parameters_unsupported() -> None:
    """Test unsupported cleaning modes raise a clear error."""
    status_trait = _create_cleaning_mode_status_trait()
    with pytest.raises(RoborockUnsupportedFeature, match="not supported"):
        get_cleaning_mode_parameters(CleaningMode.SMART_MODE, status_trait._device_features_trait)


def test_get_cleaning_mode_parameters_invalid_name() -> None:
    """Test invalid cleaning mode names raise RoborockUnsupportedFeature."""
    with pytest.raises(RoborockUnsupportedFeature, match="not supported"):
        resolve_cleaning_mode("invalid_mode")


async def test_set_cleaning_mode(
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test setting the high-level cleaning mode."""
    status_trait = _create_cleaning_mode_status_trait()
    status_trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    await status_trait.set_cleaning_mode(CleaningMode.CUSTOM)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE,
        params=[
            {
                "fan_power": VacuumModes.CUSTOMIZED.code,
                "water_box_mode": WaterModes.CUSTOMIZED.code,
                "mop_mode": CleanRoutes.CUSTOMIZED.code,
            }
        ],
    )


def test_cleaning_mode_options_with_smart_mode() -> None:
    """Test SmartPlan support is reflected in the available options."""
    status_trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)

    assert status_trait.cleaning_mode_options == [
        CleaningMode.VACUUM,
        CleaningMode.VAC_AND_MOP,
        CleaningMode.MOP,
        CleaningMode.CUSTOM,
        CleaningMode.SMART_MODE,
    ]


def test_get_cleaning_mode_parameters_qrevo_edge_2() -> None:
    """Test the app-compatible Qrevo Edge 2 mop-only payload."""
    status_trait = _create_cleaning_mode_status_trait(
        is_support_main_brush_up_down_supported=True,
        is_water_slide_mode_supported=True,
    )

    assert get_cleaning_mode_parameters(CleaningMode.MOP, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.OFF.code,
            "water_box_mode": 235,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert 105 not in {mode.code for mode in status_trait.fan_speed_options}
    assert VacuumModes.OFF_RAISE_MAIN_BRUSH not in status_trait.fan_speed_options


def test_get_cleaning_mode_parameters_without_clean_route_setting() -> None:
    """Test older V1 devices use the 2-field clean motor payload."""
    status_trait = _create_cleaning_mode_status_trait(
        is_clean_route_setting_supported=False,
        is_customized_clean_supported=False,
    )

    assert get_cleaning_mode_parameters(CleaningMode.VACUUM, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
        }
    ]
    assert get_cleaning_mode_parameters(CleaningMode.VAC_AND_MOP, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.STANDARD.code,
        }
    ]
    assert get_cleaning_mode_parameters(CleaningMode.MOP, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.OFF.code,
            "water_box_mode": WaterModes.STANDARD.code,
        }
    ]


def test_get_cleaning_mode_parameters_water_slide_device() -> None:
    """Water-slide devices should use a slide-compatible water code, not 202."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)

    assert get_cleaning_mode_parameters(CleaningMode.VACUUM, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert get_cleaning_mode_parameters(CleaningMode.VAC_AND_MOP, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": 235,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert get_cleaning_mode_parameters(CleaningMode.MOP, status_trait._device_features_trait) == [
        {
            "fan_power": VacuumModes.OFF.code,
            "water_box_mode": 235,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]


@pytest.mark.parametrize("water_box_mode", range(221, 251))
@pytest.mark.parametrize(
    ("fan_power", "expected_mode"),
    [(102, CleaningMode.VAC_AND_MOP), (104, CleaningMode.VAC_AND_MOP), (105, CleaningMode.MOP)],
)
def test_current_cleaning_mode_water_slide_codes(
    water_box_mode: int, fan_power: int, expected_mode: CleaningMode
) -> None:
    """Classify every raw slider position without changing the reported water code."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    status_trait.fan_power = fan_power
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = 303

    assert status_trait.current_cleaning_mode == expected_mode
    assert status_trait.current_cleaning_mode_name == expected_mode.value
    assert status_trait.water_box_mode == water_box_mode


@pytest.mark.parametrize(
    ("water_box_mode", "expected_mode"),
    [
        (200, CleaningMode.VACUUM),
        (204, CleaningMode.CUSTOM),
        (209, CleaningMode.SMART_MODE),
        (220, None),
        (251, None),
        (999, None),
        (None, None),
    ],
)
def test_current_cleaning_mode_water_slide_legacy_codes(
    water_box_mode: int | None, expected_mode: CleaningMode | None
) -> None:
    """Keep legacy and unknown status decoding on water-slide devices."""
    status_trait = _create_cleaning_mode_status_trait(
        is_water_slide_mode_supported=True, is_smart_clean_mode_set_supported=True
    )
    status_trait.fan_power = 102
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = 300

    assert status_trait.current_cleaning_mode == expected_mode
    assert status_trait.current_cleaning_mode_name == (expected_mode.value if expected_mode is not None else None)
    assert status_trait.water_box_mode == water_box_mode


@pytest.mark.parametrize("water_box_mode", [222, 223, 248])
def test_current_cleaning_mode_without_water_slide_support(water_box_mode: int) -> None:
    """Do not interpret slider positions without the water-slide capability."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=False)
    status_trait.fan_power = 102
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = 300

    assert status_trait.current_cleaning_mode is None
    assert status_trait.current_cleaning_mode_name is None
    assert status_trait.water_box_mode == water_box_mode


@pytest.mark.parametrize("is_water_slide_mode_supported", [False, True])
@pytest.mark.parametrize(
    ("water_box_mode", "expected_mode"),
    [
        (200, CleaningMode.VACUUM),
        (201, CleaningMode.VAC_AND_MOP),
        (202, CleaningMode.VAC_AND_MOP),
        (203, CleaningMode.VAC_AND_MOP),
        (None, None),
        (999, None),
    ],
)
def test_current_cleaning_mode_water_code_fallback(
    is_water_slide_mode_supported: bool, water_box_mode: int | None, expected_mode: CleaningMode | None
) -> None:
    """Preserve legacy water status codes and unknown-code fallback for both device types."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=is_water_slide_mode_supported)
    status_trait.fan_power = 102
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = 300

    assert status_trait.current_cleaning_mode == expected_mode


@pytest.mark.parametrize(
    ("code", "expected_mode", "display_name"),
    [
        (225, WaterModes.PURE_WATER_FLOW_SMALL, "low"),
        (235, WaterModes.PURE_WATER_FLOW_MIDDLE, "medium"),
        (245, WaterModes.PURE_WATER_SUPER_BEGIN, "high"),
        (250, WaterModes.PURE_WATER_FLOW_END, "extreme"),
    ],
)
def test_water_slide_modes_keep_their_own_codes(code: int, expected_mode: WaterModes, display_name: str) -> None:
    """Water slide modes are distinct from the legacy modes that share their names."""
    assert WaterModes.from_code_optional(code) is expected_mode
    assert expected_mode.code == code
    assert expected_mode.display_name == display_name


@pytest.mark.parametrize("water_mode", [WaterModes.MEDIUM, WaterModes.PURE_WATER_FLOW_MIDDLE])
def test_current_cleaning_mode_water_slide_accepts_enums(water_mode: WaterModes) -> None:
    """Enum inputs remain valid even when they alias a legacy water mode."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    assert (
        get_current_cleaning_mode(102, water_mode, 303, status_trait._device_features_trait) == CleaningMode.VAC_AND_MOP
    )


@pytest.mark.parametrize("is_clean_route_setting_supported", [False, True])
@pytest.mark.parametrize(
    ("cleaning_mode", "fan_power", "water_box_mode"),
    [("vacuum", 102, 200), ("vac_and_mop", 102, 235), ("mop", 105, 235)],
)
async def test_set_cleaning_mode_water_slide_wire_payload(
    mock_rpc_channel: AsyncMock,
    is_clean_route_setting_supported: bool,
    cleaning_mode: str,
    fan_power: int,
    water_box_mode: int,
) -> None:
    """Assert the public trait emits valid slide RPC integers, with optional mop route."""
    status_trait = _create_cleaning_mode_status_trait(
        is_water_slide_mode_supported=True,
        is_clean_route_setting_supported=is_clean_route_setting_supported,
    )
    status_trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]

    await status_trait.set_cleaning_mode(cleaning_mode)

    expected = {"fan_power": fan_power, "water_box_mode": water_box_mode}
    if is_clean_route_setting_supported:
        expected["mop_mode"] = 300
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[expected])


@pytest.mark.parametrize("water_slide", [False, True])
@pytest.mark.parametrize(
    ("custom", "smart", "extra"),
    [
        (True, True, [CleaningMode.CUSTOM, CleaningMode.SMART_MODE]),
        (False, True, [CleaningMode.SMART_MODE]),
        (True, False, [CleaningMode.CUSTOM]),
        (False, False, []),
    ],
)
def test_cleaning_mode_options_follow_app_flags(
    water_slide: bool, custom: bool, smart: bool, extra: list[CleaningMode]
) -> None:
    """Custom and SmartPlan options depend only on their feature flags, also on water-slide devices."""
    status_trait = _create_cleaning_mode_status_trait(
        is_water_slide_mode_supported=water_slide,
        is_custom_mode_supported=custom,  # the helper keeps is_customized_clean_supported=True
        is_smart_clean_mode_set_supported=smart,
    )

    assert status_trait.cleaning_mode_options == [
        CleaningMode.VACUUM,
        CleaningMode.VAC_AND_MOP,
        CleaningMode.MOP,
        *extra,
    ]


def test_cleaning_mode_options_custom_needs_customized_clean() -> None:
    """Custom mode is not offered without the customized-clean feature, even if the model allows it."""
    status_trait = _create_cleaning_mode_status_trait(
        is_custom_mode_supported=True,
        is_customized_clean_supported=False,
    )

    assert CleaningMode.CUSTOM not in status_trait.cleaning_mode_options


def test_mixed_custom_and_smart_codes_are_custom() -> None:
    """Custom wins over SmartPlan when the codes mix both."""
    trait = _create_cleaning_mode_status_trait(is_custom_mode_supported=True, is_smart_clean_mode_set_supported=True)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 106, 209, 300

    assert trait.current_cleaning_mode == CleaningMode.CUSTOM


@pytest.mark.parametrize(
    ("features", "codes"),
    [
        ({"is_custom_mode_supported": False}, (106, 204, 302)),
        ({"is_smart_clean_mode_set_supported": False}, (110, 209, 306)),
    ],
)
def test_current_mode_outside_options_is_none(features: dict[str, bool], codes: tuple[int, int, int]) -> None:
    """A mode that the device does not offer is not reported as the current mode."""
    trait = _create_cleaning_mode_status_trait(**features)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes

    assert trait.current_cleaning_mode is None


def test_saros_10r_smartplan_is_listed() -> None:
    """The Saros 10R SmartPlan codes classify as SmartPlan, which is among the options."""
    trait = _create_cleaning_mode_status_trait(
        is_water_slide_mode_supported=True,
        is_custom_mode_supported=True,
        is_smart_clean_mode_set_supported=True,
    )
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 110, 209, 306

    assert trait.current_cleaning_mode == CleaningMode.SMART_MODE
    assert trait.current_cleaning_mode in trait.cleaning_mode_options


def test_current_cleaning_mode_gentle_not_mop_without_pure_mop() -> None:
    """Test code 105 is not treated as mop-only on devices without pure mop."""
    status_trait = _create_cleaning_mode_status_trait(is_pure_clean_mop_supported=False)
    status_trait.fan_power = VacuumModes.GENTLE.code
    status_trait.water_box_mode = WaterModes.STANDARD.code
    status_trait.mop_mode = CleanRoutes.STANDARD.code

    assert status_trait.current_cleaning_mode == CleaningMode.VAC_AND_MOP


def test_water_slide_mode_mapping() -> None:
    """Test feature-aware water mode mapping for water slide mode devices."""
    short_model = mock_data.A114_PRODUCT_DATA["model"].split(".")[-1]
    features = DeviceFeatures.from_feature_flags(
        new_feature_info=int(mock_data.SAROS_10R_DEVICE_DATA["featureSet"]),
        new_feature_info_str=mock_data.SAROS_10R_DEVICE_DATA["newFeatureSet"],
        feature_info=[],
        product_nickname=SHORT_MODEL_TO_ENUM[short_model],
    )
    status_trait = StatusTrait(cast(DeviceFeaturesTrait, features), region="eu")

    assert features.is_water_slide_mode_supported
    assert status_trait.water_mode_mapping == {
        200: "off",
        221: "slight",
        225: "low",
        230: "gentle",
        235: "medium",
        240: "moderate",
        245: "high",
        250: "extreme",
    }
    assert [mode.display_name for mode in status_trait.water_mode_options] == [
        "off",
        "slight",
        "low",
        "gentle",
        "medium",
        "moderate",
        "high",
        "extreme",
    ]

    status_trait.water_box_mode = 225
    assert status_trait.water_mode_name == "low"
    status_trait.water_box_mode = 200
    assert status_trait.water_mode_name == "off"


@pytest.mark.parametrize(
    ("water_box_mode", "expected_name"),
    [
        (200, "off"),
        (210, "smart_water"),
        (221, "slight"),
        (223, "slight"),
        (224, "low"),
        (227, "low"),
        (228, "gentle"),
        (232, "gentle"),
        (233, "medium"),
        (236, "medium"),
        (237, "medium"),
        (238, "moderate"),
        (242, "moderate"),
        (243, "high"),
        (247, "high"),
        (248, "extreme"),
        (250, "extreme"),
        (220, None),
        (251, None),
        (999, None),
    ],
)
def test_water_slide_mode_name_covers_slider_positions(water_box_mode: int, expected_name: str | None) -> None:
    """Every slider position resolves to the label of its range in the Roborock app."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    status_trait.water_box_mode = water_box_mode

    assert status_trait.water_mode_name == expected_name


def test_option_lists_exclude_special_codes() -> None:
    """SmartPlan and custom codes are never offered as fan, water or mop route choices."""
    trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)
    special = {106, 110, 204, 209, 302, 306}
    assert special.isdisjoint(m.code for m in trait.fan_speed_options)
    assert special.isdisjoint(m.code for m in trait.water_mode_options)
    assert special.isdisjoint(m.code for m in trait.mop_route_options)
    assert special.isdisjoint(trait.fan_speed_mapping)
    assert special.isdisjoint(trait.water_mode_mapping)
    assert special.isdisjoint(trait.mop_route_mapping)


@pytest.mark.parametrize("water_slide", [False, True])
@pytest.mark.parametrize(
    ("fan", "water", "mop", "names"),
    [
        (110, 209, 306, ("smart_mode", "smart_mode", "smart_mode")),
        (106, 204, 302, ("custom", "custom", "custom")),
    ],
)
def test_special_code_names(water_slide: bool, fan: int, water: int, mop: int, names: tuple[str, str, str]) -> None:
    """Special codes are still named even though they are not selectable."""
    trait = _create_cleaning_mode_status_trait(
        is_smart_clean_mode_set_supported=True, is_water_slide_mode_supported=water_slide
    )
    trait.fan_power, trait.water_box_mode, trait.mop_mode = fan, water, mop
    assert (trait.fan_speed_name, trait.water_mode_name, trait.mop_route_name) == names


def test_water_slide_raw_position_name_unchanged() -> None:
    """Raw slider positions keep resolving to their app range name."""
    trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    trait.water_box_mode = 227
    assert trait.water_mode_name == "low"


@pytest.mark.parametrize(
    ("soft", "pure_mop", "in_list", "name"),
    [
        (True, False, True, "gentle"),
        (True, True, True, "gentle"),
        (False, True, False, "off"),
        (False, False, False, "gentle"),
    ],
)
def test_fan_code_105(soft: bool, pure_mop: bool, in_list: bool, name: str) -> None:
    """Code 105 is only selectable as gentle on soft-clean devices but is always named."""
    trait = _create_cleaning_mode_status_trait(is_soft_clean_mode_supported=soft, is_pure_clean_mop_supported=pure_mop)
    trait.fan_power = 105
    assert (105 in {m.code for m in trait.fan_speed_options}) is in_list
    assert trait.fan_speed_name == name


def test_unknown_codes_have_no_name() -> None:
    """Codes that are neither selectable nor special have no name."""
    trait = _create_cleaning_mode_status_trait()
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 999, 999, 999
    assert (trait.fan_speed_name, trait.water_mode_name, trait.mop_route_name) == (None, None, None)


def test_update_from_dps(status_trait: StatusTrait) -> None:
    """Test updating status from data protocol push message."""
    assert status_trait.battery is None
    assert status_trait.state is None

    status_trait.update_from_dps(
        {
            RoborockDataProtocol.STATE: 5,
            RoborockDataProtocol.BATTERY: 85,
            RoborockDataProtocol.FAN_POWER: 102,
        }
    )

    assert status_trait.state == 5
    assert status_trait.battery == 85
    assert status_trait.fan_power == 102


def test_update_from_dps_partial(status_trait: StatusTrait) -> None:
    """Test that partial updates only modify the specified fields."""
    status_trait.battery = 100
    status_trait.state = RoborockStateCode.charging

    status_trait.update_from_dps(
        {
            RoborockDataProtocol.BATTERY: 90,
        }
    )

    assert status_trait.battery == 90
    assert status_trait.state == RoborockStateCode.charging  # Unchanged


def test_update_listener(status_trait: StatusTrait) -> None:
    """Test that update listeners receive notifications."""
    event = asyncio.Event()
    unsubscribe = status_trait.add_update_listener(event.set)

    status_trait.update_from_dps(
        {
            RoborockDataProtocol.BATTERY: 88,
        }
    )

    assert event.is_set()
    event.clear()

    unsubscribe()

    status_trait.update_from_dps(
        {
            RoborockDataProtocol.BATTERY: 87,
        }
    )

    assert not event.is_set()


def test_update_listener_ignores_unrelated(status_trait: StatusTrait) -> None:
    """Test that update listeners are not notified for unrecognized data points."""
    event = asyncio.Event()
    unsubscribe = status_trait.add_update_listener(event.set)

    # TASK_COMPLETE is not annotated with dps metadata on StatusV2
    status_trait.update_from_dps(
        {
            RoborockDataProtocol.TASK_COMPLETE: 1,
        }
    )

    assert not event.is_set()
    unsubscribe()


async def test_leave_smartplan_without_shake_resets_route(mock_rpc_channel: AsyncMock) -> None:
    """Without a route setting the route is still reset to standard when leaving SmartPlan."""
    trait = _create_cleaning_mode_status_trait(
        is_smart_clean_mode_set_supported=True,
        is_shake_mop_set_supported=False,
        is_set_clean_motor_mode_supported=False,
        is_clean_route_setting_supported=False,
    )
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 110, 209, 306
    await trait.set_cleaning_mode(CleaningMode.VAC_AND_MOP)

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.SET_CUSTOM_MODE, params=[102]),
        call(RoborockCommand.SET_WATER_BOX_CUSTOM_MODE, params=[202]),
        call(RoborockCommand.SET_MOP_MODE, params=[300]),
    ]
    assert trait.current_cleaning_mode == CleaningMode.VAC_AND_MOP
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (102, 202, 300)


async def test_set_cleaning_mode_without_route_keeps_mop_mode(mock_rpc_channel: AsyncMock) -> None:
    """When no route is sent the cached route is left alone."""
    trait = _create_cleaning_mode_status_trait(is_clean_route_setting_supported=False, is_shake_mop_set_supported=False)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.mop_mode = 300
    await trait.set_cleaning_mode(CleaningMode.VACUUM)

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.SET_CUSTOM_MODE, params=[102]),
        call(RoborockCommand.SET_WATER_BOX_CUSTOM_MODE, params=[200]),
    ]
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (102, 200, 300)


async def test_set_cleaning_mode_notifies_listeners_once(mock_rpc_channel: AsyncMock) -> None:
    """Every command is sent first and listeners are notified a single time afterwards."""
    trait = _create_cleaning_mode_status_trait(is_shake_mop_set_supported=False, is_set_clean_motor_mode_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.mop_mode = 306  # SmartPlan route, reset to standard
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))
    await trait.set_cleaning_mode(CleaningMode.VAC_AND_MOP)

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 202}]),
        call(RoborockCommand.SET_MOP_MODE, params=[300]),
    ]
    assert len(updates) == 1


async def test_set_cleaning_mode_failure_keeps_fields(mock_rpc_channel: AsyncMock) -> None:
    """An exception mid-sequence stops sending and leaves the cached status unchanged."""
    trait = _create_cleaning_mode_status_trait(
        is_shake_mop_set_supported=False, is_set_clean_motor_mode_supported=False
    )
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 110, 209, 306
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))
    mock_rpc_channel.send_command.side_effect = ["ok", RoborockException("boom"), "ok"]

    with pytest.raises(RoborockException, match="boom"):
        await trait.set_cleaning_mode(CleaningMode.VAC_AND_MOP)

    assert mock_rpc_channel.send_command.call_count == 2
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (110, 209, 306)
    assert updates == []


async def test_set_water_mode_saros_vac_and_mop(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 103, 225, 301
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))
    await trait.set_water_mode(WaterModes.PURE_WATER_FLOW_MIDDLE)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 103, "water_box_mode": 235, "mop_mode": 300}]
    )
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (103, 235, 300)
    assert len(updates) == 1


@pytest.mark.parametrize(
    ("call_name", "arg"),
    [("set_fan_speed", VacuumModes.MAX), ("set_water_mode", WaterModes.HIGH), ("set_mop_route", CleanRoutes.DEEP)],
)
async def test_setters_refuse_in_smartplan(mock_rpc_channel: AsyncMock, call_name: str, arg: VacuumModes) -> None:
    trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 110, 209, 306
    with pytest.raises(RoborockUnsupportedFeature):
        await getattr(trait, call_name)(arg)
    mock_rpc_channel.send_command.assert_not_called()
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (110, 209, 306)


async def test_mop_only_water_change_keeps_105_and_fan_refused(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 105, 202, 300

    await trait.set_water_mode(WaterModes.HIGH)
    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 105, "water_box_mode": 203, "mop_mode": 300}]
    )

    mock_rpc_channel.send_command.reset_mock()
    with pytest.raises(RoborockUnsupportedFeature):
        await trait.set_fan_speed(VacuumModes.MAX)
    mock_rpc_channel.send_command.assert_not_called()


async def test_set_water_mode_accepts_aliased_code(mock_rpc_channel: AsyncMock) -> None:
    """HIGH shares code 203 with INTENSE, which is what the shake-mop model lists."""
    trait = _create_cleaning_mode_status_trait()
    assert WaterModes.HIGH not in trait.water_mode_options
    assert WaterModes.INTENSE in trait.water_mode_options
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300

    await trait.set_water_mode(WaterModes.HIGH)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 203, "mop_mode": 300}]
    )
    assert trait.water_box_mode == 203


async def test_set_water_mode_slide_accepts_any_slider_code(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 225, 300

    await trait.set_water_mode(WaterModes.PURE_WATER_FLOW_START)  # 221, the lowest slider position

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 221, "mop_mode": 300}]
    )


async def test_set_mop_route_refused_without_shake(mock_rpc_channel: AsyncMock) -> None:
    """Without the shake module the model offers no route choice, so the library does not send it."""
    trait = _create_cleaning_mode_status_trait(is_shake_mop_set_supported=False, is_set_clean_motor_mode_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300

    with pytest.raises(RoborockUnsupportedFeature):
        await trait.set_mop_route(CleanRoutes.DEEP)

    mock_rpc_channel.send_command.assert_not_called()
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (102, 202, 300)


_SAROS_10R_FEATURES = {
    "is_water_slide_mode_supported": True,
    "is_careful_slow_mop_supported": True,
    "is_max_plus_mode_supported": True,
}


_SLIDE_WATER_WITHOUT_OFF = [
    WaterModes.PURE_WATER_FLOW_START,
    WaterModes.PURE_WATER_FLOW_SMALL,
    WaterModes.PURE_WATER_FLOW_GENTLE,
    WaterModes.PURE_WATER_FLOW_MIDDLE,
    WaterModes.PURE_WATER_FLOW_LARGE,
    WaterModes.PURE_WATER_SUPER_BEGIN,
    WaterModes.PURE_WATER_FLOW_END,
]


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        # VAC_AND_MOP: no Max+, routes fast and standard only, no OFF.
        (
            (102, 235, 300),
            (
                [VacuumModes.QUIET, VacuumModes.BALANCED, VacuumModes.TURBO, VacuumModes.MAX],
                {CleanRoutes.FAST, CleanRoutes.STANDARD},
                _SLIDE_WATER_WITHOUT_OFF,
            ),
        ),
        # VACUUM: Max+ is offered, routes fast and standard only.
        (
            (102, 200, 300),
            (
                [VacuumModes.QUIET, VacuumModes.BALANCED, VacuumModes.TURBO, VacuumModes.MAX, VacuumModes.MAX_PLUS],
                {CleanRoutes.FAST, CleanRoutes.STANDARD},
                [],
            ),
        ),
        # MOP: no fan speed, the full route list.
        (
            (105, 235, 300),
            (
                [],
                {CleanRoutes.STANDARD, CleanRoutes.DEEP, CleanRoutes.DEEP_PLUS, CleanRoutes.FAST},
                _SLIDE_WATER_WITHOUT_OFF,
            ),
        ),
    ],
)
def test_display_options_follow_the_cleaning_mode(
    codes: tuple[int, int, int],
    expected: tuple[list[VacuumModes], set[CleanRoutes], list[WaterModes]],
) -> None:
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes
    assert trait.fan_speed_display_options == expected[0]
    assert set(trait.mop_route_display_options) == expected[1]
    assert trait.water_mode_display_options == expected[2]


@pytest.mark.parametrize(
    ("overrides", "expected_fan"),
    [
        ({"is_pure_clean_mop_supported": False, "is_none_pure_clean_mop_with_max_plus": True}, True),
        ({"is_pure_clean_mop_supported": False, "is_max_plus_mode_supported": True}, False),
    ],
)
def test_max_plus_without_sub_tabs(overrides: dict[str, bool], expected_fan: bool) -> None:
    trait = _create_cleaning_mode_status_trait(**overrides)
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300
    assert (VacuumModes.MAX_PLUS in trait.fan_speed_display_options) is expected_fan


@pytest.mark.parametrize(
    ("call_name", "arg", "codes"),
    [
        ("set_mop_route", CleanRoutes.DEEP, (102, 235, 300)),
        ("set_fan_speed", VacuumModes.MAX_PLUS, (102, 235, 300)),
        ("set_water_mode", WaterModes.OFF, (102, 235, 300)),
        ("set_mop_route", CleanRoutes.DEEP, (102, 200, 300)),
        ("set_fan_speed", VacuumModes.MAX_PLUS, (105, 235, 300)),
    ],
)
async def test_setters_refuse_values_outside_the_mode_list(
    mock_rpc_channel: AsyncMock, call_name: str, arg: VacuumModes | CleanRoutes | WaterModes, codes: tuple[int, ...]
) -> None:
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes
    with pytest.raises(RoborockUnsupportedFeature):
        await getattr(trait, call_name)(arg)
    mock_rpc_channel.send_command.assert_not_called()


async def test_set_fan_speed_max_plus_in_vacuum(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 200, 300

    await trait.set_fan_speed(VacuumModes.MAX_PLUS)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 108, "water_box_mode": 200, "mop_mode": 300}]
    )


async def test_set_mop_route_fast_in_vacuum(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 103, 200, 300

    await trait.set_mop_route(CleanRoutes.FAST)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 103, "water_box_mode": 200, "mop_mode": 304}]
    )
    assert trait.mop_mode == 304


async def test_set_water_mode_replaces_deep_route_left_by_older_client(mock_rpc_channel: AsyncMock) -> None:
    """The robot rejects route 301 in vacuum and mop, so it is sent as standard."""
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 235, 301

    await trait.set_water_mode(WaterModes.PURE_WATER_FLOW_LARGE)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 240, "mop_mode": 300}]
    )
    assert trait.mop_mode == 300


async def test_set_cleaning_mode_replaces_values_from_the_previous_tab(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 108, 200, 300

    await trait.set_cleaning_mode(CleaningMode.VAC_AND_MOP)

    sent = mock_rpc_channel.send_command.call_args.kwargs["params"][0]
    assert sent["fan_power"] == 102
    assert sent["mop_mode"] == 300


async def test_set_fan_speed_vac_and_mop(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300

    await trait.set_fan_speed(VacuumModes.MAX)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 104, "water_box_mode": 202, "mop_mode": 300}]
    )
    assert trait.fan_power == 104


@pytest.mark.parametrize(
    ("call_name", "arg"), [("set_fan_speed", VacuumModes.SMART_MODE), ("set_mop_route", CleanRoutes.CUSTOMIZED)]
)
async def test_setters_refuse_special_values(mock_rpc_channel: AsyncMock, call_name: str, arg: VacuumModes) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300
    with pytest.raises(RoborockUnsupportedFeature):
        await getattr(trait, call_name)(arg)
    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(
    ("call_name", "arg"),
    [("set_fan_speed", VacuumModes.MAX), ("set_water_mode", WaterModes.HIGH), ("set_mop_route", CleanRoutes.DEEP)],
)
async def test_setters_require_loaded_status(mock_rpc_channel: AsyncMock, call_name: str, arg: VacuumModes) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    with pytest.raises(RoborockException, match="Status is not loaded"):
        await getattr(trait, call_name)(arg)
    mock_rpc_channel.send_command.assert_not_called()


async def test_setter_failure_keeps_fields(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException, match="boom"):
        await trait.set_fan_speed(VacuumModes.MAX)

    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (102, 202, 300)
    assert updates == []


async def test_set_fan_speed_vacuum_only(mock_rpc_channel: AsyncMock) -> None:
    """A vacuum without a mop has no water mode and only receives the fan command."""
    trait = _create_cleaning_mode_status_trait(is_support_water_mode=False, is_shake_mop_set_supported=True)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power = 102
    assert trait.water_box_mode is None

    await trait.set_fan_speed(VacuumModes.MAX)

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.SET_CUSTOM_MODE, params=[104])
    assert trait.fan_power == 104
    assert trait.water_box_mode is None


async def test_set_water_mode_refuses_off_while_mopping_only(mock_rpc_channel: AsyncMock) -> None:
    trait = _create_cleaning_mode_status_trait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 105, 202, 300
    with pytest.raises(RoborockUnsupportedFeature):
        await trait.set_water_mode(WaterModes.OFF)
    mock_rpc_channel.send_command.assert_not_called()
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (105, 202, 300)


async def test_water_can_be_turned_on_without_mode_tabs(mock_rpc_channel: AsyncMock) -> None:
    """Without a mop-only tab a water-off state is still the general tab, so water stays adjustable."""
    trait = _create_cleaning_mode_status_trait(is_pure_clean_mop_supported=False)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 200, 300
    assert trait.current_cleaning_mode == CleaningMode.VACUUM
    assert trait.is_water_mode_adjustable
    assert WaterModes.OFF in trait.water_mode_display_options

    await trait.set_water_mode(WaterModes.HIGH)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 203, "mop_mode": 300}]
    )


def test_vacuum_without_a_mop_keeps_max_plus() -> None:
    trait = _create_cleaning_mode_status_trait(is_support_water_mode=False, is_max_plus_mode_supported=True)
    trait.fan_power = 102
    assert VacuumModes.MAX_PLUS in trait.fan_speed_display_options


async def test_setters_send_no_route_without_shake(mock_rpc_channel: AsyncMock) -> None:
    """Without the shake module no route is sent, even when the model has a route setting."""
    trait = _create_cleaning_mode_status_trait(
        is_shake_mop_set_supported=False, is_set_clean_motor_mode_supported=True, is_clean_route_setting_supported=True
    )
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 102, 202, 300  # VAC_AND_MOP

    await trait.set_water_mode(WaterModes.HIGH)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 203}]
    )
    assert (trait.fan_power, trait.water_box_mode, trait.mop_mode) == (102, 203, 300)


async def test_set_mop_route_replaces_the_mop_only_fan_code_left_in_vacuum(mock_rpc_channel: AsyncMock) -> None:
    """Fan code 105 outside mopping only is replaced by balanced, like Max+."""
    trait = _create_cleaning_mode_status_trait(**_SAROS_10R_FEATURES)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = 105, 200, 300
    assert trait.current_cleaning_mode == CleaningMode.VACUUM

    await trait.set_mop_route(CleanRoutes.FAST)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_MOTOR_MODE, params=[{"fan_power": 102, "water_box_mode": 200, "mop_mode": 304}]
    )


@pytest.mark.parametrize("codes", [(110, 209, 306), (106, 204, 302)])
def test_mop_route_special_values_need_shake(codes: tuple[int, int, int]) -> None:
    """Without the shake module no route is listed, not even the SmartPlan or custom value."""
    trait = _create_cleaning_mode_status_trait(
        is_smart_clean_mode_set_supported=True, is_custom_mode_supported=True, is_shake_mop_set_supported=False
    )
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes
    assert trait.mop_route_options == []
    assert trait.mop_route_display_options == []
    assert trait.water_mode_display_options != []


_FAN = CleaningSetting.FAN_SPEED
_WATER = CleaningSetting.WATER_MODE
_ROUTE = CleaningSetting.MOP_ROUTE


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"is_support_water_mode": False}, {_FAN}),
        ({"is_water_slide_mode_supported": True}, {_FAN, _WATER, _ROUTE}),
        ({"is_clean_route_fast_mode_supported": False}, {_FAN, _WATER, _ROUTE}),
        ({"is_pure_clean_mop_supported": False, "is_clean_route_fast_mode_supported": False}, {_FAN, _WATER}),
        ({"is_shake_mop_set_supported": False}, {_FAN, _WATER}),
        ({"is_clean_efficiency_supported": True}, {_FAN, _WATER, _ROUTE}),
        (
            {"is_pure_clean_mop_supported": False, "is_none_pure_clean_mop_with_max_plus": True},
            {_FAN, _WATER, _ROUTE},
        ),
    ],
)
def test_supported_cleaning_settings(overrides: dict[str, bool], expected: set[CleaningSetting]) -> None:
    """The option lists and mappings are empty exactly for the settings the model does not have."""
    trait = _create_cleaning_mode_status_trait(**overrides)
    assert trait.supported_cleaning_settings == [setting for setting in CleaningSetting if setting in expected]
    assert bool(trait.fan_speed_options) and bool(trait.fan_speed_mapping)
    assert bool(trait.water_mode_options) is (_WATER in expected)
    assert bool(trait.water_mode_mapping) is (_WATER in expected)
    assert bool(trait.mop_route_options) is (_ROUTE in expected)
    assert bool(trait.mop_route_mapping) is (_ROUTE in expected)
    # The cleaning mode select exists exactly when the model has a mop.
    assert bool(trait.cleaning_mode_options) is (_WATER in expected)


@pytest.mark.parametrize(
    ("codes", "expected_fan", "expected_water", "expected_route"),
    [
        ((106, 204, 302), VacuumModes.CUSTOMIZED, WaterModes.CUSTOMIZED, CleanRoutes.CUSTOMIZED),
        ((110, 209, 306), VacuumModes.SMART_MODE, WaterModes.SMART_MODE, CleanRoutes.SMART_MODE),
    ],
)
@pytest.mark.parametrize(
    ("setter_name", "value"),
    [
        ("set_fan_speed", VacuumModes.TURBO),
        ("set_water_mode", WaterModes.STANDARD),
        ("set_mop_route", CleanRoutes.STANDARD),
    ],
)
async def test_reported_special_mode_without_support_flags(
    mock_rpc_channel: AsyncMock,
    codes: tuple[int, int, int],
    expected_fan: VacuumModes,
    expected_water: WaterModes,
    expected_route: CleanRoutes,
    setter_name: str,
    value: VacuumModes | WaterModes | CleanRoutes,
) -> None:
    """SmartPlan or custom codes put the robot in that mode, even when the model lacks the support flags."""
    trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=False, is_custom_mode_supported=False)
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    trait.fan_power, trait.water_box_mode, trait.mop_mode = codes

    assert trait.current_cleaning_mode is None
    assert trait.fan_speed_display_options == [expected_fan]
    assert trait.water_mode_display_options == [expected_water]
    assert trait.mop_route_display_options == [expected_route]
    assert not trait.is_fan_speed_adjustable
    assert not trait.is_water_mode_adjustable
    assert not trait.is_mop_route_adjustable
    setter = getattr(trait, setter_name)
    with pytest.raises(RoborockUnsupportedFeature):
        await setter(value)
    mock_rpc_channel.send_command.assert_not_called()

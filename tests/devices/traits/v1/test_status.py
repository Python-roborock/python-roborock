"""Tests for the StatusTrait class."""

from typing import cast
from unittest.mock import AsyncMock

import pytest

from roborock import CleaningModes, CleanRoutes, VacuumModes, WaterModes
from roborock.data import SHORT_MODEL_TO_ENUM
from roborock.data.v1 import (
    RoborockStateCode,
)
from roborock.device_features import DeviceFeatures
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
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


async def test_refresh_status_propagates_exception(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that exceptions from RPC channel are propagated."""
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    with pytest.raises(RoborockException, match="Communication error"):
        await status_trait.refresh()


async def test_refresh_status_invalid_format(status_trait: StatusTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test that invalid response format raises ValueError."""
    mock_rpc_channel.send_command.return_value = "invalid"

    with pytest.raises(ValueError, match="Unexpected StatusV2 response format"):
        await status_trait.refresh()


def test_none_values(status_trait: StatusTrait) -> None:
    """Test that none values are returned correctly."""
    status_trait.fan_power = None
    status_trait.water_box_mode = None
    status_trait.mop_mode = None
    assert status_trait.fan_speed_name is None
    assert status_trait.water_mode_name is None
    assert status_trait.mop_route_name is None


def test_options(status_trait: StatusTrait) -> None:
    """Test that fan_speed_options returns a list of options."""
    assert isinstance(status_trait.fan_speed_options, list)
    assert len(status_trait.fan_speed_options) > 0
    assert isinstance(status_trait.water_mode_options, list)
    assert len(status_trait.water_mode_options) > 0
    assert isinstance(status_trait.mop_route_options, list)
    assert len(status_trait.mop_route_options) > 0


def test_cleaning_mode_options() -> None:
    """Test the high-level cleaning mode options for the device."""
    status_trait = _create_cleaning_mode_status_trait()
    assert status_trait.cleaning_mode_options == [
        CleaningModes.VACUUM,
        CleaningModes.VAC_AND_MOP,
        CleaningModes.MOP,
        CleaningModes.CUSTOM,
    ]


@pytest.mark.parametrize(
    ("fan_power", "water_box_mode", "mop_mode", "expected_mode"),
    [
        (
            VacuumModes.BALANCED.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningModes.VAC_AND_MOP,
        ),
        (
            VacuumModes.BALANCED.code,
            WaterModes.OFF.code,
            CleanRoutes.STANDARD.code,
            CleaningModes.VACUUM,
        ),
        (
            VacuumModes.OFF.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningModes.MOP,
        ),
        (
            VacuumModes.CUSTOMIZED.code,
            WaterModes.STANDARD.code,
            CleanRoutes.STANDARD.code,
            CleaningModes.CUSTOM,
        ),
        (
            VacuumModes.BALANCED.code,
            WaterModes.SMART_MODE.code,
            CleanRoutes.STANDARD.code,
            CleaningModes.SMART_MODE,
        ),
    ],
)
def test_current_cleaning_mode(
    fan_power: int,
    water_box_mode: int,
    mop_mode: int,
    expected_mode: CleaningModes,
) -> None:
    """Test the current high-level cleaning mode classification."""
    status_trait = _create_cleaning_mode_status_trait(is_smart_clean_mode_set_supported=True)
    status_trait.fan_power = fan_power
    status_trait.water_box_mode = water_box_mode
    status_trait.mop_mode = mop_mode

    assert status_trait.current_cleaning_mode == expected_mode
    assert status_trait.cleaning_mode_name == expected_mode.value


def test_current_cleaning_mode_with_brush_up_mop() -> None:
    """Test brush-up mop-only classification on supported devices."""
    status_trait = _create_cleaning_mode_status_trait(is_support_main_brush_up_down_supported=True)
    status_trait.fan_power = VacuumModes.OFF_RAISE_MAIN_BRUSH.code
    status_trait.water_box_mode = WaterModes.STANDARD.code
    status_trait.mop_mode = CleanRoutes.STANDARD.code

    assert status_trait.current_cleaning_mode == CleaningModes.MOP


def test_current_cleaning_mode_none() -> None:
    """Test that incomplete status values do not classify a cleaning mode."""
    status_trait = _create_cleaning_mode_status_trait()
    status_trait.fan_power = None
    assert status_trait.current_cleaning_mode is None
    assert status_trait.cleaning_mode_name is None


def test_current_cleaning_mode_without_mop_route_status() -> None:
    """Test older V1 devices can classify cleaning mode without mop route status."""
    status_trait = _create_cleaning_mode_status_trait(
        is_clean_route_setting_supported=False,
        is_customized_clean_supported=False,
    )
    status_trait.fan_power = VacuumModes.BALANCED.code
    status_trait.water_box_mode = WaterModes.OFF.code
    status_trait.mop_mode = None

    assert status_trait.current_cleaning_mode == CleaningModes.VACUUM


def test_get_cleaning_mode_parameters() -> None:
    """Test payload generation for supported high-level cleaning modes."""
    status_trait = _create_cleaning_mode_status_trait()
    assert status_trait.get_cleaning_mode_parameters(CleaningModes.VACUUM) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert status_trait.get_cleaning_mode_parameters("custom") == [
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
        status_trait.get_cleaning_mode_parameters(CleaningModes.SMART_MODE)


def test_get_cleaning_mode_parameters_invalid_name() -> None:
    """Test invalid cleaning mode names raise RoborockUnsupportedFeature."""
    status_trait = _create_cleaning_mode_status_trait()
    with pytest.raises(RoborockUnsupportedFeature, match="not supported"):
        status_trait.get_cleaning_mode_parameters("invalid_mode")


async def test_set_cleaning_mode(
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test setting the high-level cleaning mode."""
    status_trait = _create_cleaning_mode_status_trait()
    status_trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    await status_trait.set_cleaning_mode(CleaningModes.CUSTOM)

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
        CleaningModes.VACUUM,
        CleaningModes.VAC_AND_MOP,
        CleaningModes.MOP,
        CleaningModes.CUSTOM,
        CleaningModes.SMART_MODE,
    ]


def test_get_cleaning_mode_parameters_with_brush_up_mop() -> None:
    """Test mop-only uses the brush-up mode when supported."""
    status_trait = _create_cleaning_mode_status_trait(is_support_main_brush_up_down_supported=True)

    assert status_trait.get_cleaning_mode_parameters(CleaningModes.MOP) == [
        {
            "fan_power": VacuumModes.OFF_RAISE_MAIN_BRUSH.code,
            "water_box_mode": WaterModes.STANDARD.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]


def test_get_cleaning_mode_parameters_without_clean_route_setting() -> None:
    """Test older V1 devices use the 2-field clean motor payload."""
    status_trait = _create_cleaning_mode_status_trait(
        is_clean_route_setting_supported=False,
        is_customized_clean_supported=False,
    )

    assert status_trait.get_cleaning_mode_parameters(CleaningModes.VACUUM) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
        }
    ]
    assert status_trait.get_cleaning_mode_parameters(CleaningModes.VAC_AND_MOP) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.STANDARD.code,
        }
    ]
    assert status_trait.get_cleaning_mode_parameters(CleaningModes.MOP) == [
        {
            "fan_power": VacuumModes.OFF.code,
            "water_box_mode": WaterModes.STANDARD.code,
        }
    ]


def test_get_cleaning_mode_parameters_water_slide_device() -> None:
    """Water-slide devices should use a slide-compatible water code, not 202."""
    status_trait = _create_cleaning_mode_status_trait(is_water_slide_mode_supported=True)

    assert status_trait.get_cleaning_mode_parameters(CleaningModes.VACUUM) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.OFF.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert status_trait.get_cleaning_mode_parameters(CleaningModes.VAC_AND_MOP) == [
        {
            "fan_power": VacuumModes.BALANCED.code,
            "water_box_mode": WaterModes.PURE_WATER_FLOW_MIDDLE.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]
    assert status_trait.get_cleaning_mode_parameters(CleaningModes.MOP) == [
        {
            "fan_power": VacuumModes.OFF.code,
            "water_box_mode": WaterModes.PURE_WATER_FLOW_MIDDLE.code,
            "mop_mode": CleanRoutes.STANDARD.code,
        }
    ]


def test_current_cleaning_mode_gentle_not_mop_without_pure_mop() -> None:
    """Test code 105 is not treated as mop-only on devices without pure mop."""
    status_trait = _create_cleaning_mode_status_trait(is_pure_clean_mop_supported=False)
    status_trait.fan_power = VacuumModes.GENTLE.code
    status_trait.water_box_mode = WaterModes.STANDARD.code
    status_trait.mop_mode = CleanRoutes.STANDARD.code

    assert status_trait.current_cleaning_mode == CleaningModes.VAC_AND_MOP


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
        235: "medium",
        245: "moderate",
        248: "high",
        250: "extreme",
    }
    assert [mode.value for mode in status_trait.water_mode_options] == [
        "off",
        "slight",
        "low",
        "medium",
        "moderate",
        "high",
        "extreme",
    ]

    status_trait.water_box_mode = 225
    assert status_trait.water_mode_name == "low"
    status_trait.water_box_mode = 200
    assert status_trait.water_mode_name == "off"

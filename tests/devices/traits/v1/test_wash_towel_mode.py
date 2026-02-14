"""Tests for the WashTowelModeTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import (
    RoborockDockTypeCode,
    WashTowelModes,
)
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.wash_towel_mode import WashTowelModeTrait
from roborock.roborock_typing import RoborockCommand

WASH_TOWEL_MODE_DATA = {"wash_mode": WashTowelModes.SMART.code}


@pytest.fixture(name="wash_towel_mode")
def wash_towel_mode_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> WashTowelModeTrait | None:
    """Create a WashTowelModeTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.wash_towel_mode


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s8_dock),
        (RoborockDockTypeCode.p10_dock),
        (RoborockDockTypeCode.qrevo_s_dock),
    ],
)
async def test_wash_towel_mode_available(
    wash_towel_mode: WashTowelModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test successfully refreshing the wash towel mode."""
    assert wash_towel_mode is not None

    mock_rpc_channel.send_command.side_effect = [
        WASH_TOWEL_MODE_DATA,
    ]

    await wash_towel_mode.refresh()

    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_WASH_TOWEL_MODE),
        ]
    )

    assert wash_towel_mode.wash_mode == WashTowelModes.SMART


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s7_max_ultra_dock),
        (RoborockDockTypeCode.no_dock),
    ],
)
async def test_unsupported_wash_towel_mode(
    wash_towel_mode: WashTowelModeTrait | None, dock_type_code: RoborockDockTypeCode
) -> None:
    """Test that the trait is not available for unsupported dock types."""
    assert wash_towel_mode is None


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(RoborockDockTypeCode.s8_dock)],
)
@pytest.mark.parametrize(
    ("wash_mode"),
    [
        (WashTowelModes.SMART),
        (WashTowelModes.LIGHT),
    ],
)
async def test_set_wash_towel_mode(
    wash_towel_mode: WashTowelModeTrait | None,
    mock_rpc_channel: AsyncMock,
    wash_mode: WashTowelModes,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test setting the wash towel mode."""
    assert wash_towel_mode is not None

    await wash_towel_mode.set_wash_towel_mode(wash_mode)

    mock_rpc_channel.send_command.assert_called_with(
        RoborockCommand.SET_WASH_TOWEL_MODE, params={"wash_mode": wash_mode.code}
    )


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(RoborockDockTypeCode.s8_dock)],
)
async def test_start_wash(
    wash_towel_mode: WashTowelModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test starting the wash."""
    assert wash_towel_mode is not None

    await wash_towel_mode.start_wash()

    mock_rpc_channel.send_command.assert_called_with(RoborockCommand.APP_START_WASH)


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(RoborockDockTypeCode.s8_dock)],
)
async def test_stop_wash(
    wash_towel_mode: WashTowelModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test stopping the wash."""
    assert wash_towel_mode is not None

    await wash_towel_mode.stop_wash()

    mock_rpc_channel.send_command.assert_called_with(RoborockCommand.APP_STOP_WASH)


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(RoborockDockTypeCode.s8_dock)],
)
@pytest.mark.parametrize(
    (
        "is_super_deep_wash_supported",
        "is_dirty_replenish_clean_supported",
        "expected_modes",
    ),
    [
        (
            False,
            False,
            [WashTowelModes.LIGHT, WashTowelModes.BALANCED, WashTowelModes.DEEP],
        ),
        (
            True,
            False,
            [
                WashTowelModes.LIGHT,
                WashTowelModes.BALANCED,
                WashTowelModes.DEEP,
                WashTowelModes.SUPER_DEEP,
            ],
        ),
        (
            False,
            True,
            [
                WashTowelModes.LIGHT,
                WashTowelModes.BALANCED,
                WashTowelModes.DEEP,
                WashTowelModes.SMART,
            ],
        ),
        (
            True,
            True,
            [
                WashTowelModes.LIGHT,
                WashTowelModes.BALANCED,
                WashTowelModes.DEEP,
                WashTowelModes.SMART,
            ],
        ),
    ],
)
async def test_wash_towel_mode_options(
    wash_towel_mode: WashTowelModeTrait | None,
    dock_type_code: RoborockDockTypeCode,
    is_super_deep_wash_supported: bool,
    is_dirty_replenish_clean_supported: bool,
    expected_modes: list[WashTowelModes],
) -> None:
    """Test what modes are available based on device features."""
    assert wash_towel_mode is not None
    # We need to clear the cached property to ensure it re-reads the features
    if "wash_towel_mode_options" in wash_towel_mode.__dict__:
        del wash_towel_mode.__dict__["wash_towel_mode_options"]

    # Mock the device features
    assert wash_towel_mode.device_feature_trait is not None
    wash_towel_mode.device_feature_trait.is_super_deep_wash_supported = is_super_deep_wash_supported
    wash_towel_mode.device_feature_trait.is_dirty_replenish_clean_supported = is_dirty_replenish_clean_supported

    assert wash_towel_mode.wash_towel_mode_options == expected_modes

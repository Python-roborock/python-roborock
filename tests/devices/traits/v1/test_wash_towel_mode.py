"""Tests for the WashTowelModeTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockTypeCode, RoborockDockWashTowelModeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.wash_towel_mode import WashTowelModeTrait
from roborock.roborock_typing import RoborockCommand

WASH_TOWEL_MODE_DATA = [{"wash_mode": RoborockDockWashTowelModeCode.smart}]


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

    assert wash_towel_mode.wash_mode == RoborockDockWashTowelModeCode.smart


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

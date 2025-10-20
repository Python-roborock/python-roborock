"""Tests for the DockSummaryTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data.v1.v1_code_mappings import (
    RoborockDockTypeCode,
)
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.smart_wash_params import SmartWashParamsTrait
from roborock.roborock_typing import RoborockCommand

SMART_WASH_DATA = [{"smart_wash": 5, "wash_interval": 6}]


@pytest.fixture(name="smart_wash_params")
def smart_wash_params_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> SmartWashParamsTrait | None:
    """Create a SmartWashParamsTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.smart_wash_params


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s8_dock),
        (RoborockDockTypeCode.p10_dock),
        (RoborockDockTypeCode.qrevo_s_dock),
    ],
)
async def test_smart_wash_available(
    smart_wash_params: SmartWashParamsTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test successfully refreshing the smart wash params."""
    assert smart_wash_params is not None

    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        SMART_WASH_DATA,
    ]

    # Call the method
    await smart_wash_params.refresh()

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_SMART_WASH_PARAMS),
        ]
    )

    # Verify the summary object contains the traits
    assert smart_wash_params.smart_wash == 5
    assert smart_wash_params.wash_interval == 6


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s7_max_ultra_dock),  # Not in WASH_N_FILL_DOCK_TYPES
        (RoborockDockTypeCode.no_dock),
    ],
)
async def test_unsupported_smart_wash_params(
    smart_wash_params: SmartWashParamsTrait | None, dock_type_code: RoborockDockTypeCode
) -> None:
    """Test successfully refreshing the dock summary."""
    assert smart_wash_params is None

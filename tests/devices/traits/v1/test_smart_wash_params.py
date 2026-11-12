"""Tests for the SmartWashParamsTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockSmartWashModeCode
from roborock.data.v1.v1_code_mappings import (
    RoborockDockTypeCode,
)
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.smart_wash_params import SmartWashParamsTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability

# Saros 10R: wash the mop after every room, interval 1200 s kept for the time mode
SMART_WASH_DATA = [{"smart_wash": 1, "wash_interval": 1200}]
SAROS_10R_DOCK = RoborockDockTypeCode.shell_3s_dock


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
    dock_types_with_capability("is_washable"),
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
    assert smart_wash_params.smart_wash == RoborockDockSmartWashModeCode.by_room
    assert smart_wash_params.wash_interval == 1200


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_washable", expected=False),
)
async def test_unsupported_smart_wash_params(
    smart_wash_params: SmartWashParamsTrait | None, dock_type_code: RoborockDockTypeCode
) -> None:
    """Test successfully refreshing the dock summary."""
    assert smart_wash_params is None


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_refresh_unknown_code(
    smart_wash_params: SmartWashParamsTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that refresh tolerates an unknown smart wash mode code."""
    assert smart_wash_params is not None
    mock_rpc_channel.send_command.side_effect = [[{"smart_wash": 7, "wash_interval": 1200}]]

    await smart_wash_params.refresh()

    assert smart_wash_params.smart_wash == RoborockDockSmartWashModeCode.unknown
    assert smart_wash_params.wash_interval == 1200


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("new_smart_supported", "expected"),
    [
        (False, [RoborockDockSmartWashModeCode.by_time, RoborockDockSmartWashModeCode.by_room]),
        (
            True,
            [
                RoborockDockSmartWashModeCode.by_time,
                RoborockDockSmartWashModeCode.by_room,
                RoborockDockSmartWashModeCode.new_smart,
            ],
        ),
    ],
)
async def test_smart_wash_mode_options(
    device: RoborockDevice,
    smart_wash_params: SmartWashParamsTrait | None,
    dock_type_code: RoborockDockTypeCode,
    new_smart_supported: bool,
    expected: list[RoborockDockSmartWashModeCode],
) -> None:
    """Test that the new smart mode is offered only with its device feature."""
    assert device.v1_properties
    assert smart_wash_params is not None
    device.v1_properties.device_features.is_back_wash_new_smart_supported = new_smart_supported

    assert smart_wash_params.smart_wash_mode_options == expected
    assert smart_wash_params.wash_interval_options == [600, 900, 1200, 1500]


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("mode", "wash_interval"),
    [
        (RoborockDockSmartWashModeCode.by_room, 1200),
        (RoborockDockSmartWashModeCode.by_time, 900),
        (RoborockDockSmartWashModeCode.by_time, 600),
        (RoborockDockSmartWashModeCode.by_time, 1500),
    ],
)
async def test_set_smart_wash_params(
    smart_wash_params: SmartWashParamsTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockSmartWashModeCode,
    wash_interval: int,
) -> None:
    """Test setting an offered smart wash mode and interval."""
    assert smart_wash_params is not None

    await smart_wash_params.set_smart_wash_params(mode, wash_interval)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_SMART_WASH_PARAMS, params={"smart_wash": mode.value, "wash_interval": wash_interval}
    )
    assert smart_wash_params.smart_wash == mode
    assert smart_wash_params.wash_interval == wash_interval


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("mode", "wash_interval"),
    [
        (RoborockDockSmartWashModeCode.new_smart, 1200),
        (RoborockDockSmartWashModeCode.unknown, 1200),
        (RoborockDockSmartWashModeCode.by_time, 1000),
    ],
)
async def test_set_rejects_unoffered(
    device: RoborockDevice,
    smart_wash_params: SmartWashParamsTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockSmartWashModeCode,
    wash_interval: int,
) -> None:
    """Test that a mode or interval the device does not offer is rejected without sending."""
    assert device.v1_properties
    assert smart_wash_params is not None
    device.v1_properties.device_features.is_back_wash_new_smart_supported = False

    with pytest.raises(RoborockUnsupportedFeature):
        await smart_wash_params.set_smart_wash_params(mode, wash_interval)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_set_failure_keeps_state(
    smart_wash_params: SmartWashParamsTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the smart wash params unchanged."""
    assert smart_wash_params is not None
    smart_wash_params.smart_wash = RoborockDockSmartWashModeCode.by_room
    smart_wash_params.wash_interval = 1200
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await smart_wash_params.set_smart_wash_params(RoborockDockSmartWashModeCode.by_time, 900)

    assert smart_wash_params.smart_wash == RoborockDockSmartWashModeCode.by_room
    assert smart_wash_params.wash_interval == 1200

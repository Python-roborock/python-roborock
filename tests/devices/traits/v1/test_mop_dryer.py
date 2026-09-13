"""Tests for the MopDryerTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.mop_dryer import MopDryerTrait
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability

DRYABLE_DOCK = RoborockDockTypeCode.o4_dock

# Captured from a real dock via APP_GET_DRYER_SETTING.
MOP_DRYER_SETTING_DATA = {
    "status": 1,
    "on": {
        "cliff_on": 1000,
        "cliff_off": 1000,
        "count": 10,
        "dry_time": 7200,
        "dry_heating_film_time": 3600,
    },
    "off": {"cliff_on": 500, "cliff_off": 500, "count": 10},
}


@pytest.fixture(name="mop_dryer")
def mop_dryer_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> MopDryerTrait | None:
    """Create a MopDryerTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.mop_dryer


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_dryable"),
)
async def test_mop_dryer_available(mop_dryer: MopDryerTrait | None, dock_type_code: RoborockDockTypeCode) -> None:
    """Test that the trait is available for every dryable dock type."""
    assert mop_dryer is not None


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_dryable", expected=False),
)
async def test_unsupported_mop_dryer(mop_dryer: MopDryerTrait | None, dock_type_code: RoborockDockTypeCode) -> None:
    """Test that the trait is not available for dock types that cannot dry."""
    assert mop_dryer is None


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
async def test_refresh(
    mop_dryer: MopDryerTrait,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test refreshing the mop dryer setting from the device."""
    assert mop_dryer is not None

    mock_rpc_channel.send_command.side_effect = [
        MOP_DRYER_SETTING_DATA,
    ]

    await mop_dryer.refresh()

    mock_rpc_channel.send_command.assert_has_calls([call(RoborockCommand.APP_GET_DRYER_SETTING)])
    assert mop_dryer.is_on is True
    assert mop_dryer.on is not None
    assert mop_dryer.on.dry_time == 7200
    assert mop_dryer.on.dry_heating_film_time == 3600
    assert mop_dryer.off is not None
    assert mop_dryer.off.dry_time is None


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
@pytest.mark.parametrize(
    ("status", "expected_is_on"),
    [
        pytest.param(None, False, id="not_reported"),
        pytest.param(0, False, id="disabled"),
        pytest.param(1, True, id="enabled"),
    ],
)
async def test_is_on(
    mop_dryer: MopDryerTrait,
    dock_type_code: RoborockDockTypeCode,
    status: int | None,
    expected_is_on: bool,
) -> None:
    """Test that is_on reflects the auto mop-drying setting."""
    assert mop_dryer is not None

    mop_dryer.status = status

    assert mop_dryer.is_on is expected_is_on


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
@pytest.mark.parametrize(
    ("method_name", "expected_status", "expected_is_on"),
    [
        pytest.param("enable", 1, True, id="enable"),
        pytest.param("disable", 0, False, id="disable"),
    ],
)
async def test_set_auto_dry(
    mop_dryer: MopDryerTrait,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    method_name: str,
    expected_status: int,
    expected_is_on: bool,
) -> None:
    """Test enabling and disabling auto mop drying."""
    assert mop_dryer is not None

    await getattr(mop_dryer, method_name)()

    mock_rpc_channel.send_command.assert_called_with(
        RoborockCommand.APP_SET_DRYER_SETTING, params={"status": expected_status}
    )
    # The command result is applied optimistically to avoid an extra refresh
    assert mop_dryer.is_on is expected_is_on


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
@pytest.mark.parametrize(
    ("method_name", "expected_status"),
    [
        pytest.param("start_dry", 1, id="start"),
        pytest.param("stop_dry", 0, id="stop"),
    ],
)
async def test_dry_cycle(
    mop_dryer: MopDryerTrait,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    method_name: str,
    expected_status: int,
) -> None:
    """Test starting and stopping a mop drying cycle."""
    assert mop_dryer is not None

    await getattr(mop_dryer, method_name)()

    mock_rpc_channel.send_command.assert_called_with(
        RoborockCommand.APP_SET_DRYER_STATUS, params={"status": expected_status}
    )

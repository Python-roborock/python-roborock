"""Tests for the MopDryerTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.mop_dryer import MopDryerTrait
from roborock.roborock_typing import RoborockCommand
from tests import mock_data
from tests.devices.traits.v1.helpers import dock_types_with_capability

DRYABLE_DOCK = RoborockDockTypeCode.o4_dock


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
@pytest.mark.parametrize(
    ("dry_status", "expected_is_on"),
    [
        pytest.param(None, False, id="not_reported"),
        pytest.param(0, False, id="idle"),
        pytest.param(1, True, id="drying"),
    ],
)
async def test_is_on_reads_status(
    mop_dryer: MopDryerTrait,
    device: RoborockDevice,
    dock_type_code: RoborockDockTypeCode,
    dry_status: int | None,
    expected_is_on: bool,
) -> None:
    """Test that the mop dryer state is read from the device status."""
    assert mop_dryer is not None
    assert device.v1_properties

    device.v1_properties.status.dry_status = dry_status

    assert mop_dryer.is_on is expected_is_on


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
@pytest.mark.parametrize(
    ("method_name", "expected_status"),
    [
        pytest.param("enable", 1, id="enable"),
        pytest.param("disable", 0, id="disable"),
    ],
)
async def test_set_mop_dryer_status(
    mop_dryer: MopDryerTrait,
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    method_name: str,
    expected_status: int,
) -> None:
    """Test starting and stopping the mop dryer sends the right command."""
    assert mop_dryer is not None
    assert device.v1_properties

    await getattr(mop_dryer, method_name)()

    mock_rpc_channel.send_command.assert_called_with(
        RoborockCommand.APP_SET_DRYER_STATUS, params={"status": expected_status}
    )
    # The command result is applied optimistically to avoid an extra refresh
    assert device.v1_properties.status.dry_status == expected_status
    assert mop_dryer.is_on is bool(expected_status)


@pytest.mark.parametrize(
    ("dock_type_code"),
    [(DRYABLE_DOCK)],
)
async def test_refresh_delegates_to_status(
    mop_dryer: MopDryerTrait,
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test refreshing the mop dryer refreshes the status it reads from."""
    assert mop_dryer is not None
    assert device.v1_properties

    mock_rpc_channel.send_command.side_effect = [
        {**mock_data.STATUS, "dry_status": 1},
    ]

    await mop_dryer.refresh()

    mock_rpc_channel.send_command.assert_has_calls([call(RoborockCommand.GET_STATUS)])
    assert device.v1_properties.status.dry_status == 1
    assert mop_dryer.is_on is True

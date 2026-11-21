"""Tests for the CleaningFluidTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import RoborockDockCleaningFluidCode, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.cleaning_fluid import CleaningFluidTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability

SAROS_10R_DOCK = RoborockDockTypeCode.shell_3s_dock


@pytest.fixture(name="cleaning_fluid")
def cleaning_fluid_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CleaningFluidTrait | None:
    """Create a CleaningFluidTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.cleaning_fluid


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_clean_fluid_auto_delivery_supported"),
)
async def test_cleaning_fluid_available(
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is available for docks with cleaning fluid auto-delivery."""
    assert cleaning_fluid is not None


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_clean_fluid_auto_delivery_supported", expected=False),
)
async def test_unsupported_cleaning_fluid(
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for docks without cleaning fluid auto-delivery."""
    assert cleaning_fluid is None


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"status": 1}, RoborockDockCleaningFluidCode.standard),  # Saros 10R
        ({"status": 3}, RoborockDockCleaningFluidCode.large),
        ({"status": 0}, RoborockDockCleaningFluidCode.off),
        ({"status": 2}, RoborockDockCleaningFluidCode.unknown),
    ],
)
async def test_refresh_unknown_code(
    cleaning_fluid: CleaningFluidTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    response: dict[str, int],
    expected: RoborockDockCleaningFluidCode,
) -> None:
    """Test that refresh decodes known codes and tolerates unknown ones."""
    assert cleaning_fluid is not None
    mock_rpc_channel.send_command.side_effect = [response]

    await cleaning_fluid.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_AUTO_DELIVERY_CLEANING_FLUID)
    assert cleaning_fluid.status == expected


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_options(
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test the cleaning fluid amounts offered by the app."""
    assert cleaning_fluid is not None
    assert cleaning_fluid.cleaning_fluid_options == [
        RoborockDockCleaningFluidCode.off,
        RoborockDockCleaningFluidCode.standard,
        RoborockDockCleaningFluidCode.large,
    ]


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [
        (RoborockDockCleaningFluidCode.off, 0),
        (RoborockDockCleaningFluidCode.standard, 1),
        (RoborockDockCleaningFluidCode.large, 3),
    ],
)
async def test_set_cleaning_fluid(
    cleaning_fluid: CleaningFluidTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockCleaningFluidCode,
    expected_code: int,
) -> None:
    """Test setting an offered cleaning fluid amount sends its wire code."""
    assert cleaning_fluid is not None

    await cleaning_fluid.set_cleaning_fluid(mode)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_AUTO_DELIVERY_CLEANING_FLUID, params={"status": expected_code}
    )
    assert cleaning_fluid.status == mode


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_set_rejects_unoffered(
    cleaning_fluid: CleaningFluidTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that an amount the app does not offer is rejected without sending."""
    assert cleaning_fluid is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await cleaning_fluid.set_cleaning_fluid(RoborockDockCleaningFluidCode.unknown)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_set_failure_keeps_state(
    cleaning_fluid: CleaningFluidTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the amount unchanged."""
    assert cleaning_fluid is not None
    cleaning_fluid.status = RoborockDockCleaningFluidCode.standard
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await cleaning_fluid.set_cleaning_fluid(RoborockDockCleaningFluidCode.large)

    assert cleaning_fluid.status == RoborockDockCleaningFluidCode.standard

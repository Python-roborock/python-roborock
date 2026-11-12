"""Tests for the CleaningFluidTrait class."""

from copy import deepcopy
from typing import Any
from unittest.mock import AsyncMock

import pytest

from roborock.data import CleanFluidStatus, HomeData, RoborockDockCleaningFluidCode, RoborockDockTypeCode
from roborock.device_features import NewFeatureStrBit, RoborockDockFeatures
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.cleaning_fluid import CleaningFluidTrait, supports_cleaning_fluid
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability, home_data_with_feature_bit

SAROS_10R_DOCK = RoborockDockTypeCode.shell_3s_dock
PEARL_PLUS_DOCK = RoborockDockTypeCode.pearl_plus_dock
# dss with the cleaning fluid container bits (10-11) at 2: the fluid container is okay (Saros 10R)
DSS_FLUID_OK = 2212
# dss without cleaning fluid container bits (Qrevo MaxV 2)
DSS_NO_FLUID = 165


def _home_data_with_fluid_delivery(supported: bool) -> HomeData:
    """Return home data whose device has the cleaning fluid delivery feature bit set or cleared."""
    return home_data_with_feature_bit(NewFeatureStrBit.CLEAN_FLUID_DELIVERY, supported)


@pytest.fixture(name="trait_home_data")
def trait_home_data_fixture(request: pytest.FixtureRequest) -> HomeData:
    """Default to a robot with cleaning fluid delivery, as the Saros 10R."""
    return deepcopy(getattr(request, "param", _home_data_with_fluid_delivery(True)))


@pytest.fixture(name="status_overrides")
def status_overrides_fixture() -> dict[str, Any]:
    """Default to a robot whose cleaning fluid container is okay."""
    return {"dss": DSS_FLUID_OK}


@pytest.fixture(name="cleaning_fluid")
def cleaning_fluid_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CleaningFluidTrait | None:
    """Create a CleaningFluidTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.cleaning_fluid


@pytest.mark.parametrize(
    ("fluid_delivery", "dock_type", "has_am", "fluid_status", "expected"),
    [
        (True, SAROS_10R_DOCK, None, CleanFluidStatus.okay, True),  # Saros 10R
        (True, RoborockDockTypeCode.o0_dock, None, CleanFluidStatus.okay, True),  # amount page, no dock flag
        (False, PEARL_PLUS_DOCK, None, CleanFluidStatus.okay, True),  # on/off switch
        (False, PEARL_PLUS_DOCK, None, CleanFluidStatus.empty_not_installed, True),  # empty tank still shows it
        (True, PEARL_PLUS_DOCK, None, None, False),  # no fluid container bits (Qrevo MaxV 2)
        (False, RoborockDockTypeCode.o0_dock, None, CleanFluidStatus.okay, False),  # neither robot nor dock deliver
        (True, RoborockDockTypeCode.shell_4s_dock, None, CleanFluidStatus.okay, False),  # multi fluid dock
        (False, RoborockDockTypeCode.k1_dock, True, CleanFluidStatus.okay, True),  # auto-empty variant of a dock
        (False, RoborockDockTypeCode.k1_dock, None, CleanFluidStatus.okay, False),  # variant without auto-empty
    ],
)
def test_supports_cleaning_fluid(
    fluid_delivery: bool,
    dock_type: RoborockDockTypeCode,
    has_am: bool | None,
    fluid_status: CleanFluidStatus | None,
    expected: bool,
) -> None:
    """Test the rules for offering the cleaning fluid setting."""
    dock_features = RoborockDockFeatures.from_dock_type(dock_type, has_am=has_am)

    assert supports_cleaning_fluid(fluid_delivery, dock_features, fluid_status) is expected


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


@pytest.mark.parametrize("trait_home_data", [_home_data_with_fluid_delivery(False)], indirect=True)
@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_clean_fluid_auto_delivery_supported", expected=False),
)
async def test_unsupported_cleaning_fluid(
    trait_home_data: HomeData,
    device: RoborockDevice,
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available when neither the robot nor the dock deliver cleaning fluid."""
    assert device.is_connected
    assert cleaning_fluid is None


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o3_plus_dock])
async def test_available_from_robot_delivery_feature(
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a robot with cleaning fluid delivery gets the trait on any dock."""
    assert cleaning_fluid is not None
    assert cleaning_fluid.cleaning_fluid_options == [
        RoborockDockCleaningFluidCode.off,
        RoborockDockCleaningFluidCode.standard,
        RoborockDockCleaningFluidCode.large,
    ]


@pytest.mark.parametrize("status_overrides", [{"dss": DSS_NO_FLUID}])
@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK, PEARL_PLUS_DOCK])
async def test_unsupported_without_fluid_container_bits(
    device: RoborockDevice,
    cleaning_fluid: CleaningFluidTrait | None,
    status_overrides: dict[str, Any],
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not created when the robot reports no cleaning fluid container."""
    assert device.is_connected
    assert cleaning_fluid is None


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.shell_4s_dock])
async def test_unsupported_on_multi_fluid_dock(
    device: RoborockDevice,
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a multi fluid dock gets no single cleaning fluid control."""
    assert device.is_connected
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


@pytest.mark.parametrize(
    ("trait_home_data", "expected"),
    [
        (
            _home_data_with_fluid_delivery(True),  # Saros 10R: amount page
            [
                RoborockDockCleaningFluidCode.off,
                RoborockDockCleaningFluidCode.standard,
                RoborockDockCleaningFluidCode.large,
            ],
        ),
        (
            _home_data_with_fluid_delivery(False),  # on/off switch
            [RoborockDockCleaningFluidCode.off, RoborockDockCleaningFluidCode.standard],
        ),
    ],
    indirect=["trait_home_data"],
)
@pytest.mark.parametrize(("dock_type_code"), [PEARL_PLUS_DOCK])
async def test_options(
    trait_home_data: HomeData,
    cleaning_fluid: CleaningFluidTrait | None,
    dock_type_code: RoborockDockTypeCode,
    expected: list[RoborockDockCleaningFluidCode],
) -> None:
    """Test that the large amount is offered only by robots with cleaning fluid delivery."""
    assert cleaning_fluid is not None
    assert cleaning_fluid.cleaning_fluid_options == expected


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


@pytest.mark.parametrize("trait_home_data", [_home_data_with_fluid_delivery(False)], indirect=True)
@pytest.mark.parametrize(("dock_type_code"), [PEARL_PLUS_DOCK])
@pytest.mark.parametrize(
    ("mode"),
    [RoborockDockCleaningFluidCode.large, RoborockDockCleaningFluidCode.unknown],
)
async def test_set_rejects_unoffered(
    trait_home_data: HomeData,
    cleaning_fluid: CleaningFluidTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockCleaningFluidCode,
) -> None:
    """Test that an amount the robot does not offer is rejected without sending."""
    assert cleaning_fluid is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await cleaning_fluid.set_cleaning_fluid(mode)

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

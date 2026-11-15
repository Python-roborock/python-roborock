"""Tests for the collision avoidance traits."""

from copy import deepcopy
from unittest.mock import AsyncMock, call

import pytest

from roborock.data import CollisionAvoidanceMode, HomeData
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.collision_avoidance import CollisionAvoidanceModeTrait, CollisionAvoidanceTrait
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

COLLISION_FEATURE = "0000000008002041"
TWO_LEVEL_COLLISION_FEATURE = "00400000000000000000000008002041"
TWO_LEVEL_ONLY_COLLISION_FEATURE = "00400000000000000000000000002041"
NO_COLLISION_FEATURE = "0000000000002041"


def _home_data(new_feature_set: str) -> HomeData:
    raw = deepcopy(mock_data.HOME_DATA_RAW)
    raw["devices"][0]["newFeatureSet"] = new_feature_set
    return HomeData.from_dict(raw)


@pytest.fixture(name="collision_avoidance")
def collision_avoidance_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CollisionAvoidanceTrait | None:
    """Return the trait created by feature discovery."""
    assert device.v1_properties
    return device.v1_properties.collision_avoidance


@pytest.fixture(name="collision_avoidance_mode")
def collision_avoidance_mode_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CollisionAvoidanceModeTrait | None:
    """Return the mode trait created by feature discovery."""
    assert device.v1_properties
    return device.v1_properties.collision_avoidance_mode


@pytest.mark.parametrize(
    ("trait_home_data", "expected_switch", "expected_mode"),
    [
        (_home_data(COLLISION_FEATURE), True, False),
        (_home_data(TWO_LEVEL_COLLISION_FEATURE), False, True),
        (_home_data(TWO_LEVEL_ONLY_COLLISION_FEATURE), False, True),
        (_home_data(NO_COLLISION_FEATURE), False, False),
    ],
    indirect=["trait_home_data"],
)
async def test_discovery(
    collision_avoidance: CollisionAvoidanceTrait | None,
    collision_avoidance_mode: CollisionAvoidanceModeTrait | None,
    trait_home_data: HomeData,
    expected_switch: bool,
    expected_mode: bool,
) -> None:
    """On/off devices get the switch and two-level devices get the mode trait."""
    assert (collision_avoidance is not None) is expected_switch
    assert (collision_avoidance_mode is not None) is expected_mode


@pytest.mark.parametrize("trait_home_data", [_home_data(COLLISION_FEATURE)], indirect=True)
@pytest.mark.parametrize(("response", "expected"), [({"status": 1}, True), ({"status": 0}, False)])
async def test_refresh(
    collision_avoidance: CollisionAvoidanceTrait | None,
    trait_home_data: HomeData,
    mock_rpc_channel: AsyncMock,
    response: dict[str, int],
    expected: bool,
) -> None:
    """Refreshing reads the setting from the device."""
    assert collision_avoidance is not None
    mock_rpc_channel.send_command.return_value = response

    await collision_avoidance.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_COLLISION_AVOID_STATUS)
    assert collision_avoidance.is_on is expected


@pytest.mark.parametrize("trait_home_data", [_home_data(COLLISION_FEATURE)], indirect=True)
async def test_enable_and_disable(
    collision_avoidance: CollisionAvoidanceTrait | None,
    trait_home_data: HomeData,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Enabling and disabling send the status value and update the trait."""
    assert collision_avoidance is not None

    await collision_avoidance.enable()
    assert collision_avoidance.is_on
    await collision_avoidance.disable()
    assert not collision_avoidance.is_on

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.SET_COLLISION_AVOID_STATUS, params={"status": 1}),
        call(RoborockCommand.SET_COLLISION_AVOID_STATUS, params={"status": 0}),
    ]


@pytest.mark.parametrize("trait_home_data", [_home_data(TWO_LEVEL_COLLISION_FEATURE)], indirect=True)
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"status": 1}, CollisionAvoidanceMode.high_coverage),
        ({"status": 2}, CollisionAvoidanceMode.less_collision),
        ({"status": 0}, CollisionAvoidanceMode.unknown),
    ],
)
async def test_mode_refresh(
    collision_avoidance_mode: CollisionAvoidanceModeTrait | None,
    trait_home_data: HomeData,
    mock_rpc_channel: AsyncMock,
    response: dict[str, int],
    expected: CollisionAvoidanceMode,
) -> None:
    """Refreshing decodes the mode and keeps the raw value."""
    assert collision_avoidance_mode is not None
    mock_rpc_channel.send_command.return_value = response

    await collision_avoidance_mode.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_COLLISION_AVOID_STATUS)
    assert collision_avoidance_mode.mode is expected
    assert collision_avoidance_mode.status == response["status"]


@pytest.mark.parametrize("trait_home_data", [_home_data(TWO_LEVEL_COLLISION_FEATURE)], indirect=True)
@pytest.mark.parametrize(
    ("mode", "expected_status"),
    [(CollisionAvoidanceMode.high_coverage, 1), (CollisionAvoidanceMode.less_collision, 2)],
)
async def test_set_collision_avoidance_mode(
    collision_avoidance_mode: CollisionAvoidanceModeTrait | None,
    trait_home_data: HomeData,
    mock_rpc_channel: AsyncMock,
    mode: CollisionAvoidanceMode,
    expected_status: int,
) -> None:
    """Setting the mode sends its value and updates the trait."""
    assert collision_avoidance_mode is not None

    await collision_avoidance_mode.set_collision_avoidance_mode(mode)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_COLLISION_AVOID_STATUS, params={"status": expected_status}
    )
    assert collision_avoidance_mode.mode is mode


@pytest.mark.parametrize("trait_home_data", [_home_data(TWO_LEVEL_COLLISION_FEATURE)], indirect=True)
async def test_set_collision_avoidance_mode_unknown(
    collision_avoidance_mode: CollisionAvoidanceModeTrait | None,
    trait_home_data: HomeData,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Setting the unknown mode is rejected without sending a command."""
    assert collision_avoidance_mode is not None
    mock_rpc_channel.send_command.return_value = {"status": 0}
    await collision_avoidance_mode.refresh()
    assert collision_avoidance_mode.mode is CollisionAvoidanceMode.unknown
    mock_rpc_channel.send_command.reset_mock()

    with pytest.raises(RoborockUnsupportedFeature):
        await collision_avoidance_mode.set_collision_avoidance_mode(CollisionAvoidanceMode.unknown)

    mock_rpc_channel.send_command.assert_not_called()
    assert collision_avoidance_mode.status == 0

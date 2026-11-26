"""Tests for the CarpetCleanModeTrait class."""

from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct, UserData
from roborock.data.v1 import CarpetCleanMode, CarpetMode
from roborock.devices.cache import InMemoryCache
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.devices.traits.v1.carpet_clean_mode import CarpetCleanModeTrait
from roborock.exceptions import RoborockTimeout, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from roborock.testing import DEFAULT_APP_INIT, FakeRoborockCloud, V1VacuumSimulator
from tests import mock_data

SAROS_10R, SAROS_10R_PRODUCT = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"]
S5E = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s5e.json"][0]
SAROS_FEATURE_STR = SAROS_10R.new_feature_set or ""


@pytest.fixture(name="device_info")
def device_info_fixture() -> HomeDataDevice:
    """Use the Saros 10R, which supports every carpet mode."""
    return SAROS_10R


@pytest.fixture(name="carpet_clean_mode_trait")
def carpet_clean_mode_trait_fixture(
    device: RoborockDevice, discover_features_fixture: None
) -> CarpetCleanModeTrait | None:
    """Return the discovered CarpetCleanModeTrait from the device."""
    assert device.v1_properties
    return device.v1_properties.carpet_clean_mode


async def _refresh(
    trait: CarpetCleanModeTrait | None, rpc: AsyncMock, clean_mode: int, switch_status: int
) -> CarpetCleanModeTrait:
    assert trait is not None
    rpc.send_command.side_effect = [[{"carpet_clean_mode": clean_mode}], [{"switch_status": switch_status}]]
    await trait.refresh()
    return trait


@pytest.mark.parametrize(
    ("clean_mode", "switch_status", "mode", "carpet_first", "cross"),
    [
        (0, 0, CarpetMode.AVOID, False, False),
        (1, 0, CarpetMode.VACUUM_ONLY, False, False),
        (2, 0, CarpetMode.VAC_AND_MOP, False, False),
        (3, 19, CarpetMode.VACUUM_ONLY, False, False),
        (3, 8, CarpetMode.VACUUM_ONLY, True, False),
        (3, 32, CarpetMode.CROSS, False, True),
        (0, 40, CarpetMode.CROSS, True, True),
        (7, 0, None, False, False),
    ],
)
async def test_refresh_reads_state(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    clean_mode: int,
    switch_status: int,
    mode: CarpetMode | None,
    carpet_first: bool,
    cross: bool,
) -> None:
    """The clean mode and the switch status bits (0x08, 0x20) are read with two commands; cross wins."""
    trait = await _refresh(carpet_clean_mode_trait, mock_rpc_channel, clean_mode, switch_status)

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.GET_CARPET_CLEAN_MODE),
        call(RoborockCommand.GET_PROP, params=["get_status"]),
    ]
    assert trait.mode is mode
    assert trait.carpet_first is carpet_first
    assert trait.cross_carpet is cross
    # Carpet first and side brush lift are only accepted in Vacuum Only.
    assert trait.vacuum_only_settings_available is (mode is CarpetMode.VACUUM_ONLY)


async def test_switch_status_failure_keeps_flags(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None, mock_rpc_channel: AsyncMock
) -> None:
    """A failing get_prop leaves the known switch flags untouched and the mode is still read."""
    trait = await _refresh(carpet_clean_mode_trait, mock_rpc_channel, 3, 32)

    mock_rpc_channel.send_command.side_effect = [[{"carpet_clean_mode": 2}], RoborockTimeout("timeout")]
    await trait.refresh()

    assert trait.carpet_clean_mode is CarpetCleanMode.vac_and_mop
    assert trait.cross_carpet is True


async def test_options_saros(carpet_clean_mode_trait: CarpetCleanModeTrait | None) -> None:
    assert carpet_clean_mode_trait is not None
    assert carpet_clean_mode_trait.options == [
        CarpetMode.AVOID,
        CarpetMode.VAC_AND_MOP,
        CarpetMode.VACUUM_ONLY,
        CarpetMode.CROSS,
    ]


@pytest.mark.parametrize(
    ("features", "missing"),
    [
        ({"is_carpet_custom_clean_supported": False}, CarpetMode.CROSS),
        (
            {"is_self_adaption_carpet_supported": False, "is_dynamic_adaption_carpet_supported": False},
            CarpetMode.VACUUM_ONLY,
        ),
    ],
)
async def test_options_gated_by_features(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None,
    device: RoborockDevice,
    features: dict[str, bool],
    missing: CarpetMode,
) -> None:
    assert carpet_clean_mode_trait is not None
    assert device.v1_properties
    for name, value in features.items():
        setattr(device.v1_properties.device_features, name, value)

    assert missing not in carpet_clean_mode_trait.options


@pytest.mark.parametrize("device_info", [S5E])
async def test_trait_absent_without_carpet_support(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None, device_info: HomeDataDevice
) -> None:
    assert carpet_clean_mode_trait is None


@pytest.mark.parametrize("products", [[replace(SAROS_10R_PRODUCT, model="roborock.vacuum.a38")]])
async def test_trait_absent_on_tanos_s_lite_in_us(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None, device: RoborockDevice, products: list[HomeDataProduct]
) -> None:
    """The fixtures report the US region, where the TanosSLite has no carpet settings."""
    assert device.v1_properties
    assert device.v1_properties.device_features.is_carpet_supported
    assert carpet_clean_mode_trait is None


def _answer_reads(rpc: AsyncMock) -> None:
    """Answer the refresh reads and accept every write."""

    async def send_command(command: RoborockCommand, params: object = None) -> object:
        if command is RoborockCommand.GET_CARPET_CLEAN_MODE:
            return [{"carpet_clean_mode": 3}]
        if command is RoborockCommand.GET_PROP:
            return [{"switch_status": 0}]
        return "ok"

    rpc.send_command.side_effect = send_command


_SET_MODE = RoborockCommand.SET_CARPET_CLEAN_MODE
_SET_CROSS = RoborockCommand.APP_SET_CROSS_CARPET_CLEANING_STATUS


@pytest.mark.parametrize(
    ("mode", "features", "expected"),
    [
        (CarpetMode.AVOID, {}, [call(_SET_MODE, params={"carpet_clean_mode": 0})]),
        (CarpetMode.VAC_AND_MOP, {}, [call(_SET_MODE, params={"carpet_clean_mode": 2})]),
        (
            CarpetMode.VACUUM_ONLY,
            {"is_dynamic_adaption_carpet_supported": True},
            [call(_SET_MODE, params={"carpet_clean_mode": 3}), call(_SET_CROSS, params={"status": 0})],
        ),
        (
            CarpetMode.VACUUM_ONLY,
            {"is_dynamic_adaption_carpet_supported": False, "is_self_adaption_carpet_supported": True},
            [call(_SET_MODE, params={"carpet_clean_mode": 1}), call(_SET_CROSS, params={"status": 0})],
        ),
        (
            CarpetMode.VACUUM_ONLY,
            {"is_carpet_custom_clean_supported": False},
            [call(_SET_MODE, params={"carpet_clean_mode": 1})],
        ),
        (CarpetMode.CROSS, {}, [call(_SET_CROSS, params={"status": 1})]),
    ],
    ids=["avoid", "vac_and_mop", "vacuum_only_dynamic", "vacuum_only_self", "vacuum_only_no_custom_clean", "cross"],
)
async def test_set_mode_sends_commands(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device: RoborockDevice,
    mode: CarpetMode,
    features: dict[str, bool],
    expected: list,
) -> None:
    """Each mode sends exactly its own writes, then refreshes."""
    assert carpet_clean_mode_trait is not None
    assert device.v1_properties
    for name, value in features.items():
        setattr(device.v1_properties.device_features, name, value)
    _answer_reads(mock_rpc_channel)

    await carpet_clean_mode_trait.set_mode(mode)

    assert mock_rpc_channel.send_command.call_args_list == [
        *expected,
        call(RoborockCommand.GET_CARPET_CLEAN_MODE),
        call(RoborockCommand.GET_PROP, params=["get_status"]),
    ]


async def test_set_unoffered_mode_raises_and_sends_nothing(
    carpet_clean_mode_trait: CarpetCleanModeTrait | None, mock_rpc_channel: AsyncMock, device: RoborockDevice
) -> None:
    assert carpet_clean_mode_trait is not None
    assert device.v1_properties
    device.v1_properties.device_features.is_carpet_custom_clean_supported = False

    with pytest.raises(RoborockUnsupportedFeature):
        await carpet_clean_mode_trait.set_mode(CarpetMode.CROSS)

    mock_rpc_channel.send_command.assert_not_called()


async def test_set_mode_round_trip_with_simulator() -> None:
    """Writes land in the simulator and the refreshed trait reports them, including cross clearing."""
    sim = V1VacuumSimulator(
        duid="saros_carpet",
        app_init=replace(
            DEFAULT_APP_INIT, new_feature_info_str=SAROS_FEATURE_STR, new_feature_info=int(SAROS_FEATURE_STR, 16)
        ),
    )
    cloud = FakeRoborockCloud()
    cloud.add_device(sim)
    with cloud.patch_device_manager():
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=UserData.from_dict(mock_data.USER_DATA)),
            cache=InMemoryCache(),
        )
        device = (await manager.get_devices())[0]
    assert device.v1_properties
    trait = device.v1_properties.carpet_clean_mode
    assert trait is not None

    await trait.set_mode(CarpetMode.CROSS)
    assert trait.mode is CarpetMode.CROSS

    await trait.set_mode(CarpetMode.VACUUM_ONLY)
    assert trait.mode is CarpetMode.VACUUM_ONLY
    assert trait.cross_carpet is False

    await trait.set_mode(CarpetMode.CROSS)
    await trait.set_mode(CarpetMode.AVOID)
    assert trait.mode is CarpetMode.AVOID
    assert trait.cross_carpet is False

    await trait.set_mode(CarpetMode.CROSS)
    await trait.set_mode(CarpetMode.VAC_AND_MOP)
    assert trait.mode is CarpetMode.VAC_AND_MOP

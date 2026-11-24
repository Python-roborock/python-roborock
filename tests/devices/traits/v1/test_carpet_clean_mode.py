"""Tests for the CarpetCleanModeTrait class."""

from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct
from roborock.data.v1 import CarpetCleanMode, CarpetMode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.carpet_clean_mode import CarpetCleanModeTrait
from roborock.exceptions import RoborockTimeout
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

SAROS_10R, SAROS_10R_PRODUCT = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"]
S5E = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s5e.json"][0]


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

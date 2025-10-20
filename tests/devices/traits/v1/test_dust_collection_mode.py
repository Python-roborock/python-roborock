"""Tests for the DustCollectionModeTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockDustCollectionModeCode, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.dust_collection_mode import DustCollectionModeTrait
from roborock.roborock_typing import RoborockCommand

DUST_COLLECTION_MODE_DATA = [{"mode": 2}]


@pytest.fixture(name="dust_collection_mode")
def dust_collection_mode_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> DustCollectionModeTrait | None:
    """Create a DustCollectionModeTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.dust_collection_mode


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s7_max_ultra_dock),
        (RoborockDockTypeCode.s8_dock),
        (RoborockDockTypeCode.p10_dock),
        (RoborockDockTypeCode.qrevo_s_dock),
    ],
)
async def test_dust_collection_mode_available(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test successfully refreshing the dust collection mode."""
    assert dust_collection_mode is not None

    mock_rpc_channel.send_command.side_effect = [
        DUST_COLLECTION_MODE_DATA,
    ]

    await dust_collection_mode.refresh()

    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_DUST_COLLECTION_MODE),
        ]
    )

    assert dust_collection_mode.mode == RoborockDockDustCollectionModeCode.balanced


@pytest.mark.parametrize(("dock_type_code"), [(RoborockDockTypeCode.no_dock)])
async def test_unsupported_dust_collection_mode(
    dust_collection_mode: DustCollectionModeTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for unsupported dock types."""
    assert dust_collection_mode is None

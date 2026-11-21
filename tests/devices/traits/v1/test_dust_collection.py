"""Tests for the DustCollectionTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import HomeDataDevice, RoborockDockDustCollectionFrequencyCode, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.dust_collection import DustCollectionTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests import mock_data
from tests.devices.traits.v1.helpers import dock_types_with_capability

# Saros 10R supports the three-level auto-empty frequency (new feature string bit 53).
SAROS_10R = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"][0]
# The S7 MaxV and Q Revo (Pearl) fixtures lack bit 53, so auto-empty is only on or off.
S7_MAXV = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s7_maxv.json"][0]
Q_REVO = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_q_revo.json"][0]

ON_OFF = [RoborockDockDustCollectionFrequencyCode.off, RoborockDockDustCollectionFrequencyCode.balanced]
THREE_LEVELS = [*ON_OFF, RoborockDockDustCollectionFrequencyCode.high]


@pytest.fixture(name="device_info")
def saros_10r_device_info() -> HomeDataDevice:
    """Default to a device that supports the three-level auto-empty frequency."""
    return SAROS_10R


@pytest.fixture(name="dust_collection")
def dust_collection_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> DustCollectionTrait | None:
    """Create a DustCollectionTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.dust_collection


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable"),
)
async def test_dust_collection_available(
    dust_collection: DustCollectionTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is available for collecting docks."""
    assert dust_collection is not None


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable", expected=False),
)
async def test_unsupported_dust_collection(
    dust_collection: DustCollectionTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for unsupported dock types."""
    assert dust_collection is None


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("device_info", "expected"),
    [(SAROS_10R, THREE_LEVELS), (S7_MAXV, ON_OFF), (Q_REVO, ON_OFF)],
    ids=["saros_10r", "s7_maxv", "pearl"],
)
async def test_options(
    dust_collection: DustCollectionTrait | None,
    dock_type_code: RoborockDockTypeCode,
    device_info: HomeDataDevice,
    expected: list[RoborockDockDustCollectionFrequencyCode],
) -> None:
    """Test that every collecting dock gets the trait, with options depending on bit 53."""
    assert dust_collection is not None
    assert dust_collection.frequency_options == expected


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"status": 2}, RoborockDockDustCollectionFrequencyCode.high),  # Saros 10R
        ({"status": 0}, RoborockDockDustCollectionFrequencyCode.off),
        ({"status": 7}, RoborockDockDustCollectionFrequencyCode.unknown),
    ],
)
async def test_refresh_unknown_code(
    dust_collection: DustCollectionTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    response: dict[str, int],
    expected: RoborockDockDustCollectionFrequencyCode,
) -> None:
    """Test that refresh decodes known codes and tolerates unknown ones."""
    assert dust_collection is not None
    mock_rpc_channel.send_command.side_effect = [response]

    await dust_collection.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DUST_COLLECTION_SWITCH_STATUS)
    assert dust_collection.status == expected


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(("frequency"), THREE_LEVELS)
async def test_set_frequency(
    dust_collection: DustCollectionTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    frequency: RoborockDockDustCollectionFrequencyCode,
) -> None:
    """Test setting an offered auto-empty frequency."""
    assert dust_collection is not None

    await dust_collection.set_frequency(frequency)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_DUST_COLLECTION_SWITCH_STATUS, params={"status": frequency.value}
    )
    assert dust_collection.status == frequency


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("device_info", "frequency"),
    [
        (SAROS_10R, RoborockDockDustCollectionFrequencyCode.unknown),
        (S7_MAXV, RoborockDockDustCollectionFrequencyCode.high),
    ],
    ids=["unknown", "high_without_bit_53"],
)
async def test_set_rejects_unoffered(
    dust_collection: DustCollectionTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    device_info: HomeDataDevice,
    frequency: RoborockDockDustCollectionFrequencyCode,
) -> None:
    """Test that a frequency the device does not offer is rejected without sending."""
    assert dust_collection is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await dust_collection.set_frequency(frequency)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_set_failure_keeps_state(
    dust_collection: DustCollectionTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the frequency unchanged."""
    assert dust_collection is not None
    dust_collection.status = RoborockDockDustCollectionFrequencyCode.high
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await dust_collection.set_frequency(RoborockDockDustCollectionFrequencyCode.off)

    assert dust_collection.status == RoborockDockDustCollectionFrequencyCode.high


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(("device_info"), [SAROS_10R, Q_REVO], ids=["saros_10r", "pearl"])
@pytest.mark.parametrize(
    ("method_name", "command"),
    [
        ("start_dust_collection", RoborockCommand.APP_START_COLLECT_DUST),
        ("stop_dust_collection", RoborockCommand.APP_STOP_COLLECT_DUST),
    ],
)
async def test_dust_collection_actions(
    dust_collection: DustCollectionTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    device_info: HomeDataDevice,
    method_name: str,
    command: RoborockCommand,
) -> None:
    """Test manual dust collection on every collecting dock, including Pearl products."""
    assert dust_collection is not None

    await getattr(dust_collection, method_name)()

    mock_rpc_channel.send_command.assert_called_once_with(command)

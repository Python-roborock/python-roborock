"""Tests for the DustCollectionFrequencyTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import RoborockDockDustCollectionFrequencyCode, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.dust_collection_frequency import DustCollectionFrequencyTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability


@pytest.fixture(name="dust_collection_frequency")
def dust_collection_frequency_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> DustCollectionFrequencyTrait | None:
    """Create a DustCollectionFrequencyTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.dust_collection_frequency


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable"),
)
async def test_dust_collection_frequency_available(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is available for collecting docks."""
    assert dust_collection_frequency is not None


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable", expected=False),
)
async def test_unsupported_dust_collection_frequency(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for unsupported dock types."""
    assert dust_collection_frequency is None


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
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    response: dict[str, int],
    expected: RoborockDockDustCollectionFrequencyCode,
) -> None:
    """Test that refresh decodes known codes and tolerates unknown ones."""
    assert dust_collection_frequency is not None
    mock_rpc_channel.send_command.side_effect = [response]

    await dust_collection_frequency.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DUST_COLLECTION_SWITCH_STATUS)
    assert dust_collection_frequency.status == expected


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_options(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test the auto-empty frequencies offered by the app."""
    assert dust_collection_frequency is not None
    assert dust_collection_frequency.frequency_options == [
        RoborockDockDustCollectionFrequencyCode.off,
        RoborockDockDustCollectionFrequencyCode.balanced,
        RoborockDockDustCollectionFrequencyCode.high,
    ]


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("frequency"),
    [
        RoborockDockDustCollectionFrequencyCode.off,
        RoborockDockDustCollectionFrequencyCode.balanced,
        RoborockDockDustCollectionFrequencyCode.high,
    ],
)
async def test_set_frequency(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    frequency: RoborockDockDustCollectionFrequencyCode,
) -> None:
    """Test setting an offered auto-empty frequency."""
    assert dust_collection_frequency is not None

    await dust_collection_frequency.set_frequency(frequency)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_DUST_COLLECTION_SWITCH_STATUS, params={"status": frequency.value}
    )
    assert dust_collection_frequency.status == frequency


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_set_rejects_unoffered(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a frequency the app does not offer is rejected without sending."""
    assert dust_collection_frequency is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await dust_collection_frequency.set_frequency(RoborockDockDustCollectionFrequencyCode.unknown)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_set_failure_keeps_state(
    dust_collection_frequency: DustCollectionFrequencyTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the frequency unchanged."""
    assert dust_collection_frequency is not None
    dust_collection_frequency.status = RoborockDockDustCollectionFrequencyCode.high
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await dust_collection_frequency.set_frequency(RoborockDockDustCollectionFrequencyCode.off)

    assert dust_collection_frequency.status == RoborockDockDustCollectionFrequencyCode.high

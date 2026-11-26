"""Tests for the CleanSequenceTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import HomeDataDevice
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.clean_sequence import CleanSequenceTrait
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

S5E = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s5e.json"][0]


@pytest.fixture(name="clean_sequence_trait")
def clean_sequence_trait_fixture(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CleanSequenceTrait | None:
    """Return the discovered CleanSequenceTrait from the device."""
    assert device.v1_properties
    return device.v1_properties.clean_sequence


def test_requires_feature() -> None:
    """The trait is only created on devices that report order cleaning (robot feature 123)."""
    assert CleanSequenceTrait.requires_feature == "is_order_clean_supported"


@pytest.mark.parametrize("device_info", [S5E])
async def test_refresh(
    clean_sequence_trait: CleanSequenceTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """The response is the list of segment ids in cleaning order."""
    assert clean_sequence_trait is not None
    mock_rpc_channel.send_command.side_effect = [[8, 3, 7, 10, 1, 9]]

    await clean_sequence_trait.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CLEAN_SEQUENCE)
    assert clean_sequence_trait.rooms == [8, 3, 7, 10, 1, 9]


@pytest.mark.parametrize("device_info", [S5E])
@pytest.mark.parametrize("response", [{"unexpected": "shape"}, ["7"], [7, None]])
async def test_refresh_bad_format(
    clean_sequence_trait: CleanSequenceTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
    response: object,
) -> None:
    """A response that is not a list of segment ids raises a parsing error."""
    assert clean_sequence_trait is not None
    mock_rpc_channel.send_command.side_effect = [response]

    with pytest.raises(RoborockParsingException):
        await clean_sequence_trait.refresh()


@pytest.mark.parametrize("device_info", [S5E])
async def test_set_order(
    clean_sequence_trait: CleanSequenceTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """set_order sends the list as is and updates the trait."""
    assert clean_sequence_trait is not None
    mock_rpc_channel.send_command.side_effect = [["ok"]]

    await clean_sequence_trait.set_order([7, 8, 3, 10, 1, 9])

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CLEAN_SEQUENCE, params=[7, 8, 3, 10, 1, 9]
    )
    assert clean_sequence_trait.rooms == [7, 8, 3, 10, 1, 9]


@pytest.mark.parametrize("device_info", [S5E])
@pytest.mark.parametrize("rooms", [[], [7, 7]])
async def test_set_order_rejects_bad_input(
    clean_sequence_trait: CleanSequenceTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
    rooms: list[int],
) -> None:
    """An empty list or a repeated room is refused before anything is sent."""
    assert clean_sequence_trait is not None

    with pytest.raises(ValueError):
        await clean_sequence_trait.set_order(rooms)
    mock_rpc_channel.send_command.assert_not_called()

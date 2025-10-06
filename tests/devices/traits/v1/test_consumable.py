"""Tests for the DoNotDisturbTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.consumeable import ConsumableAttribute, ConsumableTrait
from roborock.roborock_typing import RoborockCommand

CONSUMABLE_DATA = [
    {
        "main_brush_work_time": 879348,
        "side_brush_work_time": 707618,
        "filter_work_time": 738722,
        "filter_element_work_time": 0,
        "sensor_dirty_time": 455517,
    }
]


@pytest.fixture
def consumable_trait(device: RoborockDevice) -> ConsumableTrait:
    """Create a ConsumableTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.consumables


async def test_get_consumable_data_success(consumable_trait: ConsumableTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test successfully getting consumable data."""
    # Setup mock to return the sample consumable data
    mock_rpc_channel.send_command.return_value = CONSUMABLE_DATA

    # Call the method
    await consumable_trait.refresh()
    # Verify the result
    assert consumable_trait.main_brush_work_time == 879348
    assert consumable_trait.side_brush_work_time == 707618
    assert consumable_trait.filter_work_time == 738722
    assert consumable_trait.filter_element_work_time == 0
    assert consumable_trait.sensor_dirty_time == 455517

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CONSUMABLE)


@pytest.mark.parametrize(
    ("consumable", "reset_param"),
    [
        (ConsumableAttribute.MAIN_BRUSH_WORK_TIME, "main_brush_work_time"),
        (ConsumableAttribute.SIDE_BRUSH_WORK_TIME, "side_brush_work_time"),
        (ConsumableAttribute.FILTER_WORK_TIME, "filter_work_time"),
        (ConsumableAttribute.SENSOR_DIRTY_TIME, "sensor_dirty_time"),
    ],
)
async def test_reset_consumable_data(
    consumable_trait: ConsumableTrait,
    mock_rpc_channel: AsyncMock,
    consumable: ConsumableAttribute,
    reset_param: str,
) -> None:
    """Test successfully resetting consumable data."""
    # Call the method
    await consumable_trait.reset_consumable(consumable)

    # Verify the RPC call was made correctly with expected parameters
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.RESET_CONSUMABLE, params=[reset_param])


#

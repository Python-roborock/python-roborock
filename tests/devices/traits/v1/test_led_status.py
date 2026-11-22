"""Tests for the LedStatusTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.led_status import LedStatusTrait
from roborock.exceptions import RoborockParsingException


@pytest.fixture(name="led_status")
def led_status_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> LedStatusTrait:
    """Create a LedStatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    assert device.v1_properties.led_status
    return device.v1_properties.led_status


async def test_refresh_led_status_empty_list_keeps_state(
    led_status: LedStatusTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """An empty reply raises a parsing error and keeps the previous status."""
    mock_rpc_channel.send_command.return_value = [1]
    await led_status.refresh()
    mock_rpc_channel.send_command.return_value = []

    with pytest.raises(
        RoborockParsingException,
        match=r"Failed to parse GET_LED_STATUS response for LedStatusTrait. Payload: \[\].*ValueError.*",
    ):
        await led_status.refresh()

    assert led_status.status == 1

"""Tests for B01 Q10 status trait."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXDeviceCleanTask,
    YXDeviceState,
    YXDeviceWorkMode,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.status import StatusTrait
from roborock.roborock_message import RoborockMessage
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="q10_api")
def q10_api_fixture(fake_channel: FakeChannel) -> Q10PropertiesApi:
    return Q10PropertiesApi(fake_channel)  # type: ignore[arg-type]


@pytest.fixture(name="status_trait")
def status_trait_fixture(q10_api: Q10PropertiesApi) -> StatusTrait:
    return q10_api.status


async def test_status_refresh(
    status_trait: StatusTrait,
    fake_channel: FakeChannel,
) -> None:
    """Test refreshing status from device."""
    # Simulate device response with status data
    response_data: dict[B01_Q10_DP, Any] = {
        B01_Q10_DP.STATUS: 2,  # sleep_state
        B01_Q10_DP.BATTERY: 91,
        B01_Q10_DP.FUN_LEVEL: 8,  # custom
        B01_Q10_DP.WATER_LEVEL: 1,  # medium
        B01_Q10_DP.CLEAN_MODE: 2,  # standard
        B01_Q10_DP.CLEAN_TASK_TYPE: 0,  # unknown
        B01_Q10_DP.CLEANING_PROGRESS: 75,
    }

    # Mock send_decoded_command to return response data
    with patch("roborock.devices.traits.b01.q10.status.send_decoded_command") as mock_send:
        mock_send.return_value = response_data
        result = await status_trait.refresh()

    assert result == response_data
    assert status_trait.data == response_data


async def test_status_properties(
    status_trait: StatusTrait,
    fake_channel: FakeChannel,
) -> None:
    """Test status property accessors."""
    status_trait._data = {
        B01_Q10_DP.STATUS: 2,  # sleep_state
        B01_Q10_DP.BATTERY: 91,
        B01_Q10_DP.FUN_LEVEL: 8,  # custom
        B01_Q10_DP.WATER_LEVEL: 1,  # medium
        B01_Q10_DP.CLEAN_MODE: 2,  # standard
        B01_Q10_DP.CLEAN_TASK_TYPE: 0,  # unknown
        B01_Q10_DP.CLEANING_PROGRESS: 75,
    }

    assert status_trait.state_code == 2
    assert status_trait.state == YXDeviceState.SLEEP_STATE
    assert status_trait.battery == 91
    assert status_trait.fan_level == YXFanLevel.CUSTOM
    assert status_trait.water_level == YXWaterLevel.MEDIUM
    assert status_trait.clean_mode == YXDeviceWorkMode.STANDARD
    assert status_trait.clean_task == YXDeviceCleanTask.UNKNOWN
    assert status_trait.cleaning_progress == 75


async def test_status_properties_empty(
    status_trait: StatusTrait,
) -> None:
    """Test status properties when no data is available."""
    assert status_trait.state_code is None
    assert status_trait.state is None
    assert status_trait.battery is None
    assert status_trait.fan_level is None
    assert status_trait.water_level is None
    assert status_trait.clean_mode is None
    assert status_trait.clean_task is None
    assert status_trait.cleaning_progress is None


async def test_status_enum_mappings(
    status_trait: StatusTrait,
) -> None:
    """Test all enum mappings for status values."""
    test_cases = [
        (B01_Q10_DP.STATUS, 2, YXDeviceState.SLEEP_STATE, "state"),
        (B01_Q10_DP.STATUS, 3, YXDeviceState.STANDBY_STATE, "state"),
        (B01_Q10_DP.STATUS, 5, YXDeviceState.CLEANING_STATE, "state"),
        (B01_Q10_DP.FUN_LEVEL, 1, YXFanLevel.QUIET, "fan_level"),
        (B01_Q10_DP.FUN_LEVEL, 2, YXFanLevel.NORMAL, "fan_level"),
        (B01_Q10_DP.FUN_LEVEL, 3, YXFanLevel.STRONG, "fan_level"),
        (B01_Q10_DP.FUN_LEVEL, 4, YXFanLevel.MAX, "fan_level"),
        (B01_Q10_DP.FUN_LEVEL, 8, YXFanLevel.CUSTOM, "fan_level"),
        (B01_Q10_DP.WATER_LEVEL, 0, YXWaterLevel.LOW, "water_level"),
        (B01_Q10_DP.WATER_LEVEL, 1, YXWaterLevel.MEDIUM, "water_level"),
        (B01_Q10_DP.WATER_LEVEL, 2, YXWaterLevel.HIGH, "water_level"),
        (B01_Q10_DP.CLEAN_MODE, 1, YXDeviceWorkMode.QUIET, "clean_mode"),
        (B01_Q10_DP.CLEAN_MODE, 2, YXDeviceWorkMode.STANDARD, "clean_mode"),
        (B01_Q10_DP.CLEAN_MODE, 3, YXDeviceWorkMode.HIGH, "clean_mode"),
    ]

    for dp, code, expected_enum, property_name in test_cases:
        status_trait._data = {dp: code}
        property_value = getattr(status_trait, property_name)
        assert property_value == expected_enum, f"Failed for {property_name} with code {code}"


async def test_status_data_property(
    status_trait: StatusTrait,
) -> None:
    """Test the raw data property."""
    test_data = {
        B01_Q10_DP.STATUS: 1,
        B01_Q10_DP.BATTERY: 50,
    }
    status_trait._data = test_data
    assert status_trait.data == test_data

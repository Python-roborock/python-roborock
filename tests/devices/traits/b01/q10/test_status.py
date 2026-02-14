"""Tests for Q10 StatusTrait."""

import json
from typing import Any

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXDeviceState,
    YXDeviceWorkMode,
    YXFanLevel,
)
from roborock.devices.traits.b01.q10.status import StatusTrait
from roborock.roborock_message import RoborockMessage
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="status_trait")
def status_trait_fixture(fake_channel: FakeChannel) -> StatusTrait:
    return StatusTrait(fake_channel)  # type: ignore[arg-type]


def build_q10_response(dps: dict[str, Any]) -> RoborockMessage:
    """Build a Q10 MQTT response message."""
    payload = {"dps": dps}
    return RoborockMessage(
        protocol=11,  # MQTT_PROTO
        payload=json.dumps(payload).encode(),
        seq=0,
        version=b"B01",
    )


async def test_status_trait_battery(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test getting battery status."""
    # Queue a response with battery data
    fake_channel.response_queue.append(build_q10_response({"122": 85}))

    result = await status_trait.refresh()

    assert status_trait.battery == 85
    assert B01_Q10_DP.BATTERY in result


async def test_status_trait_state(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test getting device state."""
    # CLEANING_STATE = 5
    fake_channel.response_queue.append(build_q10_response({"121": 5, "122": 100}))

    result = await status_trait.refresh()

    assert status_trait.state == YXDeviceState.CLEANING_STATE
    assert B01_Q10_DP.STATUS in result


async def test_status_trait_fan_level(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test getting fan level."""
    # FAN_LEVEL NORMAL = 2
    fake_channel.response_queue.append(build_q10_response({"121": 3, "122": 100, "123": 2}))

    result = await status_trait.refresh()

    assert status_trait.fan_level == YXFanLevel.NORMAL
    assert B01_Q10_DP.FAN_LEVEL in result


async def test_status_trait_clean_mode(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test getting cleaning mode."""
    # CLEAN_MODE BOTH_WORK = 1
    fake_channel.response_queue.append(build_q10_response({"121": 3, "122": 100, "137": 1}))

    result = await status_trait.refresh()

    assert status_trait.clean_mode == YXDeviceWorkMode.BOTH_WORK
    assert B01_Q10_DP.CLEAN_MODE in result


async def test_status_trait_cleaning_progress(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test getting cleaning progress."""
    fake_channel.response_queue.append(
        build_q10_response({"121": 5, "122": 100, "141": 25})
    )

    result = await status_trait.refresh()

    assert status_trait.cleaning_progress == 25
    assert B01_Q10_DP.CLEANING_PROGRESS in result


async def test_status_trait_empty_data(status_trait: StatusTrait) -> None:
    """Test status trait with no data queued."""
    # Test that properties return None when data is empty
    assert status_trait.battery is None
    assert status_trait.state is None
    assert status_trait.fan_level is None
    assert status_trait.clean_mode is None
    assert status_trait.cleaning_progress is None


async def test_status_trait_data_property(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test that data property returns the raw data."""
    test_data = {"121": 5, "122": 100, "123": 2}
    fake_channel.response_queue.append(build_q10_response(test_data))

    await status_trait.refresh()

    # Convert string keys to B01_Q10_DP keys
    assert B01_Q10_DP.STATUS in status_trait.data
    assert B01_Q10_DP.BATTERY in status_trait.data
    assert B01_Q10_DP.FAN_LEVEL in status_trait.data


async def test_status_trait_unknown_state(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test handling of unknown state code."""
    # Use a code that doesn't map to any state
    fake_channel.response_queue.append(build_q10_response({"121": 999, "122": 100}))

    await status_trait.refresh()

    # Should return UNKNOWN or None
    assert status_trait.state == YXDeviceState.UNKNOWN or status_trait.state is None


async def test_status_trait_multiple_refreshes(status_trait: StatusTrait, fake_channel: FakeChannel) -> None:
    """Test that multiple refreshes update the status."""
    # First refresh
    fake_channel.response_queue.append(build_q10_response({"121": 3, "122": 80}))
    await status_trait.refresh()
    assert status_trait.battery == 80

    # Second refresh with different battery
    fake_channel.response_queue.append(build_q10_response({"121": 5, "122": 60}))
    await status_trait.refresh()
    assert status_trait.battery == 60

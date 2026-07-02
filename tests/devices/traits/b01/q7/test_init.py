from typing import Any

import pytest

from roborock.data.b01_q7 import (
    CleanTaskTypeMapping,
    CleanTypeMapping,
    SCDeviceCleanParam,
    SCWindMapping,
    WaterLevelMapping,
    WorkStatusMapping,
)
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

from .conftest import FakeQ7Channel


async def test_q7_api_query_values(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test that Q7PropertiesApi correctly converts raw values."""
    response_data = {
        "status": 1,
        "wind": 2,
        "battery": 100,
    }

    fake_channel.response_queue.append(response_data)

    result = await q7_api.query_values(
        [
            RoborockB01Props.STATUS,
            RoborockB01Props.WIND,
        ]
    )

    assert result is not None
    assert result.status == WorkStatusMapping.WAITING_FOR_ORDERS
    assert result.wind == SCWindMapping.STANDARD

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.GET_PROP
    assert params == {"property": [RoborockB01Props.STATUS, RoborockB01Props.WIND]}


@pytest.mark.parametrize(
    ("query", "response_data", "expected_status"),
    [
        (
            [RoborockB01Props.STATUS],
            {"status": 2},
            WorkStatusMapping.PAUSED,
        ),
        (
            [RoborockB01Props.STATUS],
            {"status": 5},
            WorkStatusMapping.SWEEP_MOPING,
        ),
    ],
)
async def test_q7_response_value_mapping(
    query: list[RoborockB01Props],
    response_data: dict[str, Any],
    expected_status: WorkStatusMapping,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test Q7PropertiesApi value mapping for different statuses."""
    fake_channel.response_queue.append(response_data)

    result = await q7_api.query_values(query)

    assert result is not None
    assert result.status == expected_status


async def test_q7_api_set_fan_speed(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test setting fan speed."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_fan_speed(SCWindMapping.STRONG)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_PROP
    assert params == {RoborockB01Props.WIND: SCWindMapping.STRONG.code}


async def test_q7_api_set_water_level(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test setting water level."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_water_level(WaterLevelMapping.HIGH)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_PROP
    assert params == {RoborockB01Props.WATER: WaterLevelMapping.HIGH.code}


@pytest.mark.parametrize("volume", [0, 50, 100])
async def test_q7_api_set_volume(
    volume: int,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test setting the robot voice volume."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_volume(volume)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_PROP
    assert params == {RoborockB01Props.VOLUME: volume}


@pytest.mark.parametrize(
    ("enabled", "expected_code"),
    [(True, 1), (False, 0)],
)
async def test_q7_api_set_child_lock(
    enabled: bool,
    expected_code: int,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test toggling the child lock."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_child_lock(enabled)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_PROP
    assert params == {RoborockB01Props.CHILD_LOCK: expected_code}


@pytest.mark.parametrize("enabled, expected_is_open", [(True, 1), (False, 0)])
async def test_q7_api_set_do_not_disturb(
    enabled: bool,
    expected_is_open: int,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test do-not-disturb is set as a whole via service.set_quiet_time."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_do_not_disturb(enabled, 1200, 420)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_QUIET_TIME
    assert params == {
        "is_open": expected_is_open,
        "quiet_begin_time": 1200,
        "quiet_end_time": 420,
    }


@pytest.mark.parametrize(
    ("begin_time", "end_time"),
    [(-1, 420), (1440, 420), (1200, -1), (1200, 1440)],
)
async def test_q7_api_set_do_not_disturb_invalid_time(
    begin_time: int,
    end_time: int,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test out-of-range times raise ValueError and nothing is sent."""
    with pytest.raises(ValueError, match="minutes since midnight"):
        await q7_api.set_do_not_disturb(True, begin_time, end_time)

    assert len(fake_channel.published_commands) == 0


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [
        (CleanTypeMapping.VACUUM, 0),
        (CleanTypeMapping.VAC_AND_MOP, 1),
        (CleanTypeMapping.MOP, 2),
    ],
)
async def test_q7_api_set_mode(
    mode: CleanTypeMapping,
    expected_code: int,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Test setting cleaning mode (vacuum, mop, or both)."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.set_mode(mode)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_PROP
    assert params == {RoborockB01Props.MODE: expected_code}


async def test_q7_api_start_clean(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test starting cleaning."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.start_clean()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_ROOM_CLEAN
    assert params == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.START.code,
        "room_ids": [],
    }


async def test_q7_api_pause_clean(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test pausing cleaning."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.pause_clean()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_ROOM_CLEAN
    assert params == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.PAUSE.code,
        "room_ids": [],
    }


async def test_q7_api_stop_clean(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test stopping cleaning."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.stop_clean()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_ROOM_CLEAN
    assert params == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.STOP.code,
        "room_ids": [],
    }


async def test_q7_api_return_to_dock(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test returning to dock."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.return_to_dock()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.START_RECHARGE
    assert params == {}


async def test_q7_api_find_me(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test locating the device."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.find_me()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.FIND_DEVICE
    assert params == {}


async def test_q7_api_clean_segments(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test room/segment cleaning helper for Q7."""
    fake_channel.response_queue.append({"result": "ok"})
    await q7_api.clean_segments([10, 11])

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.SET_ROOM_CLEAN
    assert params == {
        "clean_type": CleanTaskTypeMapping.ROOM.code,
        "ctrl_value": SCDeviceCleanParam.START.code,
        "room_ids": [10, 11],
    }

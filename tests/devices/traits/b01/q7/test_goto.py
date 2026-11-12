"""Tests for the Q7 emulated goto (state machine and API integration)."""

import asyncio

import pytest

from roborock.data.b01_q7 import Q7RoborockPoint, SCDeviceCleanParam, WorkModeMapping
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.devices.traits.b01.q7.goto import GotoAction, GotoActionCommand, GotoSnapshot
from roborock.protocols.b01_q7_protocol import Q7DevicePush
from roborock.roborock_typing import RoborockB01Q7Methods

from .conftest import FakeQ7Channel

TARGET = Q7RoborockPoint(x=26500, y=22200)
NEAR = Q7RoborockPoint(x=26590, y=22220)
FAR = Q7RoborockPoint(x=29060, y=22090)


def _snapshot(
    position: Q7RoborockPoint | None = FAR, work_mode: WorkModeMapping | None = WorkModeMapping.PLAN_AREA
) -> GotoSnapshot:
    return GotoSnapshot(position=position, work_mode=work_mode)


def _action() -> tuple[GotoAction, list[GotoActionCommand]]:
    action = GotoAction(TARGET, tolerance=300)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)
    return action, commands


def test_goto_action_stops_near_target() -> None:
    """Once the zone task runs, getting within tolerance requests a stop."""
    action, commands = _action()

    action.update(_snapshot())
    action.update(_snapshot(position=NEAR))

    assert commands == [GotoActionCommand.STOP]


def test_goto_action_waits_for_zone_task() -> None:
    """Being near the target before the zone task started does not stop anything."""
    action, commands = _action()

    action.update(_snapshot(position=NEAR, work_mode=WorkModeMapping.IDLE))

    assert commands == []


def test_goto_action_stops_trip_home_after_zone_done() -> None:
    """If the zone finished before a close position arrived, the trip home is stopped."""
    action, commands = _action()

    action.update(_snapshot())
    action.update(_snapshot(work_mode=WorkModeMapping.PLAN_AREA_GO_HOME))

    assert commands == [GotoActionCommand.STOP]


@pytest.mark.parametrize("work_mode", [WorkModeMapping.IDLE, WorkModeMapping.MOPPING, None])
def test_goto_action_completes_when_task_replaced(work_mode: WorkModeMapping | None) -> None:
    """Leaving the zone task any other way completes the action without commands."""
    action, commands = _action()

    action.update(_snapshot())
    action.update(_snapshot(work_mode=work_mode))

    assert commands == [GotoActionCommand.COMPLETE]


@pytest.mark.parametrize(
    ("work_mode", "expected"),
    [(WorkModeMapping.PLAN_AREA, GotoActionCommand.STOP), (WorkModeMapping.IDLE, GotoActionCommand.COMPLETE)],
)
def test_goto_action_timeout(work_mode: WorkModeMapping, expected: GotoActionCommand) -> None:
    """The safety timeout stops a still-running zone task, otherwise just completes."""
    action, commands = _action()
    action.update(_snapshot())

    action.timeout(_snapshot(work_mode=work_mode))

    assert commands == [expected]


def test_goto_action_retry_after_failed_stop() -> None:
    """A failed stop can be retried from the latest state; one command is pending at a time."""
    action, commands = _action()
    action.update(_snapshot())
    action.update(_snapshot(position=NEAR))
    action.update(_snapshot(position=NEAR))  # pending: no duplicate

    action.retry()

    assert commands == [GotoActionCommand.STOP, GotoActionCommand.STOP]


def _push(**params: object) -> Q7DevicePush:
    return Q7DevicePush(method="prop.post", params=dict(params))


def _cur_path(position: Q7RoborockPoint) -> Q7DevicePush:
    x, y = position.to_world()
    return _push(cur_path=[1, x, y, 0.0, 0, 1794490763])


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_q7_goto_position_stops_zone_at_target(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """goto_position starts a small zone and stops it when the live position arrives."""
    await q7_api.start()
    assert fake_channel.device_push_callback is not None
    fake_channel.device_push_callback(_cur_path(FAR))

    await q7_api.goto_position(TARGET)
    await _settle()

    zone_points = [round(value, 3) for value in fake_channel.published_commands[1][1]["zone_points"]]
    assert fake_channel.published_commands[:3] == [
        (RoborockB01Q7Methods.SET_PREFERENCE_TYPE, {"prefer_type": 4}),
        (RoborockB01Q7Methods.SET_ZONE_POINTS, fake_channel.published_commands[1][1]),
        (RoborockB01Q7Methods.SET_ZONE_CLEAN, {"ctrl_value": SCDeviceCleanParam.START.code}),
    ]
    assert zone_points == [0.75, -3.55, 1.25, -3.55, 1.25, -3.05, 0.75, -3.05]
    # The live map is requested to track the position.
    assert (RoborockB01Q7Methods.UPLOAD_BY_MAPTYPE, {"map_type": 0}) in fake_channel.published_commands

    fake_channel.device_push_callback(_push(work_mode=WorkModeMapping.PLAN_AREA.code, status=5))
    fake_channel.device_push_callback(_cur_path(NEAR))
    await _settle()

    stop = (RoborockB01Q7Methods.SET_ZONE_CLEAN, {"ctrl_value": SCDeviceCleanParam.STOP.code})
    assert fake_channel.published_commands.count(stop) == 1
    await q7_api.close()


async def test_q7_goto_position_already_there(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """No task is started when the robot is already within tolerance of the target."""
    await q7_api.start()
    assert fake_channel.device_push_callback is not None
    fake_channel.device_push_callback(_cur_path(NEAR))

    await q7_api.goto_position(TARGET)

    assert fake_channel.published_commands == []
    await q7_api.close()


async def test_q7_goto_cancelled_by_other_command(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Another cleaning command replaces the goto, which then never sends its stop."""
    await q7_api.start()
    assert fake_channel.device_push_callback is not None

    await q7_api.goto_position(TARGET)
    await q7_api.clean_segments([11])
    fake_channel.device_push_callback(_push(work_mode=WorkModeMapping.PLAN_AREA.code))
    fake_channel.device_push_callback(_cur_path(NEAR))
    await _settle()

    stop = (RoborockB01Q7Methods.SET_ZONE_CLEAN, {"ctrl_value": SCDeviceCleanParam.STOP.code})
    assert stop not in fake_channel.published_commands
    await q7_api.close()

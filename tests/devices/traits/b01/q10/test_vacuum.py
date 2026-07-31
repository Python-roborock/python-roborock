import asyncio
from base64 import b64decode
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceState,
    YXFanLevel,
)
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10 import vacuum as vacuum_module
from roborock.devices.traits.b01.q10.vacuum import VacuumTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import Q10Point, Q10TracePacket

from .conftest import FakeB01Q10Channel


@pytest.fixture(name="vacuum")
def vacuum_fixture(q10_api: Q10PropertiesApi) -> VacuumTrait:
    return q10_api.vacuum


@pytest.mark.parametrize(
    ("command_fn", "expected_payload"),
    [
        # Payloads verified live against ss07 hardware.
        (lambda x: x.start_clean(), {"201": 1}),
        (lambda x: x.clean_segments([9]), {"201": {"cmd": 2, "clean_paramters": [9]}}),
        (lambda x: x.clean_segments([1, 2]), {"201": {"cmd": 2, "clean_paramters": [1, 2]}}),
        (lambda x: x.spot_clean(), {"201": 5}),
        (lambda x: x.pause_clean(), {"204": 0}),
        (lambda x: x.resume_clean(), {"205": 0}),
        (lambda x: x.stop_clean(), {"206": 0}),
        (lambda x: x.return_to_dock(), {"202": 5}),
        (lambda x: x.empty_dustbin(), {"203": 2}),
        (lambda x: x.set_clean_mode(YXCleanType.VAC_AND_MOP), {"137": 1}),
        (lambda x: x.set_fan_level(YXFanLevel.BALANCED), {"123": 2}),
    ],
)
async def test_vacuum_commands(
    vacuum: VacuumTrait,
    fake_channel: FakeB01Q10Channel,
    command_fn: Callable[[VacuumTrait], Awaitable[None]],
    expected_payload: dict[str, Any],
) -> None:
    """Test sending a vacuum start command."""
    await command_fn(vacuum)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]

    dp_code = int(list(expected_payload.keys())[0])
    expected_params = list(expected_payload.values())[0]

    assert command.code == dp_code
    assert params == expected_params


async def test_clean_zone(
    vacuum: VacuumTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    """Test the source-verified Q10 zone payload."""
    await vacuum.clean_zone(25550, 25600, 25650, 25700, clean_count=2)

    command, params = fake_channel.published_commands[0]
    assert command.code == 201
    assert params["cmd"] == 3
    assert b64decode(params["clean_paramters"]) == bytes(
        (
            1,
            2,
            1,
            4,
            0,
            10,
            0,
            20,
            0,
            30,
            0,
            20,
            0,
            30,
            0,
            40,
            0,
            10,
            0,
            40,
            0,
            *([0] * 19),
        )
    )


@pytest.mark.parametrize("clean_count", [0, 4])
async def test_clean_zone_rejects_invalid_clean_count(
    vacuum: VacuumTrait,
    clean_count: int,
) -> None:
    """Test that the device clean-count range is validated."""
    with pytest.raises(ValueError, match="clean_count must be between 1 and 3"):
        await vacuum.clean_zone(25550, 25600, 25650, 25700, clean_count=clean_count)


async def test_goto_position_pauses_owned_zone_at_target(
    q10_api: Q10PropertiesApi,
    fake_channel: FakeB01Q10Channel,
) -> None:
    """A goto pauses after its own trace session reaches the target."""
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(0, 0)], sequence=1))
    q10_api.status.clean_task_type = YXDeviceCleanTask.DIVIDE_AREAS
    q10_api.status.status = YXDeviceState.CLEANING

    await q10_api.vacuum.goto_position(29900, 28650)
    monitor = q10_api.vacuum._goto_monitor_task
    assert monitor is not None

    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1760, 1260)], sequence=2))
    await monitor

    assert [command for command, _ in fake_channel.published_commands] == [
        B01_Q10_DP.START_CLEAN,
        B01_Q10_DP.PAUSE,
    ]


async def test_goto_position_does_not_pause_replacement_session(
    q10_api: Q10PropertiesApi,
    fake_channel: FakeB01Q10Channel,
) -> None:
    """A newer trace session is not controlled by an older goto monitor."""
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(0, 0)], sequence=1))
    q10_api.status.clean_task_type = YXDeviceCleanTask.DIVIDE_AREAS
    q10_api.status.status = YXDeviceState.CLEANING

    await q10_api.vacuum.goto_position(29900, 28650)
    monitor = q10_api.vacuum._goto_monitor_task
    assert monitor is not None

    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(100, 100)], sequence=2))
    await asyncio.sleep(0)
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1760, 1260)], sequence=3))
    await monitor

    assert [command for command, _ in fake_channel.published_commands] == [B01_Q10_DP.START_CLEAN]


async def test_goto_position_retries_pause(
    q10_api: Q10PropertiesApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient pause failure is retried while the goto is still owned."""
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(0, 0)], sequence=1))
    q10_api.status.clean_task_type = YXDeviceCleanTask.DIVIDE_AREAS
    q10_api.status.status = YXDeviceState.CLEANING
    send = AsyncMock(side_effect=[None, RoborockException("pause failed"), None])
    q10_api.vacuum._command.send = send
    monkeypatch.setattr(vacuum_module, "_GOTO_RETRY_INTERVAL", 0)

    await q10_api.vacuum.goto_position(29900, 28650)
    monitor = q10_api.vacuum._goto_monitor_task
    assert monitor is not None
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1760, 1260)], sequence=2))
    await monitor

    assert [call.kwargs["command"] for call in send.await_args_list] == [
        B01_Q10_DP.START_CLEAN,
        B01_Q10_DP.PAUSE,
        B01_Q10_DP.PAUSE,
    ]


async def test_goto_position_stops_owned_zone_after_timeout(
    q10_api: Q10PropertiesApi,
    fake_channel: FakeB01Q10Channel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The safety timeout stops only the zone session owned by the goto."""
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(0, 0)], sequence=1))
    q10_api.status.clean_task_type = YXDeviceCleanTask.DIVIDE_AREAS
    q10_api.status.status = YXDeviceState.CLEANING
    monkeypatch.setattr(vacuum_module, "_GOTO_TIMEOUT", 0.01)
    monkeypatch.setattr(vacuum_module, "_GOTO_RETRY_INTERVAL", 0)

    await q10_api.vacuum.goto_position(29900, 28650)
    monitor = q10_api.vacuum._goto_monitor_task
    assert monitor is not None
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(100, 100)], sequence=2))
    await monitor

    assert [command for command, _ in fake_channel.published_commands] == [
        B01_Q10_DP.START_CLEAN,
        B01_Q10_DP.STOP,
    ]


async def test_goto_position_at_current_position_pauses_owned_zone(
    q10_api: Q10PropertiesApi,
    fake_channel: FakeB01Q10Channel,
) -> None:
    """An early return pauses an active goto zone instead of orphaning it."""
    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(0, 0)], sequence=1))
    q10_api.status.clean_task_type = YXDeviceCleanTask.DIVIDE_AREAS
    q10_api.status.status = YXDeviceState.CLEANING
    await q10_api.vacuum.goto_position(29900, 28650)
    monitor = q10_api.vacuum._goto_monitor_task
    assert monitor is not None

    q10_api.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(100, 100)], sequence=2))
    await asyncio.sleep(0)
    await q10_api.vacuum.goto_position(25750, 25750)
    await asyncio.sleep(0)

    assert q10_api.vacuum._goto_monitor_task is None
    assert monitor.cancelled()
    assert [command for command, _ in fake_channel.published_commands] == [
        B01_Q10_DP.START_CLEAN,
        B01_Q10_DP.PAUSE,
    ]

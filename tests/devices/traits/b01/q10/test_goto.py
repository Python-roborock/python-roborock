"""Tests for the Q10 goto state machine."""

from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceCleanTask, YXDeviceState
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.devices.traits.b01.q10.goto import (
    GotoAction,
    GotoActionCommand,
    GotoSnapshot,
)

TARGET = Q10RoborockPoint(29900, 28650)


def _snapshot(
    *,
    position: Q10RoborockPoint | None = None,
    trace_sequence: int | None = 2,
    clean_task_type: YXDeviceCleanTask | None = YXDeviceCleanTask.DIVIDE_AREAS,
    status: YXDeviceState | None = YXDeviceState.CLEANING,
) -> GotoSnapshot:
    return GotoSnapshot(position, trace_sequence, clean_task_type, status)


def test_goto_action_requests_pause_at_target() -> None:
    """A newly owned zone session requests a pause when it reaches the target."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)

    action.update(_snapshot(position=Q10RoborockPoint(29800, 28650)))

    assert commands == [GotoActionCommand.PAUSE]


def test_goto_action_ignores_previous_trace_session() -> None:
    """A cached trace from before the goto does not establish ownership."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)

    action.update(_snapshot(position=TARGET, trace_sequence=1))

    assert commands == []


def test_goto_action_does_not_pause_unconfirmed_task() -> None:
    """A new trace alone does not establish ownership of a zone-clean task."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)

    action.update(
        _snapshot(
            position=TARGET,
            clean_task_type=YXDeviceCleanTask.SMART,
        )
    )

    assert commands == []


def test_goto_action_completes_when_owned_session_is_replaced() -> None:
    """A later trace sequence is never controlled by the older goto."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)
    action.update(_snapshot(position=Q10RoborockPoint(26000, 26000)))

    action.update(_snapshot(position=TARGET, trace_sequence=3))

    assert commands == [GotoActionCommand.COMPLETE]


def test_goto_action_timeout_stops_only_owned_zone() -> None:
    """A timeout requests stop only while the owned zone session is current."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)
    snapshot = _snapshot(position=Q10RoborockPoint(26000, 26000))
    action.update(snapshot)

    action.timeout(snapshot)

    assert commands == [GotoActionCommand.STOP]


def test_goto_action_timeout_completes_without_ownership() -> None:
    """A timeout cannot stop a task when no new trace session was observed."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)

    action.timeout(_snapshot(position=TARGET, trace_sequence=1))

    assert commands == [GotoActionCommand.COMPLETE]


def test_goto_action_timeout_supersedes_failed_pause() -> None:
    """A failed pause becomes a stop retry once the safety timeout has elapsed."""
    action = GotoAction(TARGET, previous_trace_sequence=1, tolerance=200)
    commands: list[GotoActionCommand] = []
    action.add_update_listener(commands.append)
    snapshot = _snapshot(position=TARGET)
    action.update(snapshot)

    action.timeout(snapshot)
    action.retry()

    assert commands == [GotoActionCommand.PAUSE, GotoActionCommand.STOP]

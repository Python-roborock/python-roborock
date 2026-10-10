"""State management for an emulated Q10 goto action."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import hypot

from roborock.callbacks import CallbackList
from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceCleanTask, YXDeviceState
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint

_LOGGER = logging.getLogger(__name__)
_TERMINAL_STATES = {
    YXDeviceState.IDLE,
    YXDeviceState.PAUSED,
    YXDeviceState.RETURNING_HOME,
    YXDeviceState.CHARGING,
}


class GotoActionCommand(StrEnum):
    """A command requested by a Q10 goto action."""

    PAUSE = "pause"
    STOP = "stop"
    COMPLETE = "complete"


@dataclass(frozen=True)
class GotoSnapshot:
    """Device state needed to advance a goto action."""

    position: Q10RoborockPoint | None
    trace_sequence: int | None
    clean_task_type: YXDeviceCleanTask | None
    status: YXDeviceState | None


class GotoAction:
    """Decide how one emulated goto should react to device updates.

    The action owns no tasks and sends no device commands. ``VacuumTrait`` feeds
    it push-derived snapshots and performs commands requested by its callbacks.
    """

    def __init__(
        self,
        target: Q10RoborockPoint,
        previous_trace_sequence: int | None,
        *,
        tolerance: int,
    ) -> None:
        """Initialize a goto action waiting for a new trace session."""
        self._target = target
        self._previous_trace_sequence = previous_trace_sequence
        self._tolerance = tolerance
        self._owned_trace_sequence: int | None = None
        self._owned_task_seen = False
        self._command_pending = False
        self._timeout_requested = False
        self._finished = False
        self._latest_snapshot: GotoSnapshot | None = None
        self._callbacks: CallbackList[GotoActionCommand] = CallbackList(logger=_LOGGER)

    def add_update_listener(self, callback: Callable[[GotoActionCommand], None]) -> Callable[[], None]:
        """Register a callback for the next command requested by the action."""
        return self._callbacks.add_callback(callback)

    def update(self, snapshot: GotoSnapshot) -> None:
        """Process the latest push-derived device state."""
        self._latest_snapshot = snapshot
        self._evaluate(snapshot)

    def retry(self) -> None:
        """Re-evaluate the latest state after a requested command failed."""
        if self._finished or self._latest_snapshot is None:
            return
        self._command_pending = False
        if self._timeout_requested:
            self._evaluate_timeout(self._latest_snapshot)
        else:
            self._evaluate(self._latest_snapshot)

    def timeout(self, snapshot: GotoSnapshot) -> None:
        """Request a stop only if this action still owns the current zone task."""
        if self._finished:
            return
        self._latest_snapshot = snapshot
        self._timeout_requested = True
        if self._command_pending:
            return
        self._evaluate_timeout(snapshot)

    def _evaluate_timeout(self, snapshot: GotoSnapshot) -> None:
        """Derive the safe timeout command from the latest device state."""
        if self.owns(snapshot):
            self._emit(GotoActionCommand.STOP)
        else:
            self._emit(GotoActionCommand.COMPLETE)

    def complete(self) -> None:
        """Mark the action complete after its requested command succeeds."""
        self._finished = True
        self._command_pending = False

    def owns(self, snapshot: GotoSnapshot) -> bool:
        """Return whether this action owns the current Q10 zone-clean session."""
        return (
            self._owned_trace_sequence is not None
            and snapshot.trace_sequence == self._owned_trace_sequence
            and snapshot.clean_task_type is YXDeviceCleanTask.DIVIDE_AREAS
        )

    def _evaluate(self, snapshot: GotoSnapshot) -> None:
        """Derive the next command from the latest device state."""
        if self._finished or self._command_pending:
            return

        if self._owned_trace_sequence is None:
            if snapshot.trace_sequence is not None and snapshot.trace_sequence != self._previous_trace_sequence:
                self._owned_trace_sequence = snapshot.trace_sequence
        elif snapshot.trace_sequence != self._owned_trace_sequence:
            _LOGGER.debug("Q10 goto task was replaced by another cleaning session")
            self._emit(GotoActionCommand.COMPLETE)
            return

        if (
            self._owned_trace_sequence is not None
            and snapshot.clean_task_type is YXDeviceCleanTask.DIVIDE_AREAS
            and snapshot.status not in _TERMINAL_STATES
        ):
            self._owned_task_seen = True

        if self._owned_task_seen and (
            snapshot.clean_task_type is not YXDeviceCleanTask.DIVIDE_AREAS or snapshot.status in _TERMINAL_STATES
        ):
            self._emit(GotoActionCommand.COMPLETE)
            return

        if (
            self.owns(snapshot)
            and snapshot.position is not None
            and hypot(
                snapshot.position.x - self._target.x,
                snapshot.position.y - self._target.y,
            )
            <= self._tolerance
        ):
            self._emit(GotoActionCommand.PAUSE)

    def _emit(self, command: GotoActionCommand) -> None:
        """Publish a requested command once until it is handled."""
        if command is GotoActionCommand.COMPLETE:
            self._finished = True
        else:
            self._command_pending = True
        self._callbacks(command)

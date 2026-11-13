"""State management for an emulated Q7 goto action.

The Q7 firmware has no "go to point" command, so a goto is emulated (like on the
Q10) with a small zone-clean task around the target that is stopped once the
robot gets close enough.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import hypot

from roborock.callbacks import CallbackList
from roborock.data.b01_q7.b01_q7_code_mappings import WorkModeMapping
from roborock.data.b01_q7.b01_q7_containers import Q7RoborockPoint

_LOGGER = logging.getLogger(__name__)

# ``work_mode`` reported while a zone-clean task is running (verified on a Q7 sc05).
_ZONE_WORK_MODE = WorkModeMapping.PLAN_AREA
# Reported once the zone is done and the robot heads home: it already reached the target.
_ZONE_DONE_WORK_MODE = WorkModeMapping.PLAN_AREA_GO_HOME


class GotoActionCommand(StrEnum):
    """A command requested by a Q7 goto action."""

    STOP = "stop"
    COMPLETE = "complete"


@dataclass(frozen=True)
class GotoSnapshot:
    """Device state needed to advance a goto action."""

    position: Q7RoborockPoint | None
    work_mode: WorkModeMapping | None


class GotoAction:
    """Decide how one emulated goto should react to device updates.

    The action owns no tasks and sends no device commands. ``Q7PropertiesApi``
    feeds it push-derived snapshots and performs the commands it requests.
    """

    def __init__(self, target: Q7RoborockPoint, *, tolerance: int) -> None:
        """Initialize a goto action waiting for its zone task to start."""
        self._target = target
        self._tolerance = tolerance
        self._task_seen = False
        self._command_pending = False
        self._finished = False
        self._latest_snapshot: GotoSnapshot | None = None
        self._callbacks: CallbackList[GotoActionCommand] = CallbackList(logger=_LOGGER)

    def add_update_listener(self, callback: Callable[[GotoActionCommand], None]) -> Callable[[], None]:
        """Register a callback for the commands requested by the action."""
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
        self._evaluate(self._latest_snapshot)

    def timeout(self, snapshot: GotoSnapshot) -> None:
        """Stop the zone task if it is still running when the safety timeout expires."""
        if self._finished or self._command_pending:
            return
        self._latest_snapshot = snapshot
        if self._task_seen and snapshot.work_mode is _ZONE_WORK_MODE:
            self._emit(GotoActionCommand.STOP)
        else:
            self._emit(GotoActionCommand.COMPLETE)

    def complete(self) -> None:
        """Mark the action complete after its requested command succeeds."""
        self._finished = True
        self._command_pending = False

    def is_near_target(self, position: Q7RoborockPoint | None) -> bool:
        """Return whether ``position`` is within the arrival tolerance of the target."""
        return (
            position is not None and hypot(position.x - self._target.x, position.y - self._target.y) <= self._tolerance
        )

    def _evaluate(self, snapshot: GotoSnapshot) -> None:
        """Derive the next command from the latest device state."""
        if self._finished or self._command_pending:
            return

        if snapshot.work_mode is _ZONE_WORK_MODE:
            self._task_seen = True
        elif self._task_seen and snapshot.work_mode is _ZONE_DONE_WORK_MODE:
            # The small zone around the target was finished before a close-enough
            # position arrived: stop the trip home so the robot stays at the target.
            self._emit(GotoActionCommand.STOP)
            return
        elif self._task_seen:
            # The zone task ended (finished, paused, docking) or was replaced.
            _LOGGER.debug("Q7 goto zone task ended or was replaced (work_mode=%s)", snapshot.work_mode)
            self._emit(GotoActionCommand.COMPLETE)
            return

        if self._task_seen and self.is_near_target(snapshot.position):
            self._emit(GotoActionCommand.STOP)

    def _emit(self, command: GotoActionCommand) -> None:
        """Publish a requested command once until it is handled."""
        if command is GotoActionCommand.COMPLETE:
            self._finished = True
        else:
            self._command_pending = True
        self._callbacks(command)

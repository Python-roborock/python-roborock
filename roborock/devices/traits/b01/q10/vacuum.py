"""Traits for Q10 B01 devices."""

import asyncio
import logging
from collections.abc import Callable
from math import hypot

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXDeviceCleanTask,
    YXFanLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import CleanParams, encode_clean_params

from .command import CommandTrait
from .goto import GotoAction, GotoActionCommand, GotoSnapshot
from .map import MapContentTrait
from .status import StatusTrait

_GOTO_HALF_ZONE_SIZE = 200
_GOTO_TOLERANCE = 200
_GOTO_TIMEOUT = 300
_GOTO_RETRY_INTERVAL = 1

_LOGGER = logging.getLogger(__name__)


class VacuumTrait:
    """Trait for sending vacuum commands.

    This is a wrapper around the CommandTrait for sending vacuum related
    commands to Q10 devices.
    """

    def __init__(
        self,
        command: CommandTrait,
        status: StatusTrait,
        map_content: MapContentTrait,
    ) -> None:
        """Initialize the VacuumTrait."""
        self._command = command
        self._status = status
        self._map = map_content
        self._goto_action: GotoAction | None = None
        self._goto_action_remove_listener: Callable[[], None] | None = None
        self._goto_timeout_task: asyncio.Task[None] | None = None
        self._goto_command_task: asyncio.Task[None] | None = None
        self._remove_map_listener = self._map.add_update_listener(self._goto_source_updated)
        self._remove_status_listener = self._status.add_update_listener(self._goto_source_updated)

    async def close(self) -> None:
        """Cancel background work owned by the trait."""
        self.cancel_goto()
        self._remove_map_listener()
        self._remove_status_listener()

    def cancel_goto(self) -> None:
        """Cancel an emulated goto replaced by another command."""
        if self._goto_action is not None:
            self._goto_action.complete()
            self._goto_action = None
        if self._goto_action_remove_listener is not None:
            self._goto_action_remove_listener()
            self._goto_action_remove_listener = None
        current_task = asyncio.current_task()
        for task_name in ("_goto_timeout_task", "_goto_command_task"):
            if (task := getattr(self, task_name)) is not None:
                if task is not current_task:
                    task.cancel()
                setattr(self, task_name, None)

    def _goto_snapshot(self) -> GotoSnapshot:
        """Return the latest state used by an active goto action."""
        return GotoSnapshot(
            position=self._map.robot_position,
            trace_sequence=self._map.trace_sequence,
            clean_task_type=self._status.clean_task_type,
            status=self._status.status,
        )

    def _goto_source_updated(self) -> None:
        """Feed push-derived map or status state to the active goto action."""
        if self._goto_action is not None:
            self._goto_action.update(self._goto_snapshot())

    def _goto_action_updated(self, action: GotoAction, command: GotoActionCommand) -> None:
        """Schedule a device command requested by the active goto action."""
        if action is not self._goto_action:
            return
        if command is GotoActionCommand.COMPLETE:
            self.cancel_goto()
            return
        if self._goto_command_task is None:
            self._goto_command_task = asyncio.create_task(
                self._async_handle_goto_command(action, command),
                name="roborock_q10_goto_command",
            )

    async def _async_handle_goto_command(self, action: GotoAction, command: GotoActionCommand) -> None:
        """Perform a pause or stop requested by the active goto action."""
        current_task = asyncio.current_task()
        dp_command = B01_Q10_DP.PAUSE if command is GotoActionCommand.PAUSE else B01_Q10_DP.STOP
        try:
            await self._command.send(command=dp_command, params=0)
        except RoborockException as err:
            if command is GotoActionCommand.PAUSE:
                _LOGGER.warning("Failed to pause completed Q10 goto task; retrying: %s", err)
                await asyncio.sleep(_GOTO_RETRY_INTERVAL)
                if action is self._goto_action:
                    self._goto_command_task = None
                    action.retry()
                return
            _LOGGER.warning("Failed to stop timed-out Q10 goto task: %s", err)
        if action is self._goto_action:
            action.complete()
            self.cancel_goto()
        if self._goto_command_task is current_task:
            self._goto_command_task = None

    async def _async_timeout_goto(self, action: GotoAction) -> None:
        """Tell the active goto action when its safety timeout expires."""
        try:
            await asyncio.sleep(_GOTO_TIMEOUT)
        except asyncio.CancelledError:
            return
        if action is self._goto_action:
            action.timeout(self._goto_snapshot())

    async def start_clean(self) -> None:
        """Start a whole-home clean.

        The ``dpStartClean`` (201) command selects a task by code: ``1`` =
        whole-home, ``2`` = segment/room (see :meth:`clean_segments`), ``3`` =
        zone, ``4`` = build map, ``5`` = spot. Whole-home and spot accept the
        bare integer code; segment cleaning needs a room selection (an object
        payload) instead.

        Verified live against ss07 hardware: ``{"dps": {"201": 1}}`` starts a
        whole-home clean (clean_task_type -> 1).
        """
        await self._command.send(command=B01_Q10_DP.START_CLEAN, params=1)
        self.cancel_goto()

    async def clean_segments(self, segment_ids: list[int]) -> None:
        """Start a room / segment clean for the given segment (room) ids.

        The ids are the same room ids the device reports on its map (see the Q10
        ``MapContentTrait`` -- ``map.rooms``, each with an ``id``).

        Unlike whole-home and spot, ``dpStartClean`` (201) carries the room
        selection as an object: ``{"cmd": <task>, "clean_paramters": [<id>, ...]}``,
        where ``cmd`` is the segment-clean task code.

        Verified live against ss07 hardware: sending
        ``{"dps": {"201": {"cmd": 2, "clean_paramters": [9]}}}`` starts cleaning
        room 9 (clean_task_type -> 2 / electoral).
        """
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            # "clean_paramters" intentionally mirrors the device's misspelling of
            # "parameters" -- the firmware only accepts that exact key.
            params={"cmd": YXDeviceCleanTask.ELECTORAL.code, "clean_paramters": segment_ids},
        )
        self.cancel_goto()

    async def clean_zone(
        self,
        first_corner: Q10RoborockPoint,
        second_corner: Q10RoborockPoint,
        *,
        clean_count: int = 1,
    ) -> None:
        """Clean one rectangular zone in the common Roborock coordinate space."""
        encoded_zone = encode_clean_params(CleanParams(first_corner, second_corner, clean_count))
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            params={
                "cmd": YXDeviceCleanTask.DIVIDE_AREAS.code,
                # "clean_paramters" is the spelling required by the firmware.
                "clean_paramters": encoded_zone,
            },
        )
        self.cancel_goto()

    async def goto_position(self, target: Q10RoborockPoint) -> None:
        """Move to a coordinate using an owned 40 cm zone-clean task."""
        target.to_vector()
        snapshot = self._goto_snapshot()
        if (position := snapshot.position) is not None and hypot(
            position.x - target.x, position.y - target.y
        ) <= _GOTO_TOLERANCE:
            if self._goto_action is not None and self._goto_action.owns(snapshot):
                await self._command.send(command=B01_Q10_DP.PAUSE, params=0)
                self.cancel_goto()
            return

        encoded_zone = encode_clean_params(
            CleanParams(
                Q10RoborockPoint(
                    target.x - _GOTO_HALF_ZONE_SIZE,
                    target.y - _GOTO_HALF_ZONE_SIZE,
                ),
                Q10RoborockPoint(
                    target.x + _GOTO_HALF_ZONE_SIZE,
                    target.y + _GOTO_HALF_ZONE_SIZE,
                ),
            )
        )
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            params={
                "cmd": YXDeviceCleanTask.DIVIDE_AREAS.code,
                "clean_paramters": encoded_zone,
            },
        )
        self.cancel_goto()
        action = GotoAction(
            target,
            snapshot.trace_sequence,
            tolerance=_GOTO_TOLERANCE,
        )
        self._goto_action = action
        self._goto_action_remove_listener = action.add_update_listener(
            lambda command: self._goto_action_updated(action, command)
        )
        self._goto_timeout_task = asyncio.create_task(
            self._async_timeout_goto(action),
            name="roborock_q10_goto_timeout",
        )
        action.update(self._goto_snapshot())

    async def spot_clean(self) -> None:
        """Start a spot / part clean around the robot's current position.

        Verified live: ``{"dps": {"201": 5}}`` (clean_task_type -> 5).
        """
        await self._command.send(command=B01_Q10_DP.START_CLEAN, params=5)
        self.cancel_goto()

    async def pause_clean(self) -> None:
        """Pause the current task. Verified live: ``{"dps": {"204": 0}}``."""
        await self._command.send(command=B01_Q10_DP.PAUSE, params=0)
        self.cancel_goto()

    async def resume_clean(self) -> None:
        """Resume a paused task. Verified live: ``{"dps": {"205": 0}}``."""
        await self._command.send(command=B01_Q10_DP.RESUME, params=0)
        self.cancel_goto()

    async def stop_clean(self) -> None:
        """Stop / cancel the current task. Verified live: ``{"dps": {"206": 0}}``."""
        await self._command.send(command=B01_Q10_DP.STOP, params=0)
        self.cancel_goto()

    async def return_to_dock(self) -> None:
        """Send the robot back to the dock to charge.

        Uses ``dpStartBack`` (202) with the back-dock task code ``5`` (charge),
        matching the official app. Verified live: ``{"dps": {"202": 5}}`` puts the
        robot into the returning state. (The other back-dock codes are ``1`` =
        wash mop en route and ``4`` = collect dust en route.)
        """
        await self._command.send(command=B01_Q10_DP.START_BACK, params=5)
        self.cancel_goto()

    async def empty_dustbin(self) -> None:
        """Empty the dustbin at the dock.

        Verified live: ``{"dps": {"203": 2}}`` triggers dust collection
        (status -> emptying_the_bin). This is a dock task (``dpStartDockTask``),
        distinct from the en-route collect-dust back-dock code.
        """
        await self._command.send(command=B01_Q10_DP.START_DOCK_TASK, params=2)

    async def set_clean_mode(self, mode: YXCleanType) -> None:
        """Set the cleaning mode (vacuum, mop, or both)."""
        await self._command.send(
            command=B01_Q10_DP.CLEAN_MODE,
            params=mode.code,
        )

    async def set_fan_level(self, level: YXFanLevel) -> None:
        """Set the fan suction level."""
        await self._command.send(
            command=B01_Q10_DP.FAN_LEVEL,
            params=level.code,
        )

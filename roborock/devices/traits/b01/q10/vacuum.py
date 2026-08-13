"""Traits for Q10 B01 devices."""

import asyncio
import logging
from base64 import b64encode
from math import hypot
from struct import error as StructError
from struct import pack

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceState,
    YXFanLevel,
)
from roborock.exceptions import RoborockException

from .command import CommandTrait
from .coordinates import roborock_to_vector_coordinate
from .map import MapContentTrait
from .status import StatusTrait

_ZONE_NAME_FIELD_LENGTH = 19
_GOTO_HALF_ZONE_SIZE = 200
_GOTO_TOLERANCE = 200
_GOTO_TIMEOUT = 300
_GOTO_RETRY_INTERVAL = 1

_LOGGER = logging.getLogger(__name__)


def _encode_zone(x1: int, y1: int, x2: int, y2: int, clean_count: int) -> str:
    """Encode one rectangular Q10 cleaning zone."""
    if not 1 <= clean_count <= 3:
        raise ValueError("clean_count must be between 1 and 3")

    min_x, max_x = sorted((x1, x2))
    min_y, max_y = sorted((y1, y2))
    points = (
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    )
    payload = bytearray((1, clean_count, 1, len(points)))
    try:
        for point_x, point_y in points:
            payload.extend(
                pack(
                    ">hh",
                    roborock_to_vector_coordinate(point_x),
                    roborock_to_vector_coordinate(point_y),
                )
            )
    except StructError as err:
        raise ValueError("zone coordinates are outside the supported range") from err

    # The app protocol reserves a fixed 19-byte UTF-8 name field per zone.
    payload.append(0)
    payload.extend(bytes(_ZONE_NAME_FIELD_LENGTH))
    return b64encode(payload).decode()


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
        self._goto_monitor_task: asyncio.Task[None] | None = None
        self._goto_trace_sequence: int | None = None

    async def close(self) -> None:
        """Cancel background work owned by the trait."""
        if (task := self._goto_monitor_task) is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._goto_monitor_task = None
        self._goto_trace_sequence = None

    def cancel_goto(self) -> None:
        """Cancel monitoring for an emulated goto replaced by another command."""
        if self._goto_monitor_task is not None:
            self._goto_monitor_task.cancel()
            self._goto_monitor_task = None
            self._goto_trace_sequence = None

    async def _async_monitor_goto_target(
        self,
        x: int,
        y: int,
        previous_trace_sequence: int | None,
    ) -> None:
        """Pause the owned mini-zone task after it reaches the target."""
        current_task = asyncio.current_task()
        owned_trace_sequence: int | None = None
        owned_task_seen = False
        update_event = asyncio.Event()
        remove_map_listener = self._map.add_update_listener(update_event.set)
        remove_status_listener = self._status.add_update_listener(update_event.set)
        try:
            async with asyncio.timeout(_GOTO_TIMEOUT):
                while True:
                    trace_sequence = self._map.trace_sequence
                    if owned_trace_sequence is None:
                        if trace_sequence is not None and trace_sequence != previous_trace_sequence:
                            owned_trace_sequence = trace_sequence
                            self._goto_trace_sequence = trace_sequence
                    elif trace_sequence != owned_trace_sequence:
                        _LOGGER.debug("Q10 goto task was replaced by another cleaning session")
                        return

                    if (
                        owned_trace_sequence is not None
                        and self._status.clean_task_type is YXDeviceCleanTask.DIVIDE_AREAS
                        and self._status.status
                        not in {
                            YXDeviceState.IDLE,
                            YXDeviceState.PAUSED,
                            YXDeviceState.RETURNING_HOME,
                            YXDeviceState.CHARGING,
                        }
                    ):
                        owned_task_seen = True

                    if owned_task_seen and self._status.clean_task_type is not YXDeviceCleanTask.DIVIDE_AREAS:
                        _LOGGER.debug("Q10 goto task was replaced by another task type")
                        return

                    if owned_task_seen and self._status.status in {
                        YXDeviceState.IDLE,
                        YXDeviceState.PAUSED,
                        YXDeviceState.RETURNING_HOME,
                        YXDeviceState.CHARGING,
                    }:
                        return

                    if (
                        owned_trace_sequence is not None
                        and (position := self._map.roborock_position) is not None
                        and hypot(position.x - x, position.y - y) <= _GOTO_TOLERANCE
                    ):
                        try:
                            await self._command.send(command=B01_Q10_DP.PAUSE, params=0)
                        except RoborockException as err:
                            _LOGGER.warning("Failed to pause completed Q10 goto task; retrying: %s", err)
                        else:
                            return

                    update_event.clear()
                    try:
                        async with asyncio.timeout(_GOTO_RETRY_INTERVAL):
                            await update_event.wait()
                    except TimeoutError:
                        pass
        except TimeoutError:
            if (
                owned_trace_sequence is not None
                and self._map.trace_sequence == owned_trace_sequence
                and self._status.clean_task_type is YXDeviceCleanTask.DIVIDE_AREAS
            ):
                _LOGGER.warning(
                    "Q10 vacuum did not reach goto target (%s, %s) within %s seconds; stopping zone task",
                    x,
                    y,
                    _GOTO_TIMEOUT,
                )
                try:
                    await self._command.send(command=B01_Q10_DP.STOP, params=0)
                except RoborockException as err:
                    _LOGGER.warning("Failed to stop timed-out Q10 goto task: %s", err)
        finally:
            remove_map_listener()
            remove_status_listener()
            if self._goto_monitor_task is current_task:
                self._goto_monitor_task = None
                self._goto_trace_sequence = None

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
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        clean_count: int = 1,
    ) -> None:
        """Clean one rectangular zone in the common Roborock coordinate space."""
        encoded_zone = _encode_zone(x1, y1, x2, y2, clean_count)
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            params={
                "cmd": YXDeviceCleanTask.DIVIDE_AREAS.code,
                # "clean_paramters" is the spelling required by the firmware.
                "clean_paramters": encoded_zone,
            },
        )
        self.cancel_goto()

    async def goto_position(self, x: int, y: int) -> None:
        """Move to a coordinate using an owned 40 cm zone-clean task."""
        if (position := self._map.roborock_position) is not None and hypot(
            position.x - x, position.y - y
        ) <= _GOTO_TOLERANCE:
            if (
                self._goto_monitor_task is not None
                and self._goto_trace_sequence is not None
                and self._map.trace_sequence == self._goto_trace_sequence
                and self._status.clean_task_type is YXDeviceCleanTask.DIVIDE_AREAS
            ):
                await self._command.send(command=B01_Q10_DP.PAUSE, params=0)
                self.cancel_goto()
            return

        previous_trace_sequence = self._map.trace_sequence
        encoded_zone = _encode_zone(
            x - _GOTO_HALF_ZONE_SIZE,
            y - _GOTO_HALF_ZONE_SIZE,
            x + _GOTO_HALF_ZONE_SIZE,
            y + _GOTO_HALF_ZONE_SIZE,
            1,
        )
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            params={
                "cmd": YXDeviceCleanTask.DIVIDE_AREAS.code,
                "clean_paramters": encoded_zone,
            },
        )
        self.cancel_goto()
        self._goto_monitor_task = asyncio.create_task(
            self._async_monitor_goto_target(x, y, previous_trace_sequence),
            name="roborock_q10_goto",
        )

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

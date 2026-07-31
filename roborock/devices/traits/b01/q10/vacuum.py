"""Traits for Q10 B01 devices."""

from base64 import b64encode
from struct import error as StructError
from struct import pack

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXDeviceCleanTask,
    YXFanLevel,
)

from .command import CommandTrait
from .coordinates import roborock_to_vector_coordinate

_ZONE_NAME_FIELD_LENGTH = 19


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

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the VacuumTrait."""
        self._command = command

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
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            params={
                "cmd": YXDeviceCleanTask.DIVIDE_AREAS.code,
                # "clean_paramters" is the spelling required by the firmware.
                "clean_paramters": _encode_zone(x1, y1, x2, y2, clean_count),
            },
        )

    async def spot_clean(self) -> None:
        """Start a spot / part clean around the robot's current position.

        Verified live: ``{"dps": {"201": 5}}`` (clean_task_type -> 5).
        """
        await self._command.send(command=B01_Q10_DP.START_CLEAN, params=5)

    async def pause_clean(self) -> None:
        """Pause the current task. Verified live: ``{"dps": {"204": 0}}``."""
        await self._command.send(command=B01_Q10_DP.PAUSE, params=0)

    async def resume_clean(self) -> None:
        """Resume a paused task. Verified live: ``{"dps": {"205": 0}}``."""
        await self._command.send(command=B01_Q10_DP.RESUME, params=0)

    async def stop_clean(self) -> None:
        """Stop / cancel the current task. Verified live: ``{"dps": {"206": 0}}``."""
        await self._command.send(command=B01_Q10_DP.STOP, params=0)

    async def return_to_dock(self) -> None:
        """Send the robot back to the dock to charge.

        Uses ``dpStartBack`` (202) with the back-dock task code ``5`` (charge),
        matching the official app. Verified live: ``{"dps": {"202": 5}}`` puts the
        robot into the returning state. (The other back-dock codes are ``1`` =
        wash mop en route and ``4`` = collect dust en route.)
        """
        await self._command.send(command=B01_Q10_DP.START_BACK, params=5)

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

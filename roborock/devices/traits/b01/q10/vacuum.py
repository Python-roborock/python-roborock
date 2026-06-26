"""Traits for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXFanLevel,
)

from .command import CommandTrait


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

        The ``dpStartClean`` (201) command takes a bare integer task code:
        ``1`` = whole-home, ``2`` = segment/room, ``3`` = zone, ``4`` = build map,
        ``5`` = spot. Whole-home and spot take no extra parameters; segment and
        zone need a room/zone selection whose payload shape is not yet known, so
        only whole-home (here) and spot (:meth:`spot_clean`) are exposed.

        Verified live against ss07 hardware: ``{"dps": {"201": 1}}`` starts a
        whole-home clean (clean_task_type -> 1).
        """
        await self._command.send(command=B01_Q10_DP.START_CLEAN, params=1)

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

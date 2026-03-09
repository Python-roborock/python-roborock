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
        """Start cleaning."""
        await self._command.send(
            command=B01_Q10_DP.START_CLEAN,
            # TODO: figure out other commands
            # 1 = start cleaning
            # 2 = "electoral" clean, also has "clean_parameters"
            # 4 = fast create map
            params={"cmd": 1},
        )

    async def pause_clean(self) -> None:
        """Pause cleaning."""
        await self._command.send(
            command=B01_Q10_DP.PAUSE,
            params={},
        )

    async def resume_clean(self) -> None:
        """Resume cleaning."""
        await self._command.send(
            command=B01_Q10_DP.RESUME,
            params={},
        )

    async def stop_clean(self) -> None:
        """Stop cleaning."""
        await self._command.send(
            command=B01_Q10_DP.STOP,
            params={},
        )

    async def return_to_dock(self) -> None:
        """Return to dock."""
        await self._command.send(
            command=B01_Q10_DP.START_DOCK_TASK,
            params={},
        )

    async def empty_dustbin(self) -> None:
        """Empty the dustbin at the dock."""
        await self._command.send(
            command=B01_Q10_DP.START_DOCK_TASK,
            params=2,  # 2 = dock task type for "empty dustbin"
        )

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

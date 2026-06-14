"""Settings writer trait for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP

from .command import CommandTrait


class SettingsTrait:
    """Trait for changing Q10 device settings.

    Q10 setting writes must be wrapped in the ``dpCommon`` (101) data point, e.g.
    setting the volume sends ``{"dps": {"101": {"26": <value>}}}``. Writing the
    bare data point (without the ``dpCommon`` wrapper) is silently ignored by the
    device. The corresponding values can be read back from ``StatusTrait`` after
    a refresh.
    """

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the SettingsTrait."""
        self._command = command

    async def _write(self, dp: B01_Q10_DP, value: int) -> None:
        """Write a single data point value via the dpCommon (101) wrapper."""
        await self._command.send(B01_Q10_DP.COMMON, {str(dp.code): value})

    async def set_volume(self, volume: int) -> None:
        """Set the speaker volume (0-100)."""
        if not 0 <= volume <= 100:
            raise ValueError("volume must be between 0 and 100")
        await self._write(B01_Q10_DP.VOLUME, volume)

    async def set_child_lock(self, enabled: bool) -> None:
        """Enable or disable the child lock."""
        await self._write(B01_Q10_DP.CHILD_LOCK, int(enabled))

    async def set_do_not_disturb(self, enabled: bool) -> None:
        """Enable or disable Do Not Disturb."""
        await self._write(B01_Q10_DP.NOT_DISTURB, int(enabled))

    async def set_button_light(self, enabled: bool) -> None:
        """Enable or disable the indicator / button light (LED)."""
        await self._write(B01_Q10_DP.BUTTON_LIGHT_SWITCH, int(enabled))

    async def set_dust_collection(self, enabled: bool) -> None:
        """Enable or disable automatic dust collection at the dock."""
        await self._write(B01_Q10_DP.DUST_SWITCH, int(enabled))

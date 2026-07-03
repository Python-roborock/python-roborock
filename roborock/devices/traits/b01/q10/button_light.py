"""Indicator / button light (LED) trait for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP

from .command import CommandTrait


class ButtonLightTrait:
    """Trait for controlling the indicator / button light (LED) of a Q10 device.

    The device does not report the button-light state in its status dump, so
    this trait is write-only (no read-back).
    """

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the button light trait."""
        self._command = command

    async def _write(self, value: int) -> None:
        """Write the button-light data point via the dpCommon (101) wrapper."""
        await self._command.send(B01_Q10_DP.COMMON, {str(B01_Q10_DP.BUTTON_LIGHT_SWITCH.code): value})

    async def enable(self) -> None:
        """Turn the indicator light on."""
        await self._write(1)

    async def disable(self) -> None:
        """Turn the indicator light off."""
        await self._write(0)

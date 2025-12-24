"""Clean control trait for Q10 devices."""

from dataclasses import dataclass

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXBackType,
    YXDeviceWorkMode,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.devices.traits.b01.q10.common import Q10TraitMixin


@dataclass
class Q10CleanControlTrait(Q10TraitMixin):
    """Trait for controlling the cleaning process of Q10 devices."""

    async def start_clean(self) -> None:
        """Start cleaning."""
        await self.send_dp(B01_Q10_DP.START_CLEAN, {"cmd": 1})

    async def stop_clean(self) -> None:
        """Stop cleaning."""
        await self.send_dp(B01_Q10_DP.STOP, 0)

    async def pause_clean(self) -> None:
        """Pause cleaning."""
        await self.send_dp(B01_Q10_DP.PAUSE, 0)

    async def resume_clean(self) -> None:
        """Resume cleaning."""
        await self.send_dp(B01_Q10_DP.RESUME, 0)

    async def return_to_dock(self) -> None:
        """Return to dock."""
        await self.send_dp(B01_Q10_DP.START_BACK, YXBackType.BACK_CHARGING.code)

    async def find_me(self) -> None:
        """Locate the robot."""
        await self.send_public(B01_Q10_DP.SEEK, {"seek": 1})

    async def set_fan_speed(self, fan_speed: YXFanLevel) -> None:
        """Set the fan speed."""
        await self.send_dp(B01_Q10_DP.FUN_LEVEL, fan_speed.code)

    async def set_water_level(self, water_level: YXWaterLevel) -> None:
        """Set the water level."""
        await self.send_dp(B01_Q10_DP.WATER_LEVEL, water_level.code)

    async def set_work_mode(self, work_mode: YXDeviceWorkMode) -> None:
        """Set the work mode."""
        await self.send_dp(B01_Q10_DP.CLEAN_TASK_TYPE, work_mode.code)

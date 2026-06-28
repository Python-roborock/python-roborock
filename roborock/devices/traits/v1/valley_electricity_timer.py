import datetime

from roborock.data import ValleyElectricityTimer
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_ENABLED_PARAM = "enabled"


class ValleyElectricityTimerTrait(ValleyElectricityTimer, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for managing Valley Electricity Timer settings on Roborock devices."""

    command = RoborockCommand.GET_VALLEY_ELECTRICITY_TIMER
    converter = common.DefaultConverter(ValleyElectricityTimer)
    requires_feature = "is_supported_valley_electricity"

    @property
    def is_on(self) -> bool:
        """Return whether the Valley Electricity Timer is enabled."""
        return self.enabled == 1

    async def set_timer(self, timer: ValleyElectricityTimer) -> None:
        """Set the Valley Electricity Timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER, params=timer.as_list())
        await self.refresh()

    async def set_start_time(self, start_time: datetime.time) -> None:
        """Set the start time of the Valley Electricity Timer."""
        timer = ValleyElectricityTimer(
            start_hour=start_time.hour,
            start_minute=start_time.minute,
            end_hour=self.end_hour,
            end_minute=self.end_minute,
            enabled=self.enabled,
        )
        await self.rpc_channel.send_command(RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER, params=timer.as_list())
        await self.refresh()

    async def set_end_time(self, end_time: datetime.time) -> None:
        """Set the end time of the Valley Electricity Timer."""
        timer = ValleyElectricityTimer(
            start_hour=self.start_hour,
            start_minute=self.start_minute,
            end_hour=end_time.hour,
            end_minute=end_time.minute,
            enabled=self.enabled,
        )
        await self.rpc_channel.send_command(RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER, params=timer.as_list())
        await self.refresh()

    async def clear_timer(self) -> None:
        """Clear the Valley Electricity Timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CLOSE_VALLEY_ELECTRICITY_TIMER)
        await self.refresh()

    async def enable(self) -> None:
        """Enable the Valley Electricity Timer settings of the device."""
        await self.rpc_channel.send_command(
            RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER,
            params=self.as_list(),
        )
        # Optimistic update to avoid an extra refresh
        self.enabled = 1

    async def disable(self) -> None:
        """Disable the Valley Electricity Timer settings of the device."""
        await self.rpc_channel.send_command(
            RoborockCommand.CLOSE_VALLEY_ELECTRICITY_TIMER,
        )
        # Optimistic update to avoid an extra refresh
        self.enabled = 0

from roborock.data import DnDTimer
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_ENABLED_PARAM = "enabled"


class DoNotDisturbTrait(DnDTimer, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    command = RoborockCommand.GET_DND_TIMER

    @property
    def is_on(self) -> bool:
        """Return whether the Do Not Disturb (DND) timer is enabled."""
        return self.enabled == 1

    async def set_dnd_timer(self, dnd_timer: DnDTimer) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.SET_DND_TIMER, params=dnd_timer.as_dict())

    async def clear_dnd_timer(self) -> None:
        """Clear the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CLOSE_DND_TIMER)

    async def enable(self) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(
            RoborockCommand.SET_DND_TIMER,
            params=[
                self.start_hour,
                self.start_minute,
                self.end_hour,
                self.end_minute,
            ],
        )

    async def disable(self) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CLOSE_DND_TIMER)

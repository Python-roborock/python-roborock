from roborock.containers import DnDTimer
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DoNotDisturbTrait(DnDTimer, common.V1TraitMixin):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    command = RoborockCommand.GET_DND_TIMER

    async def set_dnd_timer(self, dnd_timer: DnDTimer) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.SET_DND_TIMER, params=dnd_timer.as_dict())

    async def clear_dnd_timer(self) -> None:
        """Clear the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CLOSE_DND_TIMER)

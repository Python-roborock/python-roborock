from roborock.data import LedStatus
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

from .common import V1ResponseData


class LedStatusTrait(LedStatus, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for controlling the LED status of a Roborock device."""

    command = RoborockCommand.GET_LED_STATUS
    requires_feature = "is_led_status_switch_supported"

    @property
    def is_on(self) -> bool:
        """Return whether the LED status is enabled."""
        return self.status == 1

    async def enable(self) -> None:
        """Enable the LED status."""
        await self.rpc_channel.send_command(RoborockCommand.SET_LED_STATUS, params=[1])

    async def disable(self) -> None:
        """Disable the LED status."""
        await self.rpc_channel.send_command(RoborockCommand.SET_LED_STATUS, params=[0])

    @classmethod
    def _parse_type_response(cls, response: V1ResponseData) -> LedStatus:
        """Parse the response from the device into a a RoborockBase.

        Subclasses should override this method to implement custom parsing
        logic as needed.
        """
        if not isinstance(response, list):
            raise ValueError(f"Unexpected {cls} response format: {response!r}")
        response = response[0]
        if not isinstance(response, int):
            raise ValueError(f"Unexpected {cls} response format: {response!r}")
        return cls.from_dict({"status": response})

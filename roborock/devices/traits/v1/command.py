from typing import Any

from roborock import RoborockCommand
from roborock.protocols.v1_protocol import ParamsType


class CommandTrait:
    """Trait for sending commands to Roborock devices.

    This trait allows sending raw commands directly to the device. It is particularly
    useful for:
    1.  **Cleaning Control**: Sending commands like `app_start`, `app_stop`, `app_pause`,
        or `app_charge` which don't belong to a specific state trait.
    2.  **Unsupported Features**: Accessing device functionality that hasn't been
        mapped to a specific trait yet.

    See `roborock.roborock_typing.RoborockCommand` for a list of available commands.
    """

    def __post_init__(self) -> None:
        """Post-initialization to set up the RPC channel.

        This is called automatically after the dataclass is initialized by the
        device setup code.
        """
        self._rpc_channel = None

    async def clean_segments(self, segment_ids: list[int]) -> None:
        """Start cleaning the given segments (rooms) of the current map.

        Segment ids are the `segment_id` values reported by the `rooms` trait.
        """
        await self.send(RoborockCommand.APP_SEGMENT_CLEAN, params=[{"segments": segment_ids}])

    async def send(self, command: RoborockCommand | str, params: ParamsType = None) -> Any:
        """Send a command to the device.

        Sending a raw command to the device using this method does not update
        the internal state of any other traits. It is the responsibility of the
        caller to ensure that any traits affected by the command are refreshed
        as needed.
        """
        if not self._rpc_channel:
            raise ValueError("Device trait in invalid state")
        return await self._rpc_channel.send_command(command, params=params)

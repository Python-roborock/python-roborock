"""Remote (manual) control trait for B01 Q7 devices."""

from roborock.data.b01_q7.b01_q7_code_mappings import Q7RemoteDirection
from roborock.devices.rpc.b01_q7_channel import Q7RpcChannel
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

# ``sweep_type`` values observed while the official app drives the remote control.
_MANUAL_SWEEP_TYPE = 5
_NORMAL_SWEEP_TYPE = 0


class RemoteTrait:
    """Trait for driving a Q7 manually, mirroring the Q10 ``RemoteTrait`` API.

    Manual mode is entered with ``prop.set sweep_type=5`` (the device then reports
    ``work_mode`` manual). Each movement command only moves the robot for a short
    burst, so callers repeat it (the official app sends several per second) while
    a direction is held.
    """

    def __init__(self, channel: Q7RpcChannel) -> None:
        """Initialize the RemoteTrait."""
        self._channel = channel

    async def _send_direction(self, direction: Q7RemoteDirection) -> None:
        await self._channel.send_command(RoborockB01Q7Methods.SET_DIRECTION, {"direction": direction.code})

    async def stop(self) -> None:
        """Stop moving, entering manual (remote control) mode if needed."""
        await self._channel.send_command(
            RoborockB01Q7Methods.SET_PROP,
            {RoborockB01Props.SWEEP_TYPE: _MANUAL_SWEEP_TYPE},
        )

    async def forward(self) -> None:
        """Move forward."""
        await self._send_direction(Q7RemoteDirection.FORWARD)

    async def left(self) -> None:
        """Turn left."""
        await self._send_direction(Q7RemoteDirection.LEFT)

    async def right(self) -> None:
        """Turn right."""
        await self._send_direction(Q7RemoteDirection.RIGHT)

    async def exit_remote(self) -> None:
        """Exit remote control and return to the normal idle state."""
        await self._send_direction(Q7RemoteDirection.EXIT)
        await self._channel.send_command(
            RoborockB01Q7Methods.SET_PROP,
            {RoborockB01Props.SWEEP_TYPE: _NORMAL_SWEEP_TYPE},
        )

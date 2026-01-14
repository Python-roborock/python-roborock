from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import send_command
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.protocols.b01_q10_protocol import ParamsType


class CommandTrait:
    """Trait for sending commands to Q10 Roborock devices.

    This trait allows sending raw commands directly to the device. It is particularly
    useful for accessing features that do not have their own traits. Generally
    it is preferred to use specific traits for device functionality when
    available.
    """

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the CommandTrait."""
        self._channel = channel

    async def send(self, command: B01_Q10_DP, params: ParamsType = None) -> Any:
        """Send a command to the device.

        Sending a raw command to the device using this method does not update
        the internal state of any other traits. It is the responsibility of the
        caller to ensure that any traits affected by the command are refreshed
        as needed.
        """
        if not self._channel:
            raise ValueError("Device trait in invalid state")
        return await send_command(self._channel, command, params=params)

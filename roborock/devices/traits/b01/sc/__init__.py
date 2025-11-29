"""Traits for SC B01 devices.
Right now, the only known Q7 devices are sc devices."""

from roborock import RoborockB01Methods
from roborock.devices.b01_channel import send_decoded_command
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait
from roborock.roborock_message import RoborockB01Props

__all__ = [
    "PropertiesApi",
]


class PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel

    async def query_values(self, props: list[RoborockB01Props]) -> None:
        """Query the device for the values of the given Dyad protocols."""
        await send_decoded_command(
            self._channel, dps=10000, command=RoborockB01Methods.GET_PROP, params={"property": props}
        )


def create(channel: MqttChannel) -> PropertiesApi:
    """Create traits for B01 devices."""
    return PropertiesApi(channel)

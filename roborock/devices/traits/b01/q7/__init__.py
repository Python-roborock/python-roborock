"""Traits for Q7 B01 devices.
Potentially other devices may fall into this category in the future."""

from roborock import B01Props
from roborock.devices.b01_channel import send_decoded_command
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

__all__ = [
    "Q7PropertiesApi",
]


class Q7PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel

    async def query_values(self, props: list[RoborockB01Props]) -> B01Props | None:
        """Query the device for the values of the given Q7 properties."""
        result = await send_decoded_command(
            self._channel, dps=10000, command=RoborockB01Q7Methods.GET_PROP, params={"property": props}
        )
        return B01Props.from_dict(result)


def create(channel: MqttChannel) -> Q7PropertiesApi:
    """Create traits for B01 devices."""
    return Q7PropertiesApi(channel)

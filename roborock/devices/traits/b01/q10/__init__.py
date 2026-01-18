"""Traits for Q10 B01 devices."""

from typing import Any

from roborock.devices.rpc.b01_q7_channel import send_decoded_command
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel

from .command import CommandTrait

__all__ = [
    "Q10PropertiesApi",
]


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    command: CommandTrait
    """Trait for sending commands to Q10 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self.command = CommandTrait(channel)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)

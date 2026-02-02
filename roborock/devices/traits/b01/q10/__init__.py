"""Traits for Q10 B01 devices."""

from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel

from .command import CommandTrait
from .status import StatusTrait
from .vacuum import VacuumTrait

__all__ = [
    "Q10PropertiesApi",
    "StatusTrait",
]


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    command: CommandTrait
    """Trait for sending commands to Q10 devices."""

    vacuum: VacuumTrait
    """Trait for sending vacuum related commands to Q10 devices."""

    status: StatusTrait
    """Trait for reading device status values."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self.command = CommandTrait(channel)
        self.vacuum = VacuumTrait(self.command)
        self.status = StatusTrait(channel)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)

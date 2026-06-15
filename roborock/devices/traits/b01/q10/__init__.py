"""Traits for Q10 B01 devices."""

import asyncio
import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import stream_decoded_responses
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel

from .button_light import ButtonLightTrait
from .child_lock import ChildLockTrait
from .command import CommandTrait
from .consumable import ConsumableTrait
from .do_not_disturb import DoNotDisturbTrait
from .dust_collection import DustCollectionTrait
from .network_info import NetworkInfoTrait
from .remote import RemoteTrait
from .status import StatusTrait
from .vacuum import VacuumTrait
from .volume import SoundVolumeTrait

__all__ = [
    "Q10PropertiesApi",
    "ButtonLightTrait",
    "ChildLockTrait",
    "ConsumableTrait",
    "DoNotDisturbTrait",
    "DustCollectionTrait",
    "NetworkInfoTrait",
    "SoundVolumeTrait",
    "StatusTrait",
]

_LOGGER = logging.getLogger(__name__)


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    command: CommandTrait
    """Trait for sending commands to Q10 devices."""

    status: StatusTrait
    """Trait for managing the core status of Q10 devices."""

    vacuum: VacuumTrait
    """Trait for sending vacuum related commands to Q10 devices."""

    remote: RemoteTrait
    """Trait for sending remote control related commands to Q10 devices."""

    volume: SoundVolumeTrait
    """Trait for reading / setting the speaker volume."""

    child_lock: ChildLockTrait
    """Trait for reading / controlling the child lock."""

    do_not_disturb: DoNotDisturbTrait
    """Trait for reading / controlling Do Not Disturb."""

    dust_collection: DustCollectionTrait
    """Trait for reading / controlling dock auto-empty (dust collection)."""

    button_light: ButtonLightTrait
    """Trait for controlling the indicator / button light (LED)."""

    network_info: NetworkInfoTrait
    """Trait exposing the device's network information."""

    consumable: ConsumableTrait
    """Trait exposing remaining life of consumables."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self.command = CommandTrait(channel)
        self.vacuum = VacuumTrait(self.command)
        self.remote = RemoteTrait(self.command)
        self.status = StatusTrait()
        self.volume = SoundVolumeTrait(self.command)
        self.child_lock = ChildLockTrait(self.command)
        self.do_not_disturb = DoNotDisturbTrait(self.command)
        self.dust_collection = DustCollectionTrait(self.command)
        self.button_light = ButtonLightTrait(self.command)
        self.network_info = NetworkInfoTrait()
        self.consumable = ConsumableTrait()
        # Read-model traits updated from the device's DPS push stream.
        self._updatable_traits = [
            self.status,
            self.volume,
            self.child_lock,
            self.do_not_disturb,
            self.dust_collection,
            self.network_info,
            self.consumable,
        ]
        self._subscribe_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start any necessary subscriptions for the trait."""
        self._subscribe_task = asyncio.create_task(self._subscribe_loop())

    async def close(self) -> None:
        """Close any resources held by the trait."""
        if self._subscribe_task is not None:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass  # ignore cancellation errors
            self._subscribe_task = None

    async def refresh(self) -> None:
        """Refresh all traits."""
        # Sending the REQUEST_DPS will cause the device to send all DPS values
        # to the device. Updates will be received by the subscribe loop below.
        await self.command.send(B01_Q10_DP.REQUEST_DPS, params={})

    async def _subscribe_loop(self) -> None:
        """Persistent loop to listen for status updates."""
        async for decoded_dps in stream_decoded_responses(self._channel):
            _LOGGER.debug("Received Q10 status update: %s", decoded_dps)

            # Notify all read-model traits about the new message; each trait
            # only updates the fields that it is responsible for.
            for trait in self._updatable_traits:
                trait.update_from_dps(decoded_dps)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)

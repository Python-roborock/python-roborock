"""Traits for Q10 B01 devices."""

import asyncio
import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import B01Q10Channel
from roborock.devices.traits import Trait
from roborock.map.b01_q10_map_parser import Q10MapPacket, Q10TracePacket
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate, Q10Message

from .button_light import ButtonLightTrait
from .child_lock import ChildLockTrait
from .clean_history import CleanHistoryTrait
from .command import CommandTrait
from .consumable import ConsumableTrait
from .do_not_disturb import DoNotDisturbTrait
from .dust_collection import DustCollectionTrait
from .map import MapContentTrait
from .network_info import NetworkInfoTrait
from .remote import RemoteTrait
from .status import StatusTrait
from .vacuum import VacuumTrait
from .volume import SoundVolumeTrait

__all__ = [
    "Q10PropertiesApi",
    "ButtonLightTrait",
    "ChildLockTrait",
    "CleanHistoryTrait",
    "ConsumableTrait",
    "DoNotDisturbTrait",
    "DustCollectionTrait",
    "MapContentTrait",
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

    map: MapContentTrait
    """Trait for fetching the current parsed map (image + rooms)."""

    clean_history: CleanHistoryTrait
    """Trait for fetching the device clean-record history (``dpCleanRecord``)."""

    def __init__(self, channel: B01Q10Channel) -> None:
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
        self.map = MapContentTrait()
        self.clean_history = CleanHistoryTrait(self.command)
        # Read-model traits updated from the device's DPS push stream.
        self._updatable_traits = [
            self.status,
            self.volume,
            self.child_lock,
            self.do_not_disturb,
            self.dust_collection,
            self.network_info,
            self.consumable,
            self.clean_history,
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
        """Persistent loop dispatching decoded messages to the read-model traits."""
        async for message in self._channel.subscribe_stream():
            self._handle_message(message)

    def _handle_message(self, message: Q10Message) -> None:
        """Route a single decoded message to the trait responsible for it.

        Map and trace packets arrive as protocol-301 ``MAP_RESPONSE`` pushes (the
        Q10 is entirely push-driven: there is no synchronous get-map request, a
        ``dpRequestDps`` just nudges the device to publish its current map). DPS
        updates feed the read-model traits. More traits can be dispatched here below.
        """
        if isinstance(message, Q10MapPacket):
            self.map.update_from_map_packet(message)
        elif isinstance(message, Q10TracePacket):
            self.map.update_from_trace_packet(message)
        elif isinstance(message, Q10DpsUpdate):
            _LOGGER.debug("Received Q10 status update: %s", message.dps)
            # Notify all read-model traits about the new message; each trait
            # only updates the fields that it is responsible for.
            for trait in self._updatable_traits:
                trait.update_from_dps(message.dps)


def create(channel: B01Q10Channel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)

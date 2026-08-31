"""Traits for Q10 B01 devices."""

import asyncio
import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import RoborockBase
from roborock.devices.rpc.b01_q10_channel import B01Q10Channel
from roborock.devices.traits import Trait
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10MapPacket,
    Q10MapPacketKind,
    Q10TracePacket,
)
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate, Q10Message

from .button_light import ButtonLightTrait
from .child_lock import ChildLockTrait
from .clean_history import CleanHistoryTrait
from .command import CommandTrait
from .consumable import ConsumableTrait
from .do_not_disturb import DoNotDisturbTrait
from .dust_collection import DustCollectionTrait
from .map import MapContentTrait, MapDpsTrait
from .maps import MapsTrait
from .network_info import NetworkInfoTrait
from .remote import RemoteTrait
from .room_cleaning import RoomCleaningTrait
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
    "MapsTrait",
    "NetworkInfoTrait",
    "RoomCleaningTrait",
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

    room_cleaning: RoomCleaningTrait
    """Trait for customized per-room cleaning settings and commands."""

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
    """Composed map image plus caller-facing map and trace data."""

    maps: MapsTrait
    """Saved-map list metadata."""

    _map_dps: MapDpsTrait
    """Private source of restricted zones and virtual walls received through DPS."""

    clean_history: CleanHistoryTrait
    """Trait for fetching the device clean-record history (``dpCleanRecord``)."""

    def __init__(
        self,
        channel: B01Q10Channel,
        *,
        model: str | None = None,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self.command = CommandTrait(channel)
        advanced_cleaning_supported = model is None or model == "roborock.vacuum.ss07"
        self.vacuum = VacuumTrait(self.command, advanced_cleaning_supported=advanced_cleaning_supported)
        self.remote = RemoteTrait(self.command)
        self.room_cleaning = RoomCleaningTrait(self.command, supported=advanced_cleaning_supported)
        self.status = StatusTrait()
        self.volume = SoundVolumeTrait(self.command)
        self.child_lock = ChildLockTrait(self.command)
        self.do_not_disturb = DoNotDisturbTrait(self.command)
        self.dust_collection = DustCollectionTrait(self.command)
        self.button_light = ButtonLightTrait(self.command)
        self.network_info = NetworkInfoTrait()
        self.consumable = ConsumableTrait()
        self._map_dps = MapDpsTrait()
        self.maps = MapsTrait(
            self.command,
            map_parser_config=map_parser_config,
            map_changed_callback=self.room_cleaning.invalidate,
        )
        self.map = MapContentTrait(
            self._map_dps,
            self.command,
            map_parser_config=map_parser_config,
        )
        self.clean_history = CleanHistoryTrait(
            self.command,
            map_parser_config=map_parser_config,
        )
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
            self._map_dps,
            self.maps,
            self.room_cleaning,
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
        # Sending REQUEST_DPS causes the device to publish its ordinary status
        # values. Map, map-list, and customized-room settings have separate
        # refresh methods so callers can schedule those larger responses.
        await self.command.send(B01_Q10_DP.REQUEST_DPS, params={})

    async def _subscribe_loop(self) -> None:
        """Persistent loop dispatching decoded messages to the read-model traits."""
        async for message in self._channel.subscribe_stream():
            self._handle_message(message)

    def _handle_message(self, message: Q10Message) -> None:
        """Route a single decoded message to the trait responsible for it.

        Map and trace packets arrive as protocol-301 ``MAP_RESPONSE`` pushes.
        Map-list DPS responses and other DPS updates feed the read-model traits.
        """
        if isinstance(message, Q10MapPacket):
            if message.kind is Q10MapPacketKind.CURRENT:
                self.map.update_from_map_packet(message)
            elif message.kind is Q10MapPacketKind.CLEAN_RECORD_DETAIL:
                self.clean_history.update_from_map_packet(message)
            elif message.kind is Q10MapPacketKind.SAVED_MAP_DETAIL:
                self.maps.update_from_map_packet(message)
        elif isinstance(message, Q10TracePacket):
            self.map.update_from_trace_packet(message)
        elif isinstance(message, Q10DpsUpdate):
            _LOGGER.debug("Received Q10 status update: %s", message.dps)
            # Notify all read-model traits about the new message; each trait
            # only updates the fields that it is responsible for.
            for trait in self._updatable_traits:
                trait.update_from_dps(message.dps)

    def as_dict(self) -> dict[str, Any]:
        """Return the trait data as a dictionary."""
        result: dict[str, Any] = {}
        for name, value in self.__dict__.items():
            if isinstance(value, RoborockBase) and not name.startswith("_"):
                result[name] = value.as_dict()
        if hasattr(self, "map") and hasattr(self.map, "as_dict"):
            result["map"] = self.map.as_dict()
        return result


def create(
    channel: B01Q10Channel,
    *,
    model: str | None = None,
    map_parser_config: B01Q10MapParserConfig | None = None,
) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel, model=model, map_parser_config=map_parser_config)

"""Traits for Q10 B01 devices."""

import asyncio
import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import B01Q10Channel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import Q10MapPacket, Q10TracePacket
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate, Q10Message

from .button_light import ButtonLightTrait
from .child_lock import ChildLockTrait
from .clean_history import CleanHistoryTrait
from .command import CommandTrait
from .consumable import ConsumableTrait
from .do_not_disturb import DoNotDisturbTrait
from .dust_collection import DustCollectionTrait
from .map import MapContentTrait, MapDpsTrait
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


def _map_id_from_list_response(response: Any) -> int | str | None:
    """Return the first usable map ID from a ``dpMultiMap`` list response."""
    if not isinstance(response, dict) or response.get("op") != "list":
        return None
    data = response.get("data")
    if not isinstance(data, list):
        return None
    for map_info in data:
        if isinstance(map_info, dict):
            map_id = map_info.get("id")
        else:
            map_id = map_info
        if isinstance(map_id, (int, str)) and not isinstance(map_id, bool):
            return map_id
    return None


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
    """Composed map image plus caller-facing map and trace data."""

    _map_dps: MapDpsTrait
    """Private source of restricted zones and virtual walls received through DPS."""

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
        self._map_dps = MapDpsTrait()
        self.map = MapContentTrait(self._map_dps)
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
            self._map_dps,
        ]
        self._subscribe_task: asyncio.Task[None] | None = None
        self._map_list_requested = False

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
        # Status and map retrieval use separate Q10 requests. A bare REQUEST_DPS
        # reliably refreshes status but does not reliably make every firmware
        # publish its map.
        await self.command.send(B01_Q10_DP.REQUEST_DPS, params={})
        await self.request_map()

    async def request_map(self) -> None:
        """Request the current saved map through the Q10 multi-map protocol.

        The list response arrives asynchronously on the subscribe stream.
        ``_handle_message`` extracts its first map ID and follows up with the
        matching ``get`` command; the resulting protocol-301 map packet is
        routed to :attr:`map`.
        """
        self._map_list_requested = True
        try:
            await self.command.send(
                B01_Q10_DP.COMMON,
                {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
            )
        except RoborockException:
            self._map_list_requested = False
            raise

    async def _subscribe_loop(self) -> None:
        """Persistent loop dispatching decoded messages to the read-model traits."""
        async for message in self._channel.subscribe_stream():
            await self._handle_message(message)

    async def _handle_message(self, message: Q10Message) -> None:
        """Route a single decoded message to the trait responsible for it.

        Map and trace packets arrive as protocol-301 ``MAP_RESPONSE`` pushes.
        A ``dpMultiMap`` list response completes the asynchronous request flow
        started by :meth:`request_map`; other DPS updates feed the read-model
        traits.
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
            await self._request_map_from_list_response(message.dps)

    async def _request_map_from_list_response(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Request map content after receiving our pending map-list response."""
        response = decoded_dps.get(B01_Q10_DP.MULTI_MAP)
        if not self._map_list_requested or not isinstance(response, dict) or response.get("op") != "list":
            return

        self._map_list_requested = False
        if (map_id := _map_id_from_list_response(response)) is None:
            _LOGGER.debug("Q10 map list response did not contain a usable map ID")
            return

        try:
            await self.command.send(
                B01_Q10_DP.COMMON,
                {
                    str(B01_Q10_DP.MULTI_MAP.code): {
                        "op": "get",
                        "id": map_id,
                    }
                },
            )
        except RoborockException as ex:
            # A failed follow-up must not kill the persistent subscribe loop.
            _LOGGER.debug("Failed to request Q10 map content: %s", ex)


def create(channel: B01Q10Channel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)

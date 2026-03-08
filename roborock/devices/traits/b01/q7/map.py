"""Map trait for B01 Q7 devices."""

import asyncio
from dataclasses import dataclass, field

from roborock.data import RoborockBase
from roborock.devices.rpc.b01_q7_channel import send_decoded_command, send_map_command
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import B01_Q7_DPS, Q7RequestMessage
from roborock.roborock_typing import RoborockB01Q7Methods

@dataclass
class Q7MapListEntry(RoborockBase):
    """Single map list entry returned by `service.get_map_list`."""

    id: int | None = None
    cur: bool | None = None


@dataclass
class Q7MapList(RoborockBase):
    """Map list response returned by `service.get_map_list`."""

    map_list: list[Q7MapListEntry] = field(default_factory=list)


class MapTrait(Trait):
    """Map retrieval + map metadata helpers for Q7 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        self._channel = channel
        # Map uploads are serialized per-device to avoid response cross-wiring.
        self._map_command_lock = asyncio.Lock()
        self._map_list: Q7MapList | None = None

    @property
    def map_list(self) -> Q7MapList | None:
        """Latest cached map list metadata, populated by ``refresh()``."""
        return self._map_list

    @property
    def current_map_id(self) -> int | None:
        """Current map id derived from cached map list metadata."""
        if self._map_list is None:
            return None
        return self._extract_current_map_id(self._map_list)

    async def refresh(self) -> None:
        """Refresh cached map list metadata from the device."""
        response = await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=B01_Q7_DPS, command=RoborockB01Q7Methods.GET_MAP_LIST, params={}),
        )
        if not isinstance(response, dict):
            raise TypeError(f"Unexpected response type for GET_MAP_LIST: {type(response).__name__}: {response!r}")

        parsed = Q7MapList.from_dict(response)
        if parsed is None:
            raise TypeError(f"Failed to decode map list response: {response!r}")

        self._map_list = parsed

    async def _get_map_payload(self, *, map_id: int) -> bytes:
        """Fetch raw map payload bytes for the given map id."""
        request = Q7RequestMessage(
            dps=B01_Q7_DPS,
            command=RoborockB01Q7Methods.UPLOAD_BY_MAPID,
            params={"map_id": map_id},
        )
        async with self._map_command_lock:
            return await send_map_command(self._channel, request)

    async def get_current_map_payload(self) -> bytes:
        """Fetch raw map payload bytes for the currently selected map."""
        if self._map_list is None:
            await self.refresh()

        map_id = self.current_map_id
        if map_id is None:
            raise RoborockException(f"Unable to determine map_id from map list response: {self._map_list!r}")
        return await self._get_map_payload(map_id=map_id)

    @staticmethod
    def _extract_current_map_id(map_list_response: Q7MapList) -> int | None:
        map_list = map_list_response.map_list
        if not map_list:
            return None

        for entry in map_list:
            if entry.cur and isinstance(entry.id, int):
                return entry.id

        first = map_list[0]
        if isinstance(first.id, int):
            return first.id
        return None

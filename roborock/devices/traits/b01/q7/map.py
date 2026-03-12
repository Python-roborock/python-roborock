"""Map trait for B01 Q7 devices."""

import asyncio

from roborock.data import Q7MapList
from roborock.devices.rpc.b01_q7_channel import send_decoded_command, send_map_command
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import B01_Q7_DPS, Q7RequestMessage
from roborock.roborock_typing import RoborockB01Q7Methods


class MapTrait(Q7MapList, Trait):
    """Map retrieval + map metadata helpers for Q7 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        super().__init__()
        self._channel = channel
        # Map uploads are serialized per-device to avoid response cross-wiring.
        self._map_command_lock = asyncio.Lock()
        self._loaded = False

    async def refresh(self) -> None:
        """Refresh cached map list metadata from the device."""
        response = await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=B01_Q7_DPS, command=RoborockB01Q7Methods.GET_MAP_LIST, params={}),
        )
        if not isinstance(response, dict):
            raise RoborockException(
                f"Unexpected response type for GET_MAP_LIST: {type(response).__name__}: {response!r}"
            )

        if (parsed := Q7MapList.from_dict(response)) is None:
            raise RoborockException(f"Failed to decode map list response: {response!r}")

        self.map_list = parsed.map_list
        self._loaded = True

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
        if not self._loaded:
            await self.refresh()

        map_id = self.current_map_id
        if map_id is None:
            raise RoborockException(f"Unable to determine map_id from map list response: {self!r}")
        return await self._get_map_payload(map_id=map_id)

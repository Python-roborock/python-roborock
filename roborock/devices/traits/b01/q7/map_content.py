"""Map content trait for B01/Q7 devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roborock.devices.rpc.b01_q7_channel import send_decoded_command, send_map_command
from roborock.devices.traits import Trait
from roborock.devices.traits.v1.map_content import MapContent
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import decode_b01_map_payload, parse_scmap_payload, render_map_png
from roborock.protocols.b01_q7_protocol import Q7RequestMessage
from roborock.roborock_typing import RoborockB01Q7Methods


@dataclass
class B01MapContent(MapContent):
    """B01 map content wrapper."""

    rooms: dict[int, str] | None = None


def _extract_current_map_id(map_list_response: dict[str, Any] | None) -> int | None:
    if not isinstance(map_list_response, dict):
        return None
    map_list = map_list_response.get("map_list")
    if not isinstance(map_list, list) or not map_list:
        return None

    for entry in map_list:
        if isinstance(entry, dict) and entry.get("cur") and isinstance(entry.get("id"), int):
            return entry["id"]

    first = map_list[0]
    if isinstance(first, dict) and isinstance(first.get("id"), int):
        return first["id"]
    return None


class Q7MapContentTrait(B01MapContent, Trait):
    """Fetch and parse map content from B01/Q7 devices."""

    def __init__(self, channel: MqttChannel, *, local_key: str, serial: str, model: str) -> None:
        super().__init__()
        self._channel = channel
        self._local_key = local_key
        self._serial = serial
        self._model = model

    async def refresh(self) -> B01MapContent:
        map_list_response = await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=10000, command=RoborockB01Q7Methods.GET_MAP_LIST, params={}),
        )
        map_id = _extract_current_map_id(map_list_response)
        if map_id is None:
            raise RoborockException(f"Unable to determine map_id from map list response: {map_list_response!r}")

        raw_payload = await send_map_command(
            self._channel,
            Q7RequestMessage(
                dps=10000,
                command=RoborockB01Q7Methods.UPLOAD_BY_MAPID,
                params={"map_id": map_id},
            ),
        )
        inflated = decode_b01_map_payload(
            raw_payload,
            local_key=self._local_key,
            serial=self._serial,
            model=self._model,
        )
        parsed = parse_scmap_payload(inflated)
        self.raw_api_response = raw_payload
        self.map_data = None
        self.rooms = parsed.rooms
        self.image_content = render_map_png(parsed)
        return self

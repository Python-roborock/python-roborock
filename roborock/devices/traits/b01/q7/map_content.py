"""Map content trait for B01/Q7 devices."""

from __future__ import annotations

from dataclasses import dataclass

from roborock.devices.rpc.b01_q7_channel import send_map_command
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait
from roborock.devices.traits.v1.map_content import MapContent
from roborock.map.b01_map_parser import decode_b01_map_payload, parse_scmap_payload, render_map_png
from roborock.protocols.b01_q7_protocol import Q7RequestMessage
from roborock.roborock_typing import RoborockB01Q7Methods


@dataclass
class B01MapContent(MapContent):
    """B01 map content wrapper."""


class Q7MapContentTrait(B01MapContent, Trait):
    """Fetch and parse map content from B01/Q7 devices."""

    def __init__(self, channel: MqttChannel, *, local_key: str, serial: str, model: str) -> None:
        super().__init__()
        self._channel = channel
        self._local_key = local_key
        self._serial = serial
        self._model = model

    async def refresh(self) -> B01MapContent:
        raw_payload = await send_map_command(
            self._channel,
            Q7RequestMessage(dps=10000, command=RoborockB01Q7Methods.UPLOAD_BY_MAPTYPE, params={"maptype": 301}),
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
        self.image_content = render_map_png(parsed)
        return self

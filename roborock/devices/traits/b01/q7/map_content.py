"""Trait for fetching parsed map content from B01/Q7 devices.

This intentionally mirrors the v1 `MapContentTrait` contract:
- `refresh()` performs I/O and populates cached fields
- `parse_map_content()` reparses cached raw bytes without I/O
- fields `image_content`, `map_data`, and `raw_api_response` are then readable

For B01/Q7 devices, the underlying raw map payload is retrieved via `MapTrait`.
"""

import asyncio
from dataclasses import dataclass

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.rpc.b01_q7_channel import Q7MapRpcChannel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import B01MapParser, B01MapParserConfig
from roborock.roborock_typing import RoborockB01Q7Methods

from .map import MapTrait

_TRUNCATE_LENGTH = 20


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """Parsed map data (metadata for points on the map)."""

    raw_api_response: bytes | None = None
    """Raw bytes of the map payload from the device.

    This should be treated as an opaque blob used only internally by this
    library to re-parse the map data when needed.
    """

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, map_data={self.map_data!r})"


class MapContentTrait(MapContent, Trait):
    """Trait for fetching parsed map content for Q7 devices."""

    def __init__(
        self,
        map_rpc_channel: Q7MapRpcChannel,
        map_trait: MapTrait,
        *,
        map_parser_config: B01MapParserConfig | None = None,
    ) -> None:
        super().__init__()
        self._map_rpc_channel = map_rpc_channel
        self._map_trait = map_trait
        self._map_parser = B01MapParser(map_parser_config)
        # Map uploads are serialized per-device to avoid response cross-wiring.
        self._map_command_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Fetch, decode, and parse the current map payload.

        This relies on the Map Trait already having fetched the map list metadata
        so it can determine the current map_id.
        """
        # Users must call first
        if (map_id := self._map_trait.current_map_id) is None:
            raise RoborockException("Unable to determine current map ID")

        async with self._map_command_lock:
            raw_payload = await self._map_rpc_channel.send_map_command(
                RoborockB01Q7Methods.UPLOAD_BY_MAPID,
                {"map_id": map_id},
            )

        try:
            parsed_data = self._map_parser.parse(raw_payload)
        except RoborockException:
            raise
        except Exception as ex:
            raise RoborockException("Failed to parse B01 map data") from ex

        if parsed_data.image_content is None:
            raise RoborockException("Failed to render B01 map image")

        self.image_content = parsed_data.image_content
        self.map_data = parsed_data.map_data
        self.raw_api_response = raw_payload

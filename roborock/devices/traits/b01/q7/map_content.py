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
from roborock.devices.rpc.b01_q7_channel import MapRpcChannel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.map.b01_grid_layers import GridCalibration, GridLayers
from roborock.map.b01_map_parser import B01MapParser, B01MapParserConfig, decompose_q7_layers, q7_calibration
from roborock.protocols.b01_q7_protocol import B01_Q7_DPS, Q7RequestMessage
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

    layers: GridLayers | None = None
    """Separable map layers (background / wall / floor) in grid-pixel space.

    Q7's raster has no per-room segmentation, so ``layers.rooms`` is empty (room
    ids/names are in the map metadata)."""

    calibration: GridCalibration | None = None
    """World<->pixel transform, read directly from the SCMap ``mapHead``
    (``minX``/``minY``/``resolution``); world coordinates are in metres."""

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
        map_rpc_channel: MapRpcChannel,
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

        request = Q7RequestMessage(
            dps=B01_Q7_DPS,
            command=RoborockB01Q7Methods.UPLOAD_BY_MAPID,
            params={"map_id": map_id},
        )
        async with self._map_command_lock:
            raw_payload = await self._map_rpc_channel.send_map_command(request)

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
        try:
            self.layers = decompose_q7_layers(raw_payload)
            self.calibration = q7_calibration(raw_payload)
        except RoborockException:
            self.layers = None
            self.calibration = None

"""Trait for fetching parsed map content from B01/Q7 devices.

This intentionally mirrors the v1 `MapContentTrait` contract:
- `refresh()` performs I/O and populates cached fields
- `parse_map_content()` reparses cached raw bytes without I/O
- fields `image_content`, `map_data`, and `raw_api_response` are then readable

For B01/Q7 devices, the underlying raw map payload is retrieved via `MapTrait`.
"""

from __future__ import annotations

from dataclasses import dataclass

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import B01MapParser, B01MapParserConfig

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
        map_trait: MapTrait,
        *,
        serial: str | None,
        model: str | None,
        map_parser_config: B01MapParserConfig | None = None,
    ) -> None:
        super().__init__()
        self._map_trait = map_trait
        self._serial = serial
        self._model = model
        self._map_parser = B01MapParser(map_parser_config)

    async def refresh(self) -> None:
        """Fetch, decode, and parse the current map payload."""
        raw_payload = await self._map_trait.get_current_map_payload()
        parsed = self.parse_map_content(raw_payload)
        self.image_content = parsed.image_content
        self.map_data = parsed.map_data
        self.raw_api_response = parsed.raw_api_response

    def parse_map_content(self, response: bytes) -> MapContent:
        """Parse map content from raw bytes.

        This mirrors the v1 trait behavior so cached map payload bytes can be
        reparsed without going back to the device.
        """
        if not self._serial or not self._model:
            raise RoborockException(
                "B01 map parsing requires device serial number and model metadata, but they were missing"
            )

        try:
            parsed_data = self._map_parser.parse(
                response,
                serial=self._serial,
                model=self._model,
            )
        except RoborockException:
            raise
        except Exception as ex:
            raise RoborockException("Failed to parse B01 map data") from ex

        if parsed_data.image_content is None:
            raise RoborockException("Failed to render B01 map image")

        return MapContent(
            image_content=parsed_data.image_content,
            map_data=parsed_data.map_data,
            raw_api_response=response,
        )

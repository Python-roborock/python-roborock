"""Trait for fetching the map content from Roborock devices."""

import logging
from dataclasses import dataclass

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.traits.v1 import common
from roborock.map.map_parser import MapParser, MapParserConfig
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)

_TRUNCATE_LENGTH = 20


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """The parsed map data which contains metadata for points on the map."""

    raw_api_response: bytes | None = None
    """The raw bytes of the map data from the API for caching for future use.

    This should be treated as an opaque blob used only internally by this library
    to re-parse the map data when needed.
    """

    def __repr__(self) -> str:
        """Return a string representation of the MapContent."""
        img = self.image_content
        if self.image_content and len(self.image_content) > _TRUNCATE_LENGTH:
            img = self.image_content[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, map_data={self.map_data!r})"


@common.map_rpc_channel
class MapContentTrait(MapContent, common.V1TraitMixin):
    """Trait for fetching the map content."""

    command = RoborockCommand.GET_MAP_V1

    def __init__(self, map_parser_config: MapParserConfig | None = None) -> None:
        """Initialize MapContentTrait."""
        super().__init__()
        self._map_parser = MapParser(map_parser_config or MapParserConfig())

    def _parse_response(self, response: common.V1ResponseData) -> MapContent:
        """Parse the response from the device into a MapContentTrait instance."""
        if not isinstance(response, bytes):
            raise ValueError(f"Unexpected MapContentTrait response format: {type(response)}")
        return self.parse_map_content(response)

    def parse_map_content(self, response: bytes) -> MapContent:
        """Parse the map content from raw bytes.

        This method is exposed so that cached map data can be parsed without
        needing to go through the RPC channel.

        Args:
            response: The raw bytes of the map data from the API.

        Returns:
            MapContent: The parsed map content.

        Raises:
            RoborockException: If the map data cannot be parsed.
        """
        parsed_data = self._map_parser.parse(response)
        if parsed_data is None:
            raise ValueError("Failed to parse map data")

        return MapContent(
            image_content=parsed_data.image_content,
            map_data=parsed_data.map_data,
            raw_api_response=response,
        )

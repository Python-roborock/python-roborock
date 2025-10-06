"""Trait for fetching the map content from Roborock devices."""
import logging
from dataclasses import dataclass

from vacuum_map_parser_base.map_data import MapData

from roborock.containers import RoborockBase
from roborock.devices.traits.v1 import common
from roborock.map.map_parser import MapParser, MapParserConfig
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """The parsed map data which contains metadata for points on the map."""


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

        parsed_data = self._map_parser.parse(response)
        if parsed_data is None:
            raise ValueError("Failed to parse map data")

        return MapContent(
            image_content=parsed_data.image_content,
            map_data=parsed_data.map_data,
        )

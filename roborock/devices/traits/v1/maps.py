"""Trait for managing maps and room mappings on Roborock devices.

New datatypes are introduced here to manage the additional information associated
with maps and rooms, such as map names and room names. These override the
base container datatypes to add additional fields.
"""

import logging
from typing import Self

from roborock.data import MultiMapsList, MultiMapsListMapInfo
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

from .status import StatusTrait

_LOGGER = logging.getLogger(__name__)


@common.mqtt_rpc_channel
class MapsTrait(MultiMapsList, common.V1TraitMixin):
    """Trait for managing the maps of Roborock devices.

    A device may have multiple maps, each identified by a unique map_flag.
    Each map can have multiple rooms associated with it, in a `RoomMapping`.

    The MapsTrait depends on the StatusTrait to determine the currently active
    map. It is the responsibility of the caller to ensure that the StatusTrait
    is up to date before using this trait. However, there is a possibility of
    races if another client changes the current map between the time the
    StatusTrait is refreshed and when the MapsTrait is used. This is mitigated
    by the fact that the map list is unlikely to change frequently, and the
    current map is only changed when the user explicitly switches maps.
    """

    command = RoborockCommand.GET_MULTI_MAPS_LIST

    def __init__(self, status_trait: StatusTrait) -> None:
        """Initialize the MapsTrait.

        We keep track of the StatusTrait to ensure we have the latest
        status information when dealing with maps.
        """
        super().__init__()
        self._status_trait = status_trait

    @property
    def current_map(self) -> int | None:
        """Returns the currently active map (map_flag), if available."""
        return self._status_trait.current_map

    @property
    def current_map_info(self) -> MultiMapsListMapInfo | None:
        """Returns the currently active map info, if available."""
        if (current_map := self.current_map) is None or self.map_info is None:
            return None
        for map_info in self.map_info:
            if map_info.map_flag == current_map:
                return map_info
        return None

    async def set_current_map(self, map_flag: int) -> None:
        """Update the current map of the device by it's map_flag id."""
        await self.rpc_channel.send_command(RoborockCommand.LOAD_MULTI_MAP, params=[map_flag])
        # Refresh our status to make sure it reflects the new map
        await self._status_trait.refresh()

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a MapsTrait instance.

        This overrides the base implementation to handle the specific
        response format for the multi maps list. This is needed because we have
        a custom constructor that requires the StatusTrait.
        """
        if not isinstance(response, list):
            raise ValueError(f"Unexpected MapsTrait response format: {response!r}")
        response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"Unexpected MapsTrait response format: {response!r}")
        return MultiMapsList.from_dict(response)

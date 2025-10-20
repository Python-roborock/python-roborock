"""Trait that represents a full view of the home layout.

This trait combines information about maps and rooms to provide a comprehensive
view of the home layout, including room names and their corresponding segment
on the map. It also makes it straight forward to fetch the map image and data.

This trait depends on the MapsTrait and RoomsTrait to gather the necessary
information. It provides properties to access the current map, the list of
rooms with names, and the map image and data.
"""

import asyncio
import logging
from typing import Self

from roborock.data import CombinedMapInfo, RoborockBase
from roborock.data.v1.v1_code_mappings import RoborockStateCode
from roborock.devices.cache import Cache
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockDeviceBusy, RoborockException
from roborock.roborock_typing import RoborockCommand

from .maps import MapsTrait
from .rooms import RoomsTrait
from .status import StatusTrait

_LOGGER = logging.getLogger(__name__)

MAP_SLEEP = 3


class HomeTrait(RoborockBase, common.V1TraitMixin):
    """Trait that represents a full view of the home layout."""

    command = RoborockCommand.GET_MAP_V1  # This is not used

    def __init__(
        self,
        status_trait: StatusTrait,
        maps_trait: MapsTrait,
        rooms_trait: RoomsTrait,
        cache: Cache,
    ) -> None:
        """Initialize the HomeTrait.

        We keep track of the MapsTrait and RoomsTrait to provide a comprehensive
        view of the home layout. This also depends on the StatusTrait to determine
        the current map. See comments in MapsTrait for details on that dependency.

        The cache is used to store discovered home data to minimize map switching
        and improve performance. The cache should be persisted by the caller to
        ensure data is retained across restarts.

        After initial discovery, only information for the current map is refreshed
        to keep data up to date without excessive map switching. However, as
        users switch rooms, the current map's data will be updated to ensure
        accuracy.
        """
        super().__init__()
        self._status_trait = status_trait
        self._maps_trait = maps_trait
        self._rooms_trait = rooms_trait
        self._cache = cache
        self._home_cache: dict[int, CombinedMapInfo] | None = None

    async def discover_home(self) -> None:
        """Iterate through all maps to discover rooms and cache them.

        This will be a no-op if the home cache is already populated.

        This cannot be called while the device is cleaning, as that would interrupt the
        cleaning process. This will raise `RoborockDeviceBusy` if the device is
        currently cleaning.

        After discovery, the home cache will be populated and can be accessed via the `home_cache` property.
        """
        cache_data = await self._cache.get()
        if cache_data.home_cache:
            _LOGGER.debug("Home cache already populated, skipping discovery")
            self._home_cache = cache_data.home_cache
            return

        if self._status_trait.state == RoborockStateCode.cleaning:
            raise RoborockDeviceBusy("Cannot perform home discovery while the device is cleaning")

        await self._maps_trait.refresh()
        if self._maps_trait.current_map_info is None:
            raise RoborockException("Cannot perform home discovery without current map info")

        home_cache = await self._build_home_cache()
        _LOGGER.debug("Home discovery complete, caching data for %d maps", len(home_cache))
        await self._update_home_cache(home_cache)

    async def _refresh_map_data(self, map_info) -> CombinedMapInfo:
        """Collect room data for a specific map and return CombinedMapInfo."""
        await self._rooms_trait.refresh()
        return CombinedMapInfo(
            map_flag=map_info.map_flag,
            name=map_info.name,
            rooms=self._rooms_trait.rooms or [],
        )

    async def _build_home_cache(self) -> dict[int, CombinedMapInfo]:
        """Perform the actual discovery and caching of home data."""
        home_cache: dict[int, CombinedMapInfo] = {}

        # Sort map_info to process the current map last, reducing map switching.
        # False (non-original maps) sorts before True (original map). We ensure
        # we load the original map last.
        sorted_map_infos = sorted(
            self._maps_trait.map_info or [],
            key=lambda mi: mi.map_flag == self._maps_trait.current_map,
            reverse=False,
        )
        _LOGGER.debug("Building home cache for maps: %s", [mi.map_flag for mi in sorted_map_infos])
        for map_info in sorted_map_infos:
            # We need to load each map to get its room data
            if len(sorted_map_infos) > 1:
                _LOGGER.debug("Loading map %s", map_info.map_flag)
                await self._maps_trait.set_current_map(map_info.map_flag)
                await asyncio.sleep(MAP_SLEEP)

            map_data = await self._refresh_map_data(map_info)
            home_cache[map_info.map_flag] = map_data
        return home_cache

    async def refresh(self) -> Self:
        """Refresh current map's underlying map and room data, updating cache as needed.

        This will only refresh the current map's data and will not populate non
        active maps or re-discover the home. It is expected that this will keep
        information up to date for the current map as users switch to that map.
        """
        if self._home_cache is None:
            raise RoborockException("Cannot refresh home data without home cache, did you call discover_home()?")

        # Refresh the list of map names/info
        await self._maps_trait.refresh()
        if (current_map_info := self._maps_trait.current_map_info) is None or (
            map_flag := self._maps_trait.current_map
        ) is None:
            raise RoborockException("Cannot refresh home data without current map info")

        # Refresh the current map's room data
        current_map_data = self._home_cache.get(map_flag)
        if current_map_data:
            map_data = await self._refresh_map_data(current_map_info)
            if map_data != current_map_data:
                await self._update_home_cache({**self._home_cache, map_flag: map_data})

        return self

    @property
    def home_cache(self) -> dict[int, CombinedMapInfo] | None:
        """Returns the map information for all cached maps."""
        return self._home_cache

    @property
    def current_map_data(self) -> CombinedMapInfo | None:
        """Returns the map data for the current map."""
        current_map_flag = self._maps_trait.current_map
        if current_map_flag is None or self._home_cache is None:
            return None
        return self._home_cache.get(current_map_flag)

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """This trait does not parse responses directly."""
        raise NotImplementedError("HomeTrait does not support direct command responses")

    async def _update_home_cache(self, home_cache: dict[int, CombinedMapInfo]) -> None:
        cache_data = await self._cache.get()
        cache_data.home_cache = home_cache
        await self._cache.set(cache_data)
        self._home_cache = home_cache

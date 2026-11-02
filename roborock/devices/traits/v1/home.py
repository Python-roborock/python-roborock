"""Trait that represents a full view of the home layout.

This trait combines information about maps and rooms to provide a comprehensive
view of the home layout, including room names and their corresponding segment
on the map. It also makes it straight forward to fetch the map image and data.

This trait depends on the MapsTrait and RoomsTrait to gather the necessary
information. It provides properties to access the current map, the list of
rooms with names, and the map image and data.

Callers may first call `discover_home()` to populate the home layout cache by
iterating through all available maps on the device. This will cache the map
information and room names for all maps to minimize map switching and improve
performance. After the initial discovery, callers can call `refresh()` to update
the current map's information and room names as needed.
"""

import asyncio
import base64
import logging
from collections.abc import Callable

from roborock.data import CombinedMapInfo, MultiMapsListMapInfo, NamedRoomMapping, RoborockBase
from roborock.data.v1.v1_code_mappings import RoborockStateCode
from roborock.devices.cache import DeviceCache
from roborock.devices.traits.common import TraitUpdateListener
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockDeviceBusy, RoborockException, RoborockInvalidStatus
from roborock.roborock_typing import RoborockCommand

from .map_content import MapContent, MapContentTrait
from .maps import MapsTrait
from .rooms import RoomsTrait
from .status import StatusTrait

_LOGGER = logging.getLogger(__name__)

MAP_SLEEP = 3
_MAP_LOADING_STATES = (RoborockStateCode.idle, RoborockStateCode.charging, RoborockStateCode.charging_complete)


def _has_map_image(content: MapContent) -> bool:
    """Return whether content contains a usable map rather than a placeholder."""
    return content.map_data is not None and content.map_data.image is not None and not content.map_data.image.is_empty


class HomeTrait(RoborockBase, common.V1TraitMixin, TraitUpdateListener):
    """Trait that represents a full view of the home layout."""

    command = RoborockCommand.GET_MAP_V1  # This is not used
    converter = common.DefaultConverter(RoborockBase)  # Not used

    def __init__(
        self,
        status_trait: StatusTrait,
        maps_trait: MapsTrait,
        map_content: MapContentTrait,
        rooms_trait: RoomsTrait,
        device_cache: DeviceCache,
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
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._status_trait = status_trait
        self._maps_trait = maps_trait
        self._map_content = map_content
        self._rooms_trait = rooms_trait
        self._device_cache = device_cache
        self._discovery_completed = False
        self._home_map_info: dict[int, CombinedMapInfo] | None = None
        self._home_map_content: dict[int, MapContent] | None = None

    async def discover_home(self) -> None:
        """Iterate through all maps to discover rooms and cache them.

        This will be a no-op if the home cache is already populated. A cache that
        holds "NO MAP" placeholders saved by older versions counts as incomplete:
        the placeholders are left out of memory and the home is discovered again
        once the device is idle.

        This cannot switch maps while the device is busy, as that would interrupt
        its current task. This will raise `RoborockDeviceBusy` unless the device
        is idle or charging with no cleaning or return operation in progress. It
        also raises it when a cache with placeholders needs rediscovery but the
        device reports no current map yet.

        After discovery, the home cache will be populated and can be accessed via the `home_map_info` property.
        """
        device_cache_data = await self._device_cache.get()
        keep_cached_home = False
        if device_cache_data and device_cache_data.home_map_info:
            # The device cache can hand out the object it stores, so keep copies in
            # memory: later updates here must not reach it before they are saved.
            self._home_map_info = dict(device_cache_data.home_map_info)
            try:
                cached_content = {
                    k: await self._map_content.converter.async_parse_map_content(base64.b64decode(v))
                    for k, v in (device_cache_data.home_map_content_base64 or {}).items()
                }
            except (ValueError, RoborockException) as ex:
                _LOGGER.warning("Failed to parse cached home map content, will re-discover: %s", ex)
                self._home_map_content = {}
            else:
                self._home_map_content = {k: v for k, v in cached_content.items() if _has_map_image(v)}
                if len(self._home_map_content) == len(cached_content):
                    _LOGGER.debug("Home cache already populated, skipping discovery")
                    self._discovery_completed = True
                    self._notify_update()
                    return
                # The placeholder stays in the persisted cache until a completed discovery
                # replaces it, so the missing floor is still owed after a restart or while
                # the device is busy.
                _LOGGER.debug("Home cache has map placeholders, re-discovering")
                keep_cached_home = True

        if (
            self._status_trait.state not in _MAP_LOADING_STATES
            or self._status_trait.in_cleaning
            or self._status_trait.in_returning
        ):
            raise RoborockDeviceBusy("Cannot perform home discovery while the device is busy")

        await self._maps_trait.refresh()
        if self._maps_trait.current_map_info is None:
            if keep_cached_home:
                # A floor is still owed from the cache. Stay pending so a later refresh,
                # once a current map exists, can finish discovery.
                raise RoborockDeviceBusy("Cannot rediscover the cached home without current map info")
            _LOGGER.debug("Cannot perform home discovery without current map info")
            self._discovery_completed = True
            await self._update_home_cache({}, {})
            return

        home_map_info, home_map_content = await self._build_home_map_info()
        # A map that answers with a placeholder keeps its last good image.
        home_map_content = {
            **{k: v for k, v in (self._home_map_content or {}).items() if k in home_map_info},
            **{k: v for k, v in home_map_content.items() if _has_map_image(v)},
        }
        _LOGGER.debug("Home discovery complete, caching data for %d maps", len(home_map_info))
        self._discovery_completed = True
        await self._update_home_cache(home_map_info, home_map_content)

    async def _refresh_map_info(self, map_info: MultiMapsListMapInfo) -> CombinedMapInfo:
        """Collect room data for a specific map and return CombinedMapInfo."""
        await self._rooms_trait.refresh()

        # We have room names from multiple sources:
        # - The map_info.rooms which we just received from the MultiMapsList
        # - RoomsTrait rooms come from the GET_ROOM_MAPPING command for the current device (only)
        # - RoomsTrait rooms that are pulled from the cloud API
        # We always prefer the RoomsTrait room names since they are always newer and
        # just refreshed above.
        rooms_map: dict[int, NamedRoomMapping] = {
            **map_info.rooms_map,
            **{room.segment_id: room for room in self._rooms_trait.rooms or ()},
        }
        return CombinedMapInfo(
            map_flag=map_info.map_flag,
            name=map_info.name,
            rooms=list(rooms_map.values()),
        )

    async def _wait_for_map_load(self) -> None:
        """Wait for a requested map to finish loading, then read the device status again.

        `MapsTrait.set_current_map()` reads the status right after it sends the load
        command, when it can still report the map as missing. Without this second
        read, a stale `map_present == 0` would trigger another reload on the next refresh.
        """
        await asyncio.sleep(MAP_SLEEP)
        await self._status_trait.refresh()

    async def _refresh_map_content(self, *, recover_missing: bool = True) -> MapContent:
        """Refresh the map content trait to get the latest map data."""
        # A device can retain the selected map ID without having its map loaded.
        # Reload that saved map before fetching an otherwise valid "NO MAP" image.
        # Restrict recovery to idle states so it cannot interrupt an active task.
        if (
            recover_missing
            and self._status_trait.map_present == 0
            and not self._status_trait.in_cleaning
            and not self._status_trait.in_returning
            and self._status_trait.state in _MAP_LOADING_STATES
            and (current_map_info := self._maps_trait.current_map_info) is not None
        ):
            _LOGGER.debug("Reloading missing selected map %s", current_map_info.map_flag)
            try:
                await self._maps_trait.set_current_map(current_map_info.map_flag)
            except RoborockInvalidStatus as ex:
                raise RoborockDeviceBusy("Cannot reload selected map right now (device action locked)") from ex
            await self._wait_for_map_load()

        await self._map_content.refresh()
        return MapContent(
            image_content=self._map_content.image_content,
            map_data=self._map_content.map_data,
            raw_api_response=self._map_content.raw_api_response,
        )

    async def _build_home_map_info(self) -> tuple[dict[int, CombinedMapInfo], dict[int, MapContent]]:
        """Perform the actual discovery and caching of home map info and content."""
        home_map_info: dict[int, CombinedMapInfo] = {}
        home_map_content: dict[int, MapContent] = {}

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
                try:
                    await self._maps_trait.set_current_map(map_info.map_flag)
                except RoborockInvalidStatus as ex:
                    # Device is in a state that forbids map switching. Translate to
                    # "busy" so callers can fall back to refreshing the current map only.
                    raise RoborockDeviceBusy("Cannot switch maps right now (device action locked)") from ex
                await self._wait_for_map_load()

            # Multi-map discovery has already loaded this map and waited above.
            map_content = await self._refresh_map_content(recover_missing=len(sorted_map_infos) == 1)
            home_map_content[map_info.map_flag] = map_content

            combined_map_info = await self._refresh_map_info(map_info)
            home_map_info[map_info.map_flag] = combined_map_info
        return home_map_info, home_map_content

    async def refresh(self) -> None:
        """Refresh current map's underlying map and room data, updating cache as needed.

        This will only refresh the current map's data and will not populate non
        active maps or re-discover the home. It is expected that this will keep
        information up to date for the current map as users switch to that map.
        """
        recover_missing = True
        if not self._discovery_completed:
            # Running initial discovery also populates all of the same information
            # as below so we can just call that method. If the device is busy
            # then we'll fall through below to refresh the current map only.
            try:
                await self.discover_home()
                return
            except RoborockDeviceBusy:
                _LOGGER.debug("Cannot discover home data while device is busy")
                recover_missing = False

        # Refresh the list of map names/info
        await self._maps_trait.refresh()
        if (current_map_info := self._maps_trait.current_map_info) is None or (
            map_flag := self._maps_trait.current_map
        ) is None:
            _LOGGER.debug("Cannot refresh home data without current map info")
            self._notify_update()
            return

        # Refresh the map content to ensure we have the latest image and object positions
        try:
            new_map_content = await self._refresh_map_content(recover_missing=recover_missing)
        except RoborockDeviceBusy:
            _LOGGER.debug("Cannot reload selected map while device is busy; refreshing current map only")
            new_map_content = await self._refresh_map_content(recover_missing=False)
        # Refresh the current map's room data
        combined_map_info = await self._refresh_map_info(current_map_info)
        await self._update_current_map(
            map_flag, combined_map_info, new_map_content, update_cache=self._discovery_completed
        )

    def add_update_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback when the trait has been updated.

        Overridden to immediately execute the callback with the current state if populated.
        """
        unsub = super().add_update_listener(callback)
        if self._home_map_info is not None:
            callback()
        return unsub

    @property
    def home_map_info(self) -> dict[int, CombinedMapInfo] | None:
        """Returns the map information for all cached maps."""
        if self._home_map_info is None or self._maps_trait.map_info is None:
            return self._home_map_info
        return {
            mi.map_flag: value
            for mi in self._maps_trait.map_info
            if (value := self._home_map_info.get(mi.map_flag)) is not None
        }

    @property
    def current_map_data(self) -> CombinedMapInfo | None:
        """Returns the map data for the current map."""
        current_map_flag = self._maps_trait.current_map
        if current_map_flag is None or self._home_map_info is None:
            return None
        return self._home_map_info.get(current_map_flag)

    @property
    def current_rooms(self) -> list[NamedRoomMapping]:
        """Returns the room names for the current map."""
        if self.current_map_data is None:
            return []
        return self.current_map_data.rooms

    @property
    def home_map_content(self) -> dict[int, MapContent] | None:
        """Returns the map content for all cached maps."""
        if self._home_map_content is None or self._maps_trait.map_info is None:
            return self._home_map_content
        return {
            mi.map_flag: value
            for mi in self._maps_trait.map_info
            if (value := self._home_map_content.get(mi.map_flag)) is not None
        }

    async def _update_home_cache(
        self, home_map_info: dict[int, CombinedMapInfo], home_map_content: dict[int, MapContent]
    ) -> None:
        """Update the entire home cache with new map info and content."""
        home_map_content = {k: v for k, v in home_map_content.items() if _has_map_image(v)}
        device_cache_data = await self._device_cache.get()
        device_cache_data.home_map_info = home_map_info
        device_cache_data.home_map_content_base64 = {
            k: base64.b64encode(v.raw_api_response).decode("utf-8")
            for k, v in home_map_content.items()
            if v.raw_api_response
        }
        await self._device_cache.set(device_cache_data)
        self._home_map_info = home_map_info
        self._home_map_content = home_map_content
        self._notify_update()

    async def _update_current_map(
        self,
        map_flag: int,
        map_info: CombinedMapInfo,
        map_content: MapContent,
        update_cache: bool,
    ) -> None:
        """Update the cache for the current map only."""
        # Update the persistent cache if requested e.g. home discovery has
        # completed and we want to keep it fresh. Otherwise just update the
        # in memory map below.
        if update_cache:
            device_cache_data = await self._device_cache.get()
            if device_cache_data.home_map_info is None:
                device_cache_data.home_map_info = {}
            device_cache_data.home_map_info[map_flag] = map_info
            if _has_map_image(map_content) and map_content.raw_api_response:
                if device_cache_data.home_map_content_base64 is None:
                    device_cache_data.home_map_content_base64 = {}
                device_cache_data.home_map_content_base64[map_flag] = base64.b64encode(
                    map_content.raw_api_response
                ).decode("utf-8")
            await self._device_cache.set(device_cache_data)

        if self._home_map_info is None:
            self._home_map_info = {}
        self._home_map_info[map_flag] = map_info

        if self._home_map_content is None:
            self._home_map_content = {}
        if _has_map_image(map_content):
            self._home_map_content[map_flag] = map_content
        self._notify_update()

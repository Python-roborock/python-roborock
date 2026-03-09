"""Trait for managing room mappings on Roborock devices."""

import logging
from dataclasses import dataclass

from roborock.data import HomeData, NamedRoomMapping, RoborockBase
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.web_api import UserWebApiClient

_LOGGER = logging.getLogger(__name__)


@dataclass
class Rooms(RoborockBase):
    """Dataclass representing a collection of room mappings."""

    rooms: list[NamedRoomMapping] | None = None
    """List of room mappings."""

    @property
    def room_map(self) -> dict[int, NamedRoomMapping]:
        """Returns a mapping of segment_id to NamedRoomMapping."""
        if self.rooms is None:
            return {}
        return {room.segment_id: room for room in self.rooms}


class RoomsTrait(Rooms, common.V1TraitMixin):
    """Trait for managing the room mappings of Roborock devices."""

    command = RoborockCommand.GET_ROOM_MAPPING

    def __init__(self, home_data: HomeData, web_api: UserWebApiClient) -> None:
        """Initialize the RoomsTrait."""
        super().__init__()
        self._home_data = home_data
        self._web_api = web_api
        self._seen_unknown_room_iot_ids: set[str] = set()

    async def refresh(self) -> None:
        """Refresh room mappings and backfill unknown room names from the web API."""
        response = await self.rpc_channel.send_command(self.command)
        if not isinstance(response, list):
            raise ValueError(f"Unexpected RoomsTrait response format: {response!r}")

        segment_map = _extract_segment_map(response)
        await self._populate_missing_home_data_rooms(segment_map)

        new_data = self._parse_response(response, segment_map)
        self._update_trait_values(new_data)
        _LOGGER.debug("Refreshed %s: %s", self.__class__.__name__, new_data)

    @property
    def _iot_id_room_name_map(self) -> dict[str, str]:
        """Returns a dictionary of Room IOT IDs to room names."""
        return {str(room.id): room.name for room in self._home_data.rooms or ()}

    def _parse_response(self, response: common.V1ResponseData, segment_map: dict[int, str] | None = None) -> Rooms:
        """Parse the response from the device into a list of NamedRoomMapping."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected RoomsTrait response format: {response!r}")
        if segment_map is None:
            segment_map = _extract_segment_map(response)
        name_map = self._iot_id_room_name_map
        return Rooms(
            rooms=[
                NamedRoomMapping(segment_id=segment_id, iot_id=iot_id, name=name_map.get(iot_id, f"Room {segment_id}"))
                for segment_id, iot_id in segment_map.items()
            ]
        )

    async def _populate_missing_home_data_rooms(self, segment_map: dict[int, str]) -> None:
        """Load missing room names into home data for newly-seen unknown room ids."""
        missing_room_iot_ids = set(segment_map.values()) - set(self._iot_id_room_name_map.keys())
        new_missing_room_iot_ids = missing_room_iot_ids - self._seen_unknown_room_iot_ids
        if not new_missing_room_iot_ids:
            return

        try:
            web_rooms = await self._web_api.get_rooms()
        except Exception:
            _LOGGER.debug("Failed to fetch rooms from web API", exc_info=True)
        else:
            if isinstance(web_rooms, list) and web_rooms:
                self._home_data.rooms = web_rooms

        self._seen_unknown_room_iot_ids.update(missing_room_iot_ids)


def _extract_segment_map(response: list) -> dict[int, str]:
    """Extract a segment_id -> iot_id mapping from the response.

    The response format can be either a flat list of [segment_id, iot_id] or a
    list of lists, where each inner list is a pair of [segment_id, iot_id]. This
    function normalizes the response into a dict of segment_id to iot_id.

    NOTE: We currently only partial samples of the room mapping formats, so
    improving test coverage with samples from a real device with this format
    would be helpful.
    """
    if len(response) == 2 and not isinstance(response[0], list):
        segment_id, iot_id = response[0], response[1]
        return {segment_id: str(iot_id)}

    segment_map: dict[int, str] = {}
    for part in response:
        if not isinstance(part, list) or len(part) < 2:
            _LOGGER.warning("Unexpected room mapping entry format: %r", part)
            continue
        segment_id, iot_id = part[0], part[1]
        segment_map[segment_id] = str(iot_id)
    return segment_map

"""Trait for managing room mappings on Roborock devices."""

import logging
from dataclasses import dataclass

from roborock.data import HomeData, HomeDataRoom, NamedRoomMapping, RoborockBase
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.web_api import UserWebApiClient

_LOGGER = logging.getLogger(__name__)

_DEFAULT_NAME = "Unknown"


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

    def __init__(self, home_data: HomeData, web_api: UserWebApiClient | None = None) -> None:
        """Initialize the RoomsTrait."""
        super().__init__()
        self._home_data = home_data
        self._web_api = web_api
        self._seen_unknown_room_iot_ids: set[str] = set()

    @property
    def _iot_id_room_name_map(self) -> dict[str, str]:
        """Returns a dictionary of Room IOT IDs to room names."""
        return {str(room.id): room.name for room in self._home_data.rooms or ()}

    def _parse_response(self, response: common.V1ResponseData) -> Rooms:
        """Parse the response from the device into a list of NamedRoomMapping."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected RoomsTrait response format: {response!r}")
        name_map = self._iot_id_room_name_map
        segment_pairs = _extract_segment_pairs(response)
        return Rooms(
            rooms=[
                NamedRoomMapping(segment_id=segment_id, iot_id=iot_id, name=name_map.get(iot_id, _DEFAULT_NAME))
                for segment_id, iot_id in segment_pairs
            ]
        )

    def merge_home_data_rooms(self, rooms: list[HomeDataRoom]) -> None:
        """Merge newly discovered rooms into home data by room id."""
        updated_rooms = list(self._home_data.rooms or ())
        existing_by_id = {room.id: room for room in updated_rooms}

        for room in rooms:
            existing_room = existing_by_id.get(room.id)
            if existing_room is None:
                updated_rooms.append(room)
                existing_by_id[room.id] = room
            elif room.name and existing_room.name in ("", _DEFAULT_NAME):
                existing_room.name = room.name

        self._home_data.rooms = updated_rooms

    async def resolve_unknown_room_names(self, rooms: dict[int, NamedRoomMapping]) -> None:
        """Resolve unknown room names using home data and web API fallbacks."""
        unknown_room_iot_ids = {room.iot_id for room in rooms.values() if room.name == _DEFAULT_NAME}
        new_unknown_room_iot_ids = unknown_room_iot_ids - self._seen_unknown_room_iot_ids
        web_room_names: dict[str, str] = {}

        if self._web_api and new_unknown_room_iot_ids:
            try:
                web_rooms = await self._web_api.get_rooms()
            except Exception:
                _LOGGER.debug("Failed to fetch rooms from web API", exc_info=True)
            else:
                if web_rooms:
                    web_room_names = {str(room.id): room.name for room in web_rooms}
                    self.merge_home_data_rooms(web_rooms)

        for segment_id, room in rooms.items():
            if room.name != _DEFAULT_NAME:
                continue
            rooms[segment_id] = NamedRoomMapping(
                segment_id=room.segment_id,
                iot_id=room.iot_id,
                name=web_room_names.get(room.iot_id, f"Room {room.segment_id}"),
            )

        self._seen_unknown_room_iot_ids.update(unknown_room_iot_ids)


def _extract_segment_pairs(response: list) -> list[tuple[int, str]]:
    """Extract segment_id and iot_id pairs from the response.

    The response format can be either a flat list of [segment_id, iot_id] or a
    list of lists, where each inner list is a pair of [segment_id, iot_id]. This
    function normalizes the response into a list of (segment_id, iot_id) tuples

    NOTE: We currently only partial samples of the room mapping formats, so
    improving test coverage with samples from a real device with this format
    would be helpful.
    """
    if len(response) == 2 and not isinstance(response[0], list):
        segment_id, iot_id = response[0], response[1]
        return [(segment_id, iot_id)]

    segment_pairs: list[tuple[int, str]] = []
    for part in response:
        if not isinstance(part, list) or len(part) < 2:
            _LOGGER.warning("Unexpected room mapping entry format: %r", part)
            continue
        segment_id, iot_id = part[0], part[1]
        segment_pairs.append((segment_id, iot_id))
    return segment_pairs

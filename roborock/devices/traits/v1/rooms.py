"""Trait for managing room mappings on Roborock devices."""

import logging
from dataclasses import dataclass

from roborock.data import HomeData, HomeDataRoom, NamedRoomMapping, RoborockBase
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

    def with_room_names(self, name_map: dict[str, str]) -> "Rooms":
        """Create a new Rooms object with updated room names."""
        return Rooms(
            rooms=[
                NamedRoomMapping(
                    segment_id=room.segment_id,
                    iot_id=room.iot_id,
                    raw_name=name_map.get(room.iot_id),
                )
                for room in self.rooms or []
            ]
        )


class RoomsConverter(common.V1TraitDataConverter):
    """Converts response objects to Rooms."""

    def convert(self, response: common.V1ResponseData) -> Rooms:
        """Parse the response from the device into a list of NamedRoomMapping."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected RoomsTrait response format: {response!r}")
        segment_map = self.extract_segment_map(response)
        return Rooms(
            rooms=[NamedRoomMapping(segment_id=segment_id, iot_id=iot_id) for segment_id, iot_id in segment_map.items()]
        )

    @staticmethod
    def extract_segment_map(response: list) -> dict[int, str]:
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


class RoomsTrait(Rooms, common.V1TraitMixin):
    """Trait for managing the room mappings of Roborock devices."""

    command = RoborockCommand.GET_ROOM_MAPPING
    converter = RoomsConverter()

    def __init__(self, home_data: HomeData, web_api: UserWebApiClient) -> None:
        """Initialize the RoomsTrait."""
        super().__init__()
        self._home_data = home_data
        self._web_api = web_api
        self._discovered_iot_ids: set[str] = set()

    async def refresh(self) -> None:
        """Refresh room mappings and backfill unknown room names from the web API."""
        response = await self.rpc_channel.send_command(self.command)
        if not isinstance(response, list):
            raise ValueError(f"Unexpected RoomsTrait response format: {response!r}")

        segment_map = RoomsConverter.extract_segment_map(response)
        # Track all iot ids seen before. Refresh the room list when new ids are found.
        new_iot_ids = set(segment_map.values()) - set(self._home_data.rooms_map.keys())
        if new_iot_ids - self._discovered_iot_ids:
            _LOGGER.debug("Refreshing room list to discover new room names")
            if updated_rooms := await self._refresh_rooms():
                _LOGGER.debug("Updating rooms: %s", list(updated_rooms))
                self._home_data.rooms = updated_rooms
            self._discovered_iot_ids.update(new_iot_ids)

        rooms = self.converter.convert(response)
        rooms = rooms.with_room_names(self._home_data.rooms_name_map)
        common.merge_trait_values(self, rooms)

    async def _refresh_rooms(self) -> list[HomeDataRoom]:
        """Fetch the latest rooms from the web API."""
        try:
            return await self._web_api.get_rooms()
        except Exception:
            _LOGGER.debug("Failed to fetch rooms from web API", exc_info=True)
            return []

"""Rooms trait for Q10 B01 devices."""

import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import (
    Q10RoomConfig,
    Q10RoomsConfig,
    parse_customer_clean_payload,
)
from roborock.devices.traits.common import TraitUpdateListener

from .command import CommandTrait

_LOGGER = logging.getLogger(__name__)


class RoomsTrait(Q10RoomsConfig, TraitUpdateListener):
    """Trait for managing Q10 room configuration."""

    def __init__(self, command: CommandTrait) -> None:
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._command = command

    async def refresh(self) -> None:
        """Request the current room configuration from the device."""
        await self._command.send(B01_Q10_DP.COMMON, params={B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code: 0})

    @property
    def room_map(self) -> dict[int, Q10RoomConfig]:
        """Return the current room configurations keyed by room id."""
        return {room.room_id: room for room in self.rooms}

    @property
    def room_names(self) -> dict[int, str]:
        """Return the current room names keyed by room id."""
        return {room.room_id: room.room_name for room in self.rooms}

    def get_room(self, room_id: int) -> Q10RoomConfig | None:
        """Return a room configuration by room id, if known."""
        return self.room_map.get(int(room_id))

    def get_room_name(self, room_id: int, default: str | None = None) -> str | None:
        """Return a room name by room id, optionally with a default."""
        room = self.get_room(room_id)
        if room is None:
            return default
        return room.room_name

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Update the trait from raw DPS data."""
        payload = decoded_dps.get(B01_Q10_DP.CUSTOMER_CLEAN)
        if not isinstance(payload, str):
            return

        try:
            parsed = parse_customer_clean_payload(payload)
        except Exception:
            _LOGGER.debug("Failed to parse CUSTOMER_CLEAN payload", exc_info=True)
            return

        changed = (
            self.raw_length != parsed.raw_length
            or self.declared_count != parsed.declared_count
            or self.rooms != parsed.rooms
        )
        self.raw_length = parsed.raw_length
        self.declared_count = parsed.declared_count
        self.rooms = parsed.rooms
        if changed:
            self._notify_update()

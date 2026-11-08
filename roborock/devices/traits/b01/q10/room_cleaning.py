"""Customized room-cleaning controls for Q10 devices."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10RoomCleanSettings
from roborock.data.containers import RoborockBase
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import decode_room_clean_settings, encode_room_clean_settings

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


@dataclass
class RoomCleaning(RoborockBase):
    """Current customized room-cleaning state."""

    settings: list[Q10RoomCleanSettings] | None = None


class RoomCleaningTrait(RoomCleaning, UpdatableTrait):
    """Read and control Q10 per-room cleaning settings."""

    def __init__(self, command: CommandTrait) -> None:
        RoomCleaning.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)
        self._command: CommandTrait = command

    def settings_for_room(self, room_id: int) -> Q10RoomCleanSettings | None:
        """Return the latest reported settings for one room."""
        if self.settings is None:
            return None
        return next((room for room in self.settings if room.room_id == room_id), None)

    async def refresh(self) -> None:
        """Request the complete customized-room settings."""
        await self._command.send(B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0})

    async def set_settings(self, settings: Sequence[Q10RoomCleanSettings]) -> None:
        """Publish customized settings, then request a complete settings push."""
        payload = encode_room_clean_settings(settings)
        await self._command.send(B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN.code): payload})
        await self.refresh()

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Replace full settings or upsert the rooms in a compact push."""
        payload = decoded_dps.get(B01_Q10_DP.CUSTOMER_CLEAN)
        if not isinstance(payload, str):
            return
        try:
            update = decode_room_clean_settings(payload)
        except RoborockException:
            _LOGGER.debug("Ignoring malformed Q10 customized-room settings", exc_info=True)
            return
        if update.complete:
            settings = list(update.settings)
        else:
            by_room = {room.room_id: room for room in (self.settings or [])}
            by_room.update((room.room_id, room) for room in update.settings)
            settings = list(by_room.values())
        if settings != self.settings:
            self.settings = settings
            self._notify_update()

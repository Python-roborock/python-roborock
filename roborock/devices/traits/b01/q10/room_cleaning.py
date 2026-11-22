"""Customized room-cleaning controls for Q10 devices."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    Q10CleanCount,
    Q10RoomCleanType,
    Q10RoomFanLevel,
    YXCleanLine,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10RoomCleanSettings
from roborock.data.containers import RoborockBase
from roborock.devices.traits.common import DpsDataConverter
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import decode_room_clean_settings, encode_room_clean_settings

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)

_ROOM_SETTING_MODES = (
    ("fan_level", Q10RoomFanLevel, Q10RoomFanLevel.UNKNOWN.code),
    ("water_level", YXWaterLevel, YXWaterLevel.UNKNOWN.code),
    ("clean_type", Q10RoomCleanType, Q10RoomCleanType.UNKNOWN.code),
    ("clean_count", Q10CleanCount, Q10CleanCount.UNKNOWN.code),
    ("clean_line", YXCleanLine, YXCleanLine.UNKNOWN.code),
)


def _normalize_settings(
    records: list[dict[str, int]], current: list[Q10RoomCleanSettings] | None, complete: bool
) -> list[dict[str, int]]:
    """Normalize mode codes and merge compact records before model conversion."""
    settings = []
    for record in records:
        room = {"room_id": record["room_id"]}
        for field_name, mode_type, unknown_code in _ROOM_SETTING_MODES:
            code = record[field_name]
            room[field_name] = code if mode_type.from_code_optional(code) is not None else unknown_code
        settings.append(room)
    if complete:
        return settings

    by_room = {
        room.room_id: {
            "room_id": room.room_id,
            **{field_name: getattr(room, field_name).code for field_name, _, _ in _ROOM_SETTING_MODES},
        }
        for room in (current or [])
    }
    by_room.update((room["room_id"], room) for room in settings)
    return list(by_room.values())


@dataclass
class RoomCleaning(RoborockBase):
    """Current customized room-cleaning state."""

    settings: list[Q10RoomCleanSettings] | None = field(default=None, metadata={"dps": B01_Q10_DP.CUSTOMER_CLEAN})


class RoomCleaningTrait(RoomCleaning, UpdatableTrait):
    """Read and control Q10 per-room cleaning settings."""

    _CONVERTER = DpsDataConverter.from_dataclass(RoomCleaning)

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
            records, complete = decode_room_clean_settings(payload)
        except RoborockException:
            _LOGGER.debug("Ignoring malformed Q10 customized-room settings", exc_info=True)
            return
        settings = _normalize_settings(records, self.settings, complete)
        super().update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: settings})

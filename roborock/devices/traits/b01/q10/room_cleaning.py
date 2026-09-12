"""Customized room-cleaning controls for Q10 devices."""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleanType,
    YXDeviceCleanTask,
)
from roborock.data.b01_q10.b01_q10_containers import Q10ReportedRoomCleanSettings, Q10RoomCleanSettings
from roborock.data.containers import RoborockBase
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.protocols.b01_q10_protocol import (
    Q10RoomCleanUpdate,
    decode_room_clean_settings,
    encode_room_clean_settings,
)

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)
_WRITE_CONFIRMATION_TIMEOUT = 5.0


@dataclass
class RoomCleaning(RoborockBase):
    """Current customized room-cleaning state."""

    settings: tuple[Q10ReportedRoomCleanSettings, ...] = ()
    settings_available: bool = False
    supported: bool = False


class RoomCleaningTrait(RoomCleaning, UpdatableTrait):
    """Read and control Q10 per-room cleaning settings."""

    def __init__(self, command: CommandTrait, *, supported: bool) -> None:
        """Initialize the customized room-cleaning trait."""
        RoomCleaning.__init__(self, supported=supported)
        UpdatableTrait.__init__(self, command, _LOGGER)
        self._command: CommandTrait = command
        self._supported = supported
        self._known_settings: tuple[Q10ReportedRoomCleanSettings, ...] = ()
        self._settings_available = False
        self._write_lock = asyncio.Lock()
        self._pending_payload: str | None = None
        self._pending_confirmation: asyncio.Future[None] | None = None

    def settings_for_room(self, room_id: int) -> Q10ReportedRoomCleanSettings | None:
        """Return the latest settings for a room, if available."""
        return next((settings for settings in self.settings if settings.room_id == room_id), None)

    async def refresh(self) -> None:
        """Request the complete customized-room settings."""
        self._raise_if_unsupported()
        await self._command.send(
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0},
        )

    async def set_settings(self, settings: Sequence[Q10RoomCleanSettings]) -> None:
        """Publish customized settings without starting a clean."""
        self._raise_if_unsupported()
        selected = tuple(settings)
        payload = encode_room_clean_settings(selected)
        self._validate_room_ids(selected)
        async with self._write_lock:
            await self._publish_and_confirm(payload, request_complete=True)

    async def clean(self, settings: Sequence[Q10RoomCleanSettings]) -> None:
        """Apply customized settings and start cleaning those rooms."""
        self._raise_if_unsupported()
        selected = tuple(settings)
        payload = encode_room_clean_settings(selected)
        self._validate_room_ids(selected)
        async with self._write_lock:
            await self._publish_and_confirm(payload)
            await self._command.send(B01_Q10_DP.CLEAN_MODE, YXCleanType.CUSTOMIZED.code)
            await self._command.send(
                B01_Q10_DP.START_CLEAN,
                {
                    "cmd": YXDeviceCleanTask.ELECTORAL.code,
                    # "clean_paramters" is the spelling required by the firmware.
                    "clean_paramters": [room.room_id for room in selected],
                },
            )

    async def _publish_and_confirm(self, payload: str, *, request_complete: bool = False) -> None:
        """Publish compact settings and wait for matching device confirmation."""
        confirmation = asyncio.get_running_loop().create_future()
        self._pending_payload = payload
        self._pending_confirmation = confirmation
        try:
            await self._command.send(
                B01_Q10_DP.COMMON,
                {str(B01_Q10_DP.CUSTOMER_CLEAN.code): payload},
            )
            if request_complete:
                await self._command.send(
                    B01_Q10_DP.COMMON,
                    {str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0},
                )
            try:
                await asyncio.wait_for(asyncio.shield(confirmation), _WRITE_CONFIRMATION_TIMEOUT)
            except TimeoutError as ex:
                raise RoborockException("Q10 did not confirm customized-room settings") from ex
        finally:
            self._pending_payload = None
            self._pending_confirmation = None
            if not confirmation.done():
                confirmation.cancel()

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Apply a complete settings response or confirm a compact write echo."""
        payload = decoded_dps.get(B01_Q10_DP.CUSTOMER_CLEAN)
        if not isinstance(payload, str):
            return
        try:
            update = decode_room_clean_settings(payload)
        except RoborockException:
            _LOGGER.debug("Ignoring malformed Q10 customized-room settings", exc_info=True)
            return

        self._confirm_write(payload, update)
        if update.complete:
            changed = update.settings != self._known_settings or not self._settings_available
            self._known_settings = update.settings
            self._settings_available = True
            self.settings = update.settings
            self.settings_available = True
            if changed:
                self._notify_update()

    def _confirm_write(self, payload: str, update: Q10RoomCleanUpdate) -> None:
        """Resolve the active write when the device reports matching settings."""
        confirmation = self._pending_confirmation
        if confirmation is None or confirmation.done() or self._pending_payload is None:
            return
        expected = decode_room_clean_settings(self._pending_payload).settings
        matches = payload == self._pending_payload
        if update.complete:
            by_room = {settings.room_id: settings for settings in update.settings}
            matches = all(self._reported_matches(by_room.get(settings.room_id), settings) for settings in expected)
        if matches:
            confirmation.set_result(None)

    @staticmethod
    def _reported_matches(
        reported: Q10ReportedRoomCleanSettings | None,
        expected: Q10ReportedRoomCleanSettings,
    ) -> bool:
        return reported is not None and reported == expected

    def _validate_room_ids(self, settings: Sequence[Q10RoomCleanSettings]) -> None:
        if not self._settings_available:
            raise RoborockException("Refresh Q10 customized-room settings before writing them")
        known = {room.room_id for room in self._known_settings}
        unknown = sorted({room.room_id for room in settings} - known)
        if unknown:
            raise ValueError(f"Unknown Q10 room_id values: {unknown}")

    def _raise_if_unsupported(self) -> None:
        if not self._supported:
            raise RoborockUnsupportedFeature("Customized room cleaning is only verified for Q10 model ss07")

    def invalidate(self) -> None:
        """Discard room settings after a map change."""
        changed = self._settings_available or bool(self._known_settings)
        self._settings_available = False
        self._known_settings = ()
        self.settings_available = False
        self.settings = ()
        confirmation = self._pending_confirmation
        if confirmation is not None and not confirmation.done():
            confirmation.set_exception(RoborockException("Q10 map changed while room settings were pending"))
        if changed:
            self._notify_update()

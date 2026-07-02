"""Clean history trait for Q10 B01 devices.

Unlike the Q7 (which exposes a synchronous ``service.get_record_list`` RPC), the
Q10 is push-driven: :meth:`CleanHistoryTrait.refresh` sends an ``{"op": "list"}``
query for ``dpCleanRecord`` (DP 52) over the ``dpCommon`` channel, and the device
publishes its clean-record list back on the subscribe stream, which
:meth:`CleanHistoryTrait.update_from_dps` then decodes.

Wire parsing is separated from state management: :class:`CleanRecordConverter` turns
a ``dpCleanRecord`` envelope into a :class:`CleanRecordPush`, and the trait applies it.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleaningResult,
    YXCleanScope,
    YXCleanType,
    YXStartMethod,
)
from roborock.data.b01_q10.b01_q10_containers import Q10CleanRecord

from .command import CommandTrait
from .common import UpdatableTrait

__all__ = [
    "CleanHistoryTrait",
    "CleanRecordConverter",
    "CleanRecordPush",
]

_LOGGER = logging.getLogger(__name__)

_RECORD_FIELD_COUNT = 12


@dataclass
class CleanRecordPush:
    """A parsed ``dpCleanRecord`` push: the records it carries and how to apply them.

    ``replace`` is ``True`` for an ``{"op": "list"}`` reply (the full history, which
    replaces the current state) and ``False`` for an ``{"op": "notify"}`` push (a
    single just-finished record, which is upserted).
    """

    records: list[Q10CleanRecord] = field(default_factory=list)
    replace: bool = False


class CleanRecordConverter:
    """Converts a raw ``dpCleanRecord`` (DP 52) envelope into a :class:`CleanRecordPush`.

    Mirrors the converter-per-object pattern used by the other Q10 traits: parsing the
    wire payload lives here, separate from the trait that manages the record list.
    """

    def parse(self, envelope: dict[str, Any]) -> CleanRecordPush | None:
        """Parse a decoded ``dpCleanRecord`` envelope into a :class:`CleanRecordPush`.

        Returns ``None`` for an envelope that carries nothing usable (so the trait can
        ignore it without changing state). Malformed individual records are skipped.
        """
        if envelope.get("op") == "notify":
            record = CleanRecordConverter.parse_record(envelope.get("id"))
            return CleanRecordPush([record], replace=False) if record is not None else None
        data = envelope.get("data")
        if not isinstance(data, list):
            return None
        records = [record for item in data if (record := CleanRecordConverter.parse_record(item)) is not None]
        return CleanRecordPush(records, replace=True)

    @staticmethod
    def parse_record(raw: Any | None) -> Q10CleanRecord | None:
        """Decode one underscore-delimited clean-record string into a :class:`Q10CleanRecord`.

        The device joins 12 values with ``_``: recordId, startTime (Unix s), cleanTime
        (min), cleanArea (m2), mapLen, pathLen, virtualLen, cleanMode, workMode,
        cleaningResult, startMethod, collectDustCount. Returns ``None`` for anything but
        a well-formed 12-field string; an unmapped enum code resolves to ``None`` on its
        field (``raw`` keeps the original).
        """
        if not isinstance(raw, str):
            return None
        parts = raw.split("_")
        if len(parts) != _RECORD_FIELD_COUNT:
            return None
        try:
            return Q10CleanRecord(
                raw=raw,
                record_id=parts[0],
                start_time=int(parts[1]),
                clean_time=int(parts[2]),
                clean_area=int(parts[3]),
                map_len=int(parts[4]),
                path_len=int(parts[5]),
                virtual_len=int(parts[6]),
                clean_mode=YXCleanScope.from_code_optional(int(parts[7])),
                work_mode=YXCleanType.from_code_optional(int(parts[8])),
                cleaning_result=YXCleaningResult.from_code_optional(int(parts[9])),
                start_method=YXStartMethod.from_code_optional(int(parts[10])),
                collect_dust_count=int(parts[11]),
            )
        except ValueError:
            return None


class CleanHistoryTrait(UpdatableTrait):
    """Access to the Q10 clean-record history (``dpCleanRecord``, DP 52).

    A read-model trait updated from the DPS stream like the others, but it overrides
    :meth:`update_from_dps` because the payload is a structured push (a record list,
    or a single ``op:"notify"`` record) rather than a flat data-point-to-field map.
    """

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the clean history trait."""
        UpdatableTrait.__init__(self, command, _LOGGER)
        self._converter = CleanRecordConverter()
        self.records: list[Q10CleanRecord] = []
        """Decoded clean records, most recent first."""

    @property
    def last_record(self) -> Q10CleanRecord | None:
        """The most recent clean record, or ``None`` if there are none."""
        return self.records[0] if self.records else None

    async def refresh(self) -> None:
        """Request the clean-record list from the device.

        This sends the query and returns immediately; the records arrive
        asynchronously on the device stream and populate :attr:`records` once
        :meth:`update_from_dps` processes the ``dpCleanRecord`` push.
        """
        if self._command is None:
            raise ValueError("Trait is read-only; no command channel was provided")
        await self._command.send(
            B01_Q10_DP.COMMON,
            params={str(B01_Q10_DP.CLEAN_RECORD.code): {"op": "list"}},
        )

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Apply a ``dpCleanRecord`` push (a full list reply or a single notify)."""
        envelope = decoded_dps.get(B01_Q10_DP.CLEAN_RECORD)
        if not isinstance(envelope, dict):
            return
        push = self._converter.parse(envelope)
        if push is None:
            return
        self._apply(push)

    def _apply(self, push: CleanRecordPush) -> None:
        """Merge or replace the records from ``push``, then sort newest-first and notify."""
        if push.replace:
            records = list(push.records)
        else:
            updated_ids = {record.record_id for record in push.records}
            records = [record for record in self.records if record.record_id not in updated_ids]
            records.extend(push.records)
        records.sort(key=lambda record: record.start_time or 0, reverse=True)
        self.records = records
        self._notify_update()

"""Clean summary / clean records trait for B01 Q7 devices.

For B01/Q7, the Roborock app uses `service.get_record_list` which returns totals
and a `record_list` whose items contain a JSON string in `detail`.
"""

from __future__ import annotations

import json

from roborock import CleanRecordDetail, CleanRecordList, CleanRecordSummary
from roborock.devices.rpc.b01_q7_channel import send_decoded_command
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import Q7RequestMessage
from roborock.roborock_typing import RoborockB01Q7Methods

__all__ = [
    "CleanSummaryTrait",
]


class CleanSummaryTrait(CleanRecordSummary, Trait):
    """B01/Q7 clean summary + clean record access (via record list service)."""

    def __init__(self, channel: MqttChannel) -> None:
        super().__init__()
        self._channel = channel

    async def refresh(self) -> None:
        """Refresh totals and last record detail from the device."""
        record_list = await self.get_record_list()

        self.total_time = record_list.total_time
        self.total_area = record_list.total_area
        self.total_count = record_list.total_count

        details = await self.get_clean_record_details(record_list=record_list)
        self.last_record_detail = details[0] if details else None

    async def get_record_list(self) -> CleanRecordList:
        """Fetch the raw device clean record list (`service.get_record_list`)."""
        result = await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=10000, command=RoborockB01Q7Methods.GET_RECORD_LIST, params={}),
        )

        if not isinstance(result, dict):
            raise TypeError(f"Unexpected response type for GET_RECORD_LIST: {type(result).__name__}: {result!r}")
        return CleanRecordList.from_dict(result)

    @staticmethod
    def _parse_record_detail(detail: dict | str | None) -> CleanRecordDetail | None:
        if detail is None:
            return None
        if isinstance(detail, str):
            try:
                parsed = json.loads(detail)
            except json.JSONDecodeError as ex:
                raise RoborockException(f"Invalid B01 record detail JSON: {detail!r}") from ex
            if not isinstance(parsed, dict):
                raise RoborockException(f"Unexpected B01 record detail type: {type(parsed).__name__}: {parsed!r}")
            return CleanRecordDetail.from_dict(parsed)
        if isinstance(detail, dict):
            return CleanRecordDetail.from_dict(detail)
        raise TypeError(f"Unexpected B01 record detail type: {type(detail).__name__}: {detail!r}")

    async def get_clean_record_details(self, *, record_list: CleanRecordList | None = None) -> list[CleanRecordDetail]:
        """Return parsed record detail objects (newest-first)."""
        if record_list is None:
            record_list = await self.get_record_list()

        details: list[CleanRecordDetail] = []
        for item in record_list.record_list:
            parsed = self._parse_record_detail(item.detail)
            if parsed is not None:
                details.append(parsed)

        # App treats the newest record as the end of the list
        details.reverse()
        return details

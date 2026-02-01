"""Clean summary / clean records trait for B01 Q7 devices.

For B01/Q7, the Roborock app uses `service.get_record_list` which returns totals
and a `record_list` whose items contain a JSON string in `detail`.
"""

from __future__ import annotations

import logging

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

_LOGGER = logging.getLogger(__name__)


class CleanSummaryTrait(CleanRecordSummary, Trait):
    """B01/Q7 clean summary + clean record access (via record list service)."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the clean summary trait.

        Args:
            channel: MQTT channel used to communicate with the device.
        """
        super().__init__()
        self._channel = channel

    async def refresh(self) -> None:
        """Refresh totals and last record detail from the device."""
        record_list = await self._get_record_list()

        self.total_time = record_list.total_time
        self.total_area = record_list.total_area
        self.total_count = record_list.total_count

        details = await self._get_clean_record_details(record_list=record_list)
        self.last_record_detail = details[0] if details else None

    async def _get_record_list(self) -> CleanRecordList:
        """Fetch the raw device clean record list (`service.get_record_list`)."""
        result = await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=10000, command=RoborockB01Q7Methods.GET_RECORD_LIST, params={}),
        )

        if not isinstance(result, dict):
            raise TypeError(f"Unexpected response type for GET_RECORD_LIST: {type(result).__name__}: {result!r}")
        return CleanRecordList.from_dict(result)

    async def _get_clean_record_details(self, *, record_list: CleanRecordList) -> list[CleanRecordDetail]:
        """Return parsed record detail objects (newest-first)."""
        details: list[CleanRecordDetail] = []
        for item in record_list.record_list:
            try:
                parsed = item.detail_parsed
            except RoborockException as ex:
                # Rather than failing if something goes wrong here, we should fail and log to tell the user.
                _LOGGER.debug("Failed to parse record detail: %s", ex)
                continue
            if parsed is not None:
                details.append(parsed)

        # The server returns the newest record at the end of record_list; reverse so newest is first (index 0).
        details.reverse()
        return details

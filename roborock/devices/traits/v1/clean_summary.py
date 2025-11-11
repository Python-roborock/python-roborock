import logging
from typing import Self

from roborock.data import CleanRecord, CleanSummaryWithDetail
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list

_LOGGER = logging.getLogger(__name__)


class CleanSummaryTrait(CleanSummaryWithDetail, common.V1TraitMixin):
    """Trait for managing the clean summary of Roborock devices."""

    command = RoborockCommand.GET_CLEAN_SUMMARY

    async def refresh(self) -> None:
        """Refresh the clean summary data and last clean record.

        Assumes that the clean summary has already been fetched.
        """
        await super().refresh()
        if not self.records:
            _LOGGER.debug("No clean records available in clean summary.")
            self.last_clean_record = None
            return
        last_record_id = self.records[-1]
        self.last_clean_record = await self.get_clean_record(last_record_id)

    @classmethod
    def _parse_type_response(cls, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a CleanSummary."""
        if isinstance(response, dict):
            return cls.from_dict(response)
        elif isinstance(response, list):
            clean_time, clean_area, clean_count, records = unpack_list(response, 4)
            return cls(
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(response, int):
            return cls(clean_time=response)
        raise ValueError(f"Unexpected clean summary format: {response!r}")

    async def get_clean_record(self, record_id: int) -> CleanRecord:
        """Load a specific clean record by ID."""
        response = await self.rpc_channel.send_command(RoborockCommand.GET_CLEAN_RECORD, params=[record_id])
        return self._parse_clean_record_response(response)

    @classmethod
    def _parse_clean_record_response(cls, response: common.V1ResponseData) -> CleanRecord:
        """Parse the response from the device into a CleanRecord."""
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if isinstance(response, dict):
            return CleanRecord.from_dict(response)
        if isinstance(response, list):
            if isinstance(response[-1], dict):
                records = [CleanRecord.from_dict(rec) for rec in response]
                final_record = records[-1]
                try:
                    # This code is semi-presumptuous - so it is put in a try finally to be safe.
                    final_record.begin = records[0].begin
                    final_record.begin_datetime = records[0].begin_datetime
                    final_record.start_type = records[0].start_type
                    for rec in records[0:-1]:
                        final_record.duration = (final_record.duration or 0) + (rec.duration or 0)
                        final_record.area = (final_record.area or 0) + (rec.area or 0)
                        final_record.avoid_count = (final_record.avoid_count or 0) + (rec.avoid_count or 0)
                        final_record.wash_count = (final_record.wash_count or 0) + (rec.wash_count or 0)
                        final_record.square_meter_area = (final_record.square_meter_area or 0) + (
                            rec.square_meter_area or 0
                        )
                    return final_record
                except Exception:
                    # Return final record when an exception occurred
                    return final_record
            # There are still a few unknown variables in this.
            begin, end, duration, area = unpack_list(response, 4)
            return CleanRecord(begin=begin, end=end, duration=duration, area=area)
        raise ValueError(f"Unexpected clean record format: {response!r}")

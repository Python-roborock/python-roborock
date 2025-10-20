"""Trait for getting the last clean record."""

import logging
from typing import Self

from roborock.data import CleanRecord
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list

from .clean_summary import CleanSummaryTrait

_LOGGER = logging.getLogger(__name__)


class CleanRecordTrait(CleanRecord, common.V1TraitMixin):
    """Trait for getting the last clean record."""

    command = RoborockCommand.GET_CLEAN_RECORD

    def __init__(self, clean_summary_trait: CleanSummaryTrait) -> None:
        """Initialize the clean record trait."""
        super().__init__()
        self._clean_summary_trait = clean_summary_trait

    async def refresh(self) -> Self:
        """Get the last clean record.

        Assumes that the clean summary has already been fetched.
        """
        if not self._clean_summary_trait.records:
            _LOGGER.debug("No clean records available in clean summary.")
            return self
        last_record_id = self._clean_summary_trait.records[-1]
        response = await self.rpc_channel.send_command(self.command, params=[last_record_id])
        new_self = self._parse_response(response)
        self._update_trait_values(new_self)
        return self

    @classmethod
    def _parse_type_response(cls, response: common.V1ResponseData) -> CleanRecord:
        """Parse the response from the device into a CleanRecord."""
        if isinstance(response, dict):
            return CleanRecord.from_dict(response)
        if isinstance(response, list):
            if isinstance(response[-1], dict):
                records = [CleanRecord.from_dict(rec) for rec in response]
                final_record = records[-1]
                try:
                    # This code is semi-presumptions - so it is put in a try finally to be safe.
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

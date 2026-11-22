import logging
from dataclasses import replace

from roborock.data import CleanRecord, CleanSummary, CleanSummaryWithDetail, RoborockBase
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list

_LOGGER = logging.getLogger(__name__)


def _sum_reported(values: list[int | None]) -> int | None:
    """Sum the values reported by each phase, or None if no phase reported one."""
    reported = [value for value in values if value is not None]
    return sum(reported) if reported else None


class CleanSummaryConverter(common.V1TraitDataConverter):
    """Converter for CleanSummary objects.

    The summary response carries no clean record, so merging the result leaves
    the trait's last clean record untouched.
    """

    def convert(self, response: common.V1ResponseData) -> RoborockBase:
        """Parse the response from the device into a CleanSummary."""
        if isinstance(response, dict):
            return CleanSummary.from_dict(response)
        elif isinstance(response, list):
            clean_time, clean_area, clean_count, records = unpack_list(response, 4)
            return CleanSummary(
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(response, int):
            return CleanSummary(clean_time=response)
        raise ValueError(f"Unexpected clean summary format: {response!r}")


class CleanRecordConverter(common.V1TraitDataConverter):
    """Convert server responses to a CleanRecord."""

    def convert(self, response: common.V1ResponseData) -> CleanRecord:
        """Parse the response from the device into a CleanRecord."""
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if isinstance(response, dict):
            return CleanRecord.from_dict(response)
        if isinstance(response, list):
            if not response:
                raise ValueError("Empty clean record response")
            if any(isinstance(rec, dict) for rec in response):
                if not all(isinstance(rec, dict) for rec in response):
                    raise ValueError("Mixed clean record formats")
                records = [CleanRecord.from_dict(rec) for rec in response]
                return replace(
                    records[-1],
                    begin=records[0].begin,
                    start_type=records[0].start_type,
                    duration=_sum_reported([rec.duration for rec in records]),
                    area=_sum_reported([rec.area for rec in records]),
                    avoid_count=_sum_reported([rec.avoid_count for rec in records]),
                    wash_count=_sum_reported([rec.wash_count for rec in records]),
                )
            # There are still a few unknown variables in this.
            begin, end, duration, area = unpack_list(response, 4)
            return CleanRecord(begin=begin, end=end, duration=duration, area=area)
        raise ValueError(f"Unexpected clean record format: {response!r}")


class CleanSummaryTrait(CleanSummaryWithDetail, common.V1TraitMixin):
    """Trait for managing the clean summary of Roborock devices."""

    command = RoborockCommand.GET_CLEAN_SUMMARY
    converter = CleanSummaryConverter()
    clean_record_converter = CleanRecordConverter()

    async def refresh(self) -> None:
        """Refresh the clean summary data and last clean record.

        Assumes that the clean summary has already been fetched. The previous
        clean record is kept if fetching the latest record fails.
        """
        await super().refresh()
        if not self.records:
            _LOGGER.debug("No clean records available in clean summary.")
            self.last_clean_record = None
            return
        # Record IDs are start timestamps; devices may return them in either order.
        last_record_id = max(self.records)
        self.last_clean_record = await self.get_clean_record(last_record_id)

    async def get_clean_record(self, record_id: int) -> CleanRecord:
        """Load a specific clean record by ID."""
        response = await self.rpc_channel.send_command(RoborockCommand.GET_CLEAN_RECORD, params=[record_id])
        try:
            return self.clean_record_converter.convert(response)
        except (TypeError, ValueError) as err:
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=RoborockCommand.GET_CLEAN_RECORD,
                payload=response,
                inner_error=err,
            ) from err

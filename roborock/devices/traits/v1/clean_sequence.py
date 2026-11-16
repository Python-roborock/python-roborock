"""Trait for the room cleaning order of Roborock devices."""

from roborock.data import CleanSequence
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

from .common import V1ResponseData


class CleanSequenceConverter(common.V1TraitDataConverter):
    """Converts get_clean_sequence responses to CleanSequence."""

    def convert(self, response: V1ResponseData) -> CleanSequence:
        """Parse the list of segment ids returned by the device."""
        if not isinstance(response, list) or not all(isinstance(room, int) for room in response):
            raise ValueError(f"Unexpected CleanSequence response format: {response!r}")
        return CleanSequence(rooms=list(response))


class CleanSequenceTrait(CleanSequence, common.V1TraitMixin):
    """Trait for reading and setting the order in which rooms are cleaned.

    The device keeps this order and uses it for room cleaning
    (`app_segment_clean`), whatever order the segments are sent in.
    """

    command = RoborockCommand.GET_CLEAN_SEQUENCE
    converter = CleanSequenceConverter()
    requires_feature = "is_order_clean_supported"

    async def set_order(self, rooms: list[int]) -> None:
        """Set the room cleaning order.

        A device rejects a new order with an invalid status error while it is
        cleaning or moving; set it while the device is idle or docked.
        """
        if not rooms or len(set(rooms)) != len(rooms):
            raise ValueError(f"rooms must be a non-empty list of distinct segment ids: {rooms!r}")
        await self.rpc_channel.send_command(RoborockCommand.SET_CLEAN_SEQUENCE, params=list(rooms))
        # Optimistic update to avoid an extra refresh
        self.rooms = list(rooms)

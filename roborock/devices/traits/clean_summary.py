"""Module for Roborock V1 devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import logging

from roborock.containers import (
    CleanSummary,
)
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list

from .trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "CleanSummaryTrait",
]


class CleanSummaryTrait(Trait):
    """Trait for managing the clean summary of Roborock devices."""

    name = "clean_summary"

    def __init__(self, rpc_channel: V1RpcChannel) -> None:
        """Initialize the CleanSummaryTrait."""
        self._rpc_channel = rpc_channel

    async def get_clean_summary(self) -> CleanSummary:
        """Get the current clean summary of the device.

        This is a placeholder command and will likely be changed/moved in the future.
        """
        clean_summary = await self._rpc_channel.send_command(RoborockCommand.GET_CLEAN_SUMMARY)
        if isinstance(clean_summary, dict):
            return CleanSummary.from_dict(clean_summary)
        elif isinstance(clean_summary, list):
            clean_time, clean_area, clean_count, records = unpack_list(clean_summary, 4)
            return CleanSummary(
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(clean_summary, int):
            return CleanSummary(clean_time=clean_summary)
        raise ValueError(f"Unexpected clean summary format: {clean_summary!r}")

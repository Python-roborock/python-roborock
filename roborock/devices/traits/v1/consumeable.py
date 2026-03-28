"""Trait for managing consumable attributes.

A consumable attribute is one that is expected to be replaced or refilled
periodically, such as filters, brushes, etc.
"""

import logging
from enum import StrEnum
from typing import Any, Self

from roborock.data import Consumable
from roborock.devices.traits.v1 import common
from roborock.roborock_message import RoborockDataProtocol
from roborock.roborock_typing import RoborockCommand

from .common import TraitUpdateListener

__all__ = [
    "ConsumableTrait",
]

_LOGGER = logging.getLogger(__name__)

_DPS_CONVERTER = common.DpsDataConverter.from_dataclass(Consumable)


class ConsumableAttribute(StrEnum):
    """Enum for consumable attributes."""

    SENSOR_DIRTY_TIME = "sensor_dirty_time"
    FILTER_WORK_TIME = "filter_work_time"
    SIDE_BRUSH_WORK_TIME = "side_brush_work_time"
    MAIN_BRUSH_WORK_TIME = "main_brush_work_time"

    @classmethod
    def from_str(cls, value: str) -> Self:
        """Create a ConsumableAttribute from a string value."""
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Unknown ConsumableAttribute: {value}")


class ConsumableTrait(Consumable, common.V1TraitMixin, TraitUpdateListener):
    """Trait for managing consumable attributes on Roborock devices.

    After the first refresh, you can tell what consumables are supported by
    checking which attributes are not None.
    """

    command = RoborockCommand.GET_CONSUMABLE
    converter = common.DefaultConverter(Consumable)

    def __init__(self) -> None:
        """Initialize the consumable trait."""
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)

    async def reset_consumable(self, consumable: ConsumableAttribute) -> None:
        """Reset a specific consumable attribute on the device."""
        await self.rpc_channel.send_command(RoborockCommand.RESET_CONSUMABLE, params=[consumable.value])
        await self.refresh()

    def update_from_dps(self, decoded_dps: dict[RoborockDataProtocol, Any]) -> None:
        """Update the trait from data protocol push message data.

        This handles unsolicited status updates pushed by the device
        via RoborockDataProtocol codes (e.g. STATE=121, BATTERY=122).
        """
        if _DPS_CONVERTER.update_from_dps(self, decoded_dps):
            self._notify_update()

"""Trait for managing consumable attributes.

A consumable attribute is one that is expected to be replaced or refilled
periodically, such as filters, brushes, etc.
"""

from enum import StrEnum
from typing import Self

from roborock.data import Consumable
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

__all__ = [
    "ConsumableTrait",
]


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


class ConsumableTrait(Consumable, common.V1TraitMixin):
    """Trait for managing consumable attributes on Roborock devices.

    After the first refresh, you can tell what consumables are supported by
    checking which attributes are not None.
    """

    command = RoborockCommand.GET_CONSUMABLE

    async def reset_consumable(self, consumable: ConsumableAttribute) -> None:
        """Reset a specific consumable attribute on the device."""
        await self.rpc_channel.send_command(RoborockCommand.RESET_CONSUMABLE, params=[consumable.value])

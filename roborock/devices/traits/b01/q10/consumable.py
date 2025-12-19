"""Consumable trait for Q10 devices."""

from dataclasses import dataclass

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10Consumable
from roborock.devices.traits.b01.q10.common import Q10TraitMixin


@dataclass
class Q10ConsumableTrait(Q10Consumable, Q10TraitMixin):
    """Trait for managing the consumables of Q10 devices."""

    dps_field_map = {
        B01_Q10_DP.MAIN_BRUSH_LIFE: "main_brush_life",
        B01_Q10_DP.SIDE_BRUSH_LIFE: "side_brush_life",
        B01_Q10_DP.FILTER_LIFE: "filter_life",
        B01_Q10_DP.RAG_LIFE: "rag_life",
        B01_Q10_DP.SENSOR_LIFE: "sensor_life",
    }

    async def reset_main_brush(self) -> None:
        """Reset the main brush life."""
        await self.send_dp(B01_Q10_DP.RESET_MAIN_BRUSH, 1)

    async def reset_side_brush(self) -> None:
        """Reset the side brush life."""
        await self.send_dp(B01_Q10_DP.RESET_SIDE_BRUSH, 1)

    async def reset_filter(self) -> None:
        """Reset the filter life."""
        await self.send_dp(B01_Q10_DP.RESET_FILTER, 1)

    async def reset_rag_life(self) -> None:
        """Reset the rag life."""
        await self.send_dp(B01_Q10_DP.RESET_RAG_LIFE, 1)

    async def reset_sensor(self) -> None:
        """Reset the sensor life."""
        await self.send_dp(B01_Q10_DP.RESET_SENSOR, 1)

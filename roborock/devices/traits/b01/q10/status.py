"""Status trait for Q10 devices."""

from dataclasses import dataclass

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10Status
from roborock.devices.traits.b01.q10.common import Q10TraitMixin


@dataclass
class Q10StatusTrait(Q10Status, Q10TraitMixin):
    """Trait for managing the status of Q10 devices."""

    dps_field_map = {
        B01_Q10_DP.CLEAN_TIME: "clean_time",
        B01_Q10_DP.CLEAN_AREA: "clean_area",
        B01_Q10_DP.BATTERY: "battery",
        B01_Q10_DP.STATUS: "status",
        B01_Q10_DP.FUN_LEVEL: "fun_level",
        B01_Q10_DP.WATER_LEVEL: "water_level",
        B01_Q10_DP.CLEAN_COUNT: "clean_count",
        B01_Q10_DP.CLEAN_MODE: "clean_mode",
        B01_Q10_DP.CLEAN_TASK_TYPE: "clean_task_type",
        B01_Q10_DP.BACK_TYPE: "back_type",
        B01_Q10_DP.CLEANING_PROGRESS: "cleaning_progress",
    }

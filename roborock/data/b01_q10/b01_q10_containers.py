"""Data container classes for Q10 B01 devices.

Many of these classes use the `field(metadata={"dps": ...})` convention to map
fields to device Data Points (DPS). This metadata is utilized by the
`update_from_dps` helper in `roborock.devices.traits.b01.q10.common` to
automatically update objects from raw device responses.
"""

from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q10_code_mappings import (
    B01_Q10_DP,
    YXBackType,
    YXDeviceCleanTask,
    YXDeviceState,
    YXDeviceWorkMode,
    YXFanLevel,
    YXWaterLevel,
)


@dataclass
class dpCleanRecord(RoborockBase):
    op: str
    result: int
    id: str
    data: list


@dataclass
class dpMultiMap(RoborockBase):
    op: str
    result: int
    data: list


@dataclass
class dpGetCarpet(RoborockBase):
    op: str
    result: int
    data: str


@dataclass
class dpSelfIdentifyingCarpet(RoborockBase):
    op: str
    result: int
    data: str


@dataclass
class dpNetInfo(RoborockBase):
    wifiName: str
    ipAdress: str
    mac: str
    signal: int


@dataclass
class dpNotDisturbExpand(RoborockBase):
    disturb_dust_enable: int
    disturb_light: int
    disturb_resume_clean: int
    disturb_voice: int


@dataclass
class dpCurrentCleanRoomIds(RoborockBase):
    room_id_list: list


@dataclass
class dpVoiceVersion(RoborockBase):
    version: int


@dataclass
class dpTimeZone(RoborockBase):
    timeZoneCity: str
    timeZoneSec: int


@dataclass
class Q10Status(RoborockBase):
    """Status for Q10 devices.

    Fields are mapped to DPS values using metadata. Objects of this class can be
    automatically updated using the `update_from_dps` helper.
    """

    clean_time: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TIME})
    clean_area: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_AREA})
    battery: int | None = field(default=None, metadata={"dps": B01_Q10_DP.BATTERY})
    status: YXDeviceState | None = field(default=None, metadata={"dps": B01_Q10_DP.STATUS})
    fan_level: YXFanLevel | None = field(default=None, metadata={"dps": B01_Q10_DP.FAN_LEVEL})
    water_level: YXWaterLevel | None = field(default=None, metadata={"dps": B01_Q10_DP.WATER_LEVEL})
    clean_count: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_COUNT})
    clean_mode: YXDeviceWorkMode | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_MODE})
    clean_task_type: YXDeviceCleanTask | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TASK_TYPE})
    back_type: YXBackType | None = field(default=None, metadata={"dps": B01_Q10_DP.BACK_TYPE})
    cleaning_progress: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEANING_PROGRESS})

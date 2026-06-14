"""Data container classes for Q10 B01 devices.

Many of these classes use the `field(metadata={"dps": ...})` convention to map
dataclass fields to device Data Points (DPS). This metadata is utilized by the
`update_from_dps` helper in `roborock.devices.traits.b01.q10.common` to
automatically update objects from raw device responses.
"""

from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q10_code_mappings import (
    B01_Q10_DP,
    YXBackType,
    YXCleanLine,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceState,
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
    # Field names are snake_case so they match the device's camelCase keys once
    # `RoborockBase.from_dict` decamelizes them (e.g. "wifiName" -> "wifi_name").
    # The "ip_adress" spelling intentionally mirrors the device's "ipAdress" typo.
    wifi_name: str | None = None
    ip_adress: str | None = None
    mac: str | None = None
    signal: int | None = None


@dataclass
class dpNotDisturbExpand(RoborockBase):
    disturb_dust_enable: int | None = None
    disturb_light: int | None = None
    disturb_resume_clean: int | None = None
    disturb_voice: int | None = None


@dataclass
class dpCurrentCleanRoomIds(RoborockBase):
    room_id_list: list


@dataclass
class dpVoiceVersion(RoborockBase):
    version: int


@dataclass
class dpTimeZone(RoborockBase):
    # snake_case so the decamelized device keys ("timeZoneCity") map correctly.
    time_zone_city: str | None = None
    time_zone_sec: int | None = None


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
    total_clean_area: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_AREA})
    total_clean_count: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_COUNT})
    total_clean_time: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_TIME})
    main_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MAIN_BRUSH_LIFE})
    side_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SIDE_BRUSH_LIFE})
    filter_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FILTER_LIFE})
    sensor_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SENSOR_LIFE})
    clean_mode: YXCleanType | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_MODE})
    clean_task_type: YXDeviceCleanTask | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TASK_TYPE})
    back_type: YXBackType | None = field(default=None, metadata={"dps": B01_Q10_DP.BACK_TYPE})
    cleaning_progress: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_PROGRESS})
    fault: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FAULT})

    # Additional settings and state reported in the device's full status dump.
    volume: int | None = field(default=None, metadata={"dps": B01_Q10_DP.VOLUME})
    not_disturb: int | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB})
    not_disturb_expand: dpNotDisturbExpand | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB_EXPAND})
    child_lock: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CHILD_LOCK})
    mop_state: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MOP_STATE})
    auto_boost: int | None = field(default=None, metadata={"dps": B01_Q10_DP.AUTO_BOOST})
    dust_switch: int | None = field(default=None, metadata={"dps": B01_Q10_DP.DUST_SWITCH})
    dust_setting: int | None = field(default=None, metadata={"dps": B01_Q10_DP.DUST_SETTING})
    map_save_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MAP_SAVE_SWITCH})
    multi_map_switch: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP_SWITCH})
    recent_clean_record: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.RECENT_CLEAN_RECORD})
    breakpoint_clean: int | None = field(default=None, metadata={"dps": B01_Q10_DP.BREAKPOINT_CLEAN})
    valley_point_charging: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.VALLEY_POINT_CHARGING})
    carpet_clean_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CARPET_CLEAN_TYPE})
    clean_line: YXCleanLine | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_LINE})
    ground_clean: int | None = field(default=None, metadata={"dps": B01_Q10_DP.GROUND_CLEAN})
    line_laser_obstacle_avoidance: int | None = field(
        default=None, metadata={"dps": B01_Q10_DP.LINE_LASER_OBSTACLE_AVOIDANCE}
    )
    add_clean_state: int | None = field(default=None, metadata={"dps": B01_Q10_DP.ADD_CLEAN_STATE})
    timer_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TIMER_TYPE})
    user_plan: int | None = field(default=None, metadata={"dps": B01_Q10_DP.USER_PLAN})
    robot_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_TYPE})
    robot_country_code: str | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_COUNTRY_CODE})
    area_unit: int | None = field(default=None, metadata={"dps": B01_Q10_DP.AREA_UNIT})
    time_zone: dpTimeZone | None = field(default=None, metadata={"dps": B01_Q10_DP.TIME_ZONE})
    net_info: dpNetInfo | None = field(default=None, metadata={"dps": B01_Q10_DP.NET_INFO})

"""Data container classes for Q10 B01 devices.

Many of these classes use the `field(metadata={"dps": ...})` convention to map
dataclass fields to device Data Points (DPS). This metadata is utilized by the
`UpdatableTrait` helper in `roborock.devices.traits.b01.q10.common` to
automatically update objects from raw device responses.
"""

import datetime
from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q10_code_mappings import (
    B01_Q10_DP,
    YXAreaUnit,
    YXBackType,
    YXCarpetCleanType,
    YXCleaningResult,
    YXCleanLine,
    YXCleanScope,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceDustCollectionFrequency,
    YXDeviceState,
    YXFanLevel,
    YXFault,
    YXStartMethod,
    YXWaterLevel,
)


@dataclass
class dpCleanRecord(RoborockBase):
    op: str
    result: int
    id: str
    data: list


@dataclass
class Q10CleanRecord(RoborockBase):
    """A single Q10 (ss07) clean record decoded from a ``dpCleanRecord`` (DP 52) entry.

    The device returns each record as a 12-field underscore-delimited string in the
    ``data`` list of a ``{"op": "list"}`` query (or the ``id`` of an ``{"op": "notify"}``
    push). The ``*_len`` values are internal blob-length metrics whose units aren't
    confirmed; the original ``raw`` string is always retained. The enum fields resolve
    an unmapped/unset code to ``None`` rather than guessing.
    """

    raw: str
    record_id: str | None = None
    start_time: int | None = None
    """Clean start time, Unix seconds."""
    clean_time: int | None = None
    """Cleaning time, minutes."""
    clean_area: int | None = None
    """Cleaned area in square meters."""
    map_len: int | None = None
    """Length of the saved map blob for this record (0 = none stored)."""
    path_len: int | None = None
    """Length of the saved path blob for this record (0 = none stored)."""
    virtual_len: int | None = None
    """Length of the saved virtual-restriction blob for this record (0 = none stored)."""
    clean_mode: YXCleanScope | None = None
    """Clean scope/type (full / selective-room / zone / spot). Same axis as the live
    :class:`YXDeviceCleanTask` but a different record encoding -- see :class:`YXCleanScope`."""
    work_mode: YXCleanType | None = None
    """Actual work performed (vac+mop / vacuum / mop) -- the same enum :class:`Q10Status`
    uses for the live clean-mode DP. Records only ever carry 1/2/3 here."""
    cleaning_result: YXCleaningResult | None = None
    """How the clean ended: 0 interrupted (fault), 1 completed, 2 stopped (no fault)."""
    start_method: YXStartMethod | None = None
    """What initiated the clean: 0 remote, 1 app, 2 timer, 3 button."""
    collect_dust_count: int | None = None
    """Number of dock auto-empties during the clean."""

    @property
    def start_datetime(self) -> datetime.datetime | None:
        """The start time as a timezone-aware (UTC) datetime."""
        if self.start_time is not None:
            return datetime.datetime.fromtimestamp(self.start_time).astimezone(datetime.UTC)
        return None


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
    wifi_name: str | None = None
    # "ip_adress" intentionally mirrors the device's "ipAdress" key (sic).
    ip_adress: str | None = None
    mac: str | None = None
    signal: int | None = None

    @property
    def ip_address(self) -> str | None:
        """Correctly-spelled alias for :attr:`ip_adress`."""
        return self.ip_adress


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
    time_zone_city: str | None = None
    time_zone_sec: int | None = None


@dataclass
class Q10Status(RoborockBase):
    """Core vacuum status for Q10 devices.

    Fields are mapped to DPS values using metadata. Objects of this class can be
    automatically updated using the `UpdatableTrait` helper. Settings that have
    their own trait (volume, child lock, do-not-disturb, dust collection,
    network info, consumables) live on those traits instead of here.
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
    clean_mode: YXCleanType | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_MODE})
    clean_task_type: YXDeviceCleanTask | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TASK_TYPE})
    back_type: YXBackType | None = field(default=None, metadata={"dps": B01_Q10_DP.BACK_TYPE})
    cleaning_progress: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_PROGRESS})
    fault: YXFault | None = field(default=None, metadata={"dps": B01_Q10_DP.FAULT})

    # Additional state reported in the device's full status dump.
    clean_line: YXCleanLine | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_LINE})
    carpet_clean_type: YXCarpetCleanType | None = field(default=None, metadata={"dps": B01_Q10_DP.CARPET_CLEAN_TYPE})
    area_unit: YXAreaUnit | None = field(default=None, metadata={"dps": B01_Q10_DP.AREA_UNIT})
    auto_boost: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.AUTO_BOOST})
    multi_map_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP_SWITCH})
    map_save_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MAP_SAVE_SWITCH})
    recent_clean_record: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.RECENT_CLEAN_RECORD})
    valley_point_charging: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.VALLEY_POINT_CHARGING})
    line_laser_obstacle_avoidance: bool | None = field(
        default=None, metadata={"dps": B01_Q10_DP.LINE_LASER_OBSTACLE_AVOIDANCE}
    )
    # Whether a mop module is attached, and whether "clean along floor direction" is on.
    mop_state: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MOP_STATE})
    ground_clean: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.GROUND_CLEAN})
    # True while an "add area" / re-clean (the app's draw-a-rectangle "re cleaning")
    # request is in progress; pulses back to False once the robot has the area.
    add_clean_state: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.ADD_CLEAN_STATE})
    robot_country_code: str | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_COUNTRY_CODE})
    time_zone: dpTimeZone | None = field(default=None, metadata={"dps": B01_Q10_DP.TIME_ZONE})

    # TODO(#846): value mappings for these ints are not yet decoded (no app
    # control found / internal / constant); keep as int until reverse-engineered.
    breakpoint_clean: int | None = field(default=None, metadata={"dps": B01_Q10_DP.BREAKPOINT_CLEAN})
    timer_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TIMER_TYPE})
    user_plan: int | None = field(default=None, metadata={"dps": B01_Q10_DP.USER_PLAN})
    robot_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_TYPE})

    # DEPRECATED: consumable/accessory remaining-life now lives on the
    # ``Q10Consumable`` trait. These aliases are kept here for backwards
    # compatibility and will be removed in a follow-up release. See PR #846.
    main_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MAIN_BRUSH_LIFE})
    side_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SIDE_BRUSH_LIFE})
    filter_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FILTER_LIFE})
    sensor_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SENSOR_LIFE})

    @property
    def fault_name(self) -> str | None:
        """Returns the name of the current fault."""
        return self.fault.value if self.fault is not None else None


@dataclass
class SoundVolume(RoborockBase):
    """Speaker volume read-model (0-100)."""

    volume: int | None = field(default=None, metadata={"dps": B01_Q10_DP.VOLUME})


@dataclass
class ChildLock(RoborockBase):
    """Child-lock read-model."""

    child_lock: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.CHILD_LOCK})


@dataclass
class DoNotDisturb(RoborockBase):
    """Do Not Disturb read-model."""

    not_disturb: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB})
    not_disturb_expand: dpNotDisturbExpand | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB_EXPAND})


@dataclass
class DustCollection(RoborockBase):
    """Dock auto-empty (dust collection) read-model."""

    dust_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.DUST_SWITCH})
    dust_setting: YXDeviceDustCollectionFrequency | None = field(
        default=None, metadata={"dps": B01_Q10_DP.DUST_SETTING}
    )


@dataclass
class Q10Consumable(RoborockBase):
    """Consumable / accessory remaining-life read-model.

    Named with a ``Q10`` prefix to avoid shadowing the v1 ``Consumable`` when both
    are star-imported into the ``roborock.data`` namespace.
    """

    main_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MAIN_BRUSH_LIFE})
    side_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SIDE_BRUSH_LIFE})
    filter_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FILTER_LIFE})
    sensor_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SENSOR_LIFE})


@dataclass
class Q10NetworkInfo(RoborockBase):
    """Network information read-model.

    Named with a ``Q10`` prefix to avoid shadowing the v1 ``NetworkInfo`` when both
    are star-imported into the ``roborock.data`` namespace.
    """

    net_info: dpNetInfo | None = field(default=None, metadata={"dps": B01_Q10_DP.NET_INFO})

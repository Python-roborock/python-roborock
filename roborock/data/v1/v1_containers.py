import datetime
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from roborock.const import (
    CLEANING_BRUSH_REPLACE_TIME,
    DUST_COLLECTION_REPLACE_TIME,
    FILTER_REPLACE_TIME,
    MAIN_BRUSH_REPLACE_TIME,
    MOP_ROLLER_REPLACE_TIME,
    NO_MAP,
    SENSOR_DIRTY_REPLACE_TIME,
    SIDE_BRUSH_REPLACE_TIME,
    STRAINER_REPLACE_TIME,
)
from roborock.roborock_message import RoborockDataProtocol

from ..containers import NamedRoomMapping, RoborockBase, RoborockBaseTimer, _attr_repr, field_metadata
from .v1_clean_modes import WashTowelModes
from .v1_code_mappings import (
    CleanFluidStatus,
    ClearWaterBoxStatus,
    DirtyWaterBoxStatus,
    DustBagStatus,
    RoborockChargeStatus,
    RoborockCleanType,
    RoborockDockDustCollectionModeCode,
    RoborockDockErrorCode,
    RoborockDockState,
    RoborockDockTypeCode,
    RoborockErrorCode,
    RoborockFinishReason,
    RoborockInCleaning,
    RoborockStartType,
    RoborockStateCode,
)

_LOGGER = logging.getLogger(__name__)


class FieldNameBase(StrEnum):
    """A base enum class that represents a field name in a RoborockBase dataclass."""


class StatusField(FieldNameBase):
    """An enum that represents a field in the `StatusV2` class.

    This is used with `roborock.devices.traits.v1.status.DeviceFeaturesTrait`
    to understand if a feature is supported by the device using `is_field_supported`.

    The enum values are names of fields in the `StatusV2` class. Each field is
    annotated with `dps` metadata to map the field to a `RoborockDataProtocol`
    value used to check support against the product schema.
    """

    STATE = "state"
    BATTERY = "battery"
    FAN_POWER = "fan_power"
    WATER_BOX_MODE = "water_box_mode"
    CHARGE_STATUS = "charge_status"
    DRY_STATUS = "dry_status"
    ERROR_CODE = "error_code"
    WATER_BOX_CARRIAGE_STATUS = "water_box_carriage_status"
    WATER_BOX_STATUS = "water_box_status"
    WATER_SHORTAGE_STATUS = "water_shortage_status"
    DIRTY_WATER_BOX_STATUS = "dirty_water_box_status"
    CLEAR_WATER_BOX_STATUS = "clear_water_box_status"
    CLEAN_FLUID_STATUS = "clean_fluid_status"
    CLEAN_PERCENT = "clean_percent"
    DOCK_ERROR_STATUS = "dock_error_status"
    RDT = "rdt"


@dataclass
class StatusV2(RoborockBase):
    """The result of a GET_STATUS API request."""

    msg_ver: int | None = None
    msg_seq: int | None = None
    state: RoborockStateCode | None = field(default=None, metadata={"dps": RoborockDataProtocol.STATE})
    battery: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.BATTERY})
    clean_time: int | None = None
    clean_area: int | None = None
    error_code: RoborockErrorCode | None = field(default=None, metadata={"dps": RoborockDataProtocol.ERROR_CODE})
    map_present: int | None = None
    in_cleaning: RoborockInCleaning | None = None
    in_returning: int | None = None
    in_fresh_state: int | None = None
    lab_status: int | None = None
    water_box_status: int | None = field(default=None, metadata={"feature": "is_support_water_mode"})
    back_type: int | None = None
    wash_phase: int | None = None
    wash_ready: int | None = None
    fan_power: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.FAN_POWER})
    dnd_enabled: int | None = None
    map_status: int | None = None
    is_locating: int | None = None
    lock_status: int | None = None
    water_box_mode: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.WATER_BOX_MODE})
    water_box_carriage_status: int | None = field(default=None, metadata={"feature": "is_support_water_mode"})
    mop_forbidden_enable: int | None = None
    camera_status: int | None = None
    is_exploring: int | None = None
    home_sec_status: int | None = None
    home_sec_enable_password: int | None = None
    adbumper_status: list[int] | None = None
    water_shortage_status: int | None = field(default=None, metadata={"feature": "is_support_water_mode"})
    dock_type: RoborockDockTypeCode | None = None
    dust_collection_status: int | None = None
    auto_dust_collection: int | None = None
    avoid_count: int | None = None
    mop_mode: int | None = None
    debug_mode: int | None = None
    collision_avoid_status: int | None = None
    switch_map_mode: int | None = None
    dock_error_status: RoborockDockErrorCode | None = field(default=None, metadata={"dock_feature": "has_dock"})

    charge_status: RoborockChargeStatus | None = field(
        default=None, metadata={"dps": RoborockDataProtocol.CHARGE_STATUS}
    )
    unsave_map_reason: int | None = None
    unsave_map_flag: int | None = None
    wash_status: int | None = None
    distance_off: int | None = None
    in_warmup: int | None = None
    dry_status: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.DRYING_STATUS})
    rdt: int | None = field(default=None, metadata={"feature": "is_supported_drying"})
    clean_percent: int | None = field(default=None, metadata={"feature": "is_support_clean_estimate"})
    rss: int | None = None
    dss: int | None = None
    common_status: int | None = None
    corner_clean_mode: int | None = None
    last_clean_t: int | None = None
    replenish_mode: int | None = None
    repeat: int | None = None
    kct: int | None = None
    subdivision_sets: int | None = None

    @property
    def square_meter_clean_area(self) -> float | None:
        return round(self.clean_area / 1000000, 1) if self.clean_area is not None else None

    @property
    def error_code_name(self) -> str | None:
        return self.error_code.name if self.error_code is not None else None

    @property
    def state_name(self) -> str | None:
        return self.state.name if self.state is not None else None

    @property
    def current_map(self) -> int | None:
        """Returns the current map ID if the map is present."""
        if self.map_status is not None:
            map_flag = self.map_status >> 2
            if map_flag != NO_MAP:
                return map_flag
        return None

    @property
    def has_am(self) -> bool | None:
        if self.dss is None:
            return None
        return (self.dss & 3) == 2

    @property
    @field_metadata(dock_feature="is_washable")
    def clear_water_box_status(self) -> ClearWaterBoxStatus | None:
        if self.dss:
            return ClearWaterBoxStatus((self.dss >> 2) & 3)
        return None

    @property
    @field_metadata(dock_feature="is_washable")
    def dirty_water_box_status(self) -> DirtyWaterBoxStatus | None:
        if self.dss:
            return DirtyWaterBoxStatus((self.dss >> 4) & 3)
        return None

    @property
    def dust_bag_status(self) -> DustBagStatus | None:
        if self.dss:
            return DustBagStatus((self.dss >> 6) & 3)
        return None

    @property
    def water_box_filter_status(self) -> int | None:
        if self.dss:
            return (self.dss >> 8) & 3
        return None

    @property
    @field_metadata(
        dock_feature="is_clean_fluid_auto_delivery_supported",
    )
    def clean_fluid_status(self) -> CleanFluidStatus | None:
        if self.dss:
            value = (self.dss >> 10) & 3
            if value == 0:
                return None  # Feature not supported by this device
            return CleanFluidStatus(value)
        return None

    @property
    def hatch_door_status(self) -> int | None:
        if self.dss:
            return (self.dss >> 12) & 7
        return None

    @property
    def dock_cool_fan_status(self) -> int | None:
        if self.dss:
            return (self.dss >> 15) & 3
        return None

    @property
    def dock_state(self) -> RoborockDockState:
        """A synthesized, high-level dock state reflecting the UI's display.

        This property simplifies integration by handling the complex logic
        of checking state, charge_status, and battery level simultaneously. It handles
        newer off-peak charging logic seamlessly while maintaining backwards compatibility
        with older devices.
        """
        if self.state is None or self.state == RoborockStateCode.unknown:
            return RoborockDockState.unknown

        # 6. DUSTING
        if self.state == RoborockStateCode.emptying_the_bin:
            return RoborockDockState.dusting

        # 5. FULL
        if self.state == RoborockStateCode.charging_complete or (
            self.state == RoborockStateCode.charging and self.battery == 100
        ):
            return RoborockDockState.full

        # 3 & 4. CHARGING and CHARGE_WAITING
        if self.state == RoborockStateCode.charging:
            if self.charge_status == RoborockChargeStatus.charge_waiting:
                return RoborockDockState.off_peak_waiting
            return RoborockDockState.charging

        # 2. RECHARGING
        if self.state in (RoborockStateCode.returning_home, RoborockStateCode.docking):
            return RoborockDockState.returning

        # 1. IDLE (Not on dock, or doing something else)
        return RoborockDockState.idle

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class DnDTimer(RoborockBaseTimer):
    """DnDTimer"""


@dataclass
class ValleyElectricityTimer(RoborockBaseTimer):
    """ValleyElectricityTimer"""


@dataclass
class CleanSummary(RoborockBase):
    clean_time: int | None = None
    clean_area: int | None = None
    clean_count: int | None = None
    dust_collection_count: int | None = None
    records: list[int] | None = None
    last_clean_t: int | None = None

    @property
    def square_meter_clean_area(self) -> float | None:
        """Returns the clean area in square meters."""
        if isinstance(self.clean_area, list | str):
            _LOGGER.warning(f"Clean area is a unexpected type! Please give the following in a issue: {self.clean_area}")
            return None
        return round(self.clean_area / 1000000, 1) if self.clean_area is not None else None

    def __repr__(self) -> str:
        """Return a string representation of the object including all attributes."""
        return _attr_repr(self)


@dataclass
class CleanRecord(RoborockBase):
    begin: int | None = None
    end: int | None = None
    duration: int | None = None
    area: int | None = None
    error: int | None = None
    complete: int | None = None
    start_type: RoborockStartType | None = None
    clean_type: RoborockCleanType | None = None
    finish_reason: RoborockFinishReason | None = None
    dust_collection_status: int | None = None
    avoid_count: int | None = None
    wash_count: int | None = None
    map_flag: int | None = None

    @property
    def square_meter_area(self) -> float | None:
        return round(self.area / 1000000, 1) if self.area is not None else None

    @property
    def begin_datetime(self) -> datetime.datetime | None:
        return datetime.datetime.fromtimestamp(self.begin).astimezone(datetime.UTC) if self.begin else None

    @property
    def end_datetime(self) -> datetime.datetime | None:
        return datetime.datetime.fromtimestamp(self.end).astimezone(datetime.UTC) if self.end else None

    def __repr__(self) -> str:
        return _attr_repr(self)


class CleanSummaryWithDetail(CleanSummary):
    """CleanSummary with the last CleanRecord included."""

    last_clean_record: CleanRecord | None = None


class ConsumableField(FieldNameBase):
    """An enum that represents a field in the `Consumable` class.

    This is used with `roborock.devices.traits.v1.status.DeviceFeaturesTrait`
    to understand if a feature is supported by the device using `is_field_supported`.

    The enum values are names of fields in the `Consumable` class. Each field is
    annotated with `dps` metadata to map the field to a `RoborockDataProtocol`
    value used to check support against the product schema.
    """

    MAIN_BRUSH_WORK_TIME = "main_brush_work_time"
    SIDE_BRUSH_WORK_TIME = "side_brush_work_time"
    FILTER_WORK_TIME = "filter_work_time"


@dataclass
class Consumable(RoborockBase):
    main_brush_work_time: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.MAIN_BRUSH_WORK_TIME})
    side_brush_work_time: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.SIDE_BRUSH_WORK_TIME})
    filter_work_time: int | None = field(default=None, metadata={"dps": RoborockDataProtocol.FILTER_WORK_TIME})
    filter_element_work_time: int | None = None
    sensor_dirty_time: int | None = None
    strainer_work_times: int | None = None
    dust_collection_work_times: int | None = None
    cleaning_brush_work_times: int | None = None
    moproller_work_time: int | None = None

    @property
    def main_brush_time_left(self) -> int | None:
        return MAIN_BRUSH_REPLACE_TIME - self.main_brush_work_time if self.main_brush_work_time is not None else None

    @property
    def side_brush_time_left(self) -> int | None:
        return SIDE_BRUSH_REPLACE_TIME - self.side_brush_work_time if self.side_brush_work_time is not None else None

    @property
    def filter_time_left(self) -> int | None:
        return FILTER_REPLACE_TIME - self.filter_work_time if self.filter_work_time is not None else None

    @property
    def sensor_time_left(self) -> int | None:
        return SENSOR_DIRTY_REPLACE_TIME - self.sensor_dirty_time if self.sensor_dirty_time is not None else None

    @property
    def strainer_time_left(self) -> int | None:
        return STRAINER_REPLACE_TIME - self.strainer_work_times if self.strainer_work_times is not None else None

    @property
    def dust_collection_time_left(self) -> int | None:
        return (
            DUST_COLLECTION_REPLACE_TIME - self.dust_collection_work_times
            if self.dust_collection_work_times is not None
            else None
        )

    @property
    def cleaning_brush_time_left(self) -> int | None:
        return (
            CLEANING_BRUSH_REPLACE_TIME - self.cleaning_brush_work_times
            if self.cleaning_brush_work_times is not None
            else None
        )

    @property
    def mop_roller_time_left(self) -> int | None:
        return MOP_ROLLER_REPLACE_TIME - self.moproller_work_time if self.moproller_work_time is not None else None

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class MultiMapsListRoom(RoborockBase):
    id: int | None = None
    tag: int | None = None
    iot_name_id: str | None = None
    iot_name: str | None = None

    @property
    def named_room_mapping(self) -> NamedRoomMapping | None:
        """Returns a NamedRoomMapping object if valid."""
        if self.id is None or self.iot_name_id is None:
            return None
        return NamedRoomMapping(
            segment_id=self.id,
            iot_id=self.iot_name_id,
            raw_name=self.iot_name,
        )


@dataclass
class MultiMapsListMapInfoBakMaps(RoborockBase):
    mapflag: Any | None = None
    add_time: Any | None = None


@dataclass
class MultiMapsListMapInfo(RoborockBase):
    map_flag: int
    name: str
    add_time: Any | None = None
    length: Any | None = None
    bak_maps: list[MultiMapsListMapInfoBakMaps] | None = None
    rooms: list[MultiMapsListRoom] | None = None

    @property
    def mapFlag(self) -> int:
        """Alias for map_flag, returns the map flag as an integer."""
        return self.map_flag

    @property
    def rooms_map(self) -> dict[int, NamedRoomMapping]:
        """Returns a dictionary of room mappings by segment id."""
        return {
            room.id: mapping
            for room in self.rooms or ()
            if room.id is not None and (mapping := room.named_room_mapping) is not None
        }


@dataclass
class MultiMapsList(RoborockBase):
    max_multi_map: int | None = None
    max_bak_map: int | None = None
    multi_map_count: int | None = None
    map_info: list[MultiMapsListMapInfo] | None = None


@dataclass
class SmartWashParams(RoborockBase):
    smart_wash: int | None = None
    wash_interval: int | None = None


@dataclass
class DustCollectionMode(RoborockBase):
    mode: RoborockDockDustCollectionModeCode | None = None


@dataclass
class WashTowelMode(RoborockBase):
    wash_mode: WashTowelModes | None = None


@dataclass
class NetworkInfo(RoborockBase):
    ip: str
    ssid: str | None = None
    mac: str | None = None
    bssid: str | None = None
    rssi: int | None = None


@dataclass
class AppInitStatusLocalInfo(RoborockBase):
    location: str
    bom: str | None = None
    featureset: int | None = None
    language: str | None = None
    logserver: str | None = None
    wifiplan: str | None = None
    timezone: str | None = None
    name: str | None = None


@dataclass
class AppInitStatus(RoborockBase):
    local_info: AppInitStatusLocalInfo
    feature_info: list[int]
    new_feature_info: int = 0
    new_feature_info_str: str = ""
    new_feature_info_2: int | None = None
    carriage_type: int | None = None
    dsp_version: str | None = None


@dataclass
class ChildLockStatus(RoborockBase):
    lock_status: int = 0


@dataclass
class FlowLedStatus(RoborockBase):
    status: int = 0


@dataclass
class LedStatus(RoborockBase):
    status: int = 0

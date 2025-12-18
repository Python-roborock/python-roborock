import datetime
import logging
from dataclasses import dataclass
from typing import Any

from roborock.const import (
    CLEANING_BRUSH_REPLACE_TIME,
    DUST_COLLECTION_REPLACE_TIME,
    FILTER_REPLACE_TIME,
    MAIN_BRUSH_REPLACE_TIME,
    MOP_ROLLER_REPLACE_TIME,
    NO_MAP,
    ROBOROCK_G10S_PRO,
    ROBOROCK_P10,
    ROBOROCK_Q7_MAX,
    ROBOROCK_QREVO_CURV,
    ROBOROCK_QREVO_MASTER,
    ROBOROCK_QREVO_MAXV,
    ROBOROCK_QREVO_PRO,
    ROBOROCK_QREVO_S,
    ROBOROCK_S4_MAX,
    ROBOROCK_S5_MAX,
    ROBOROCK_S6,
    ROBOROCK_S6_MAXV,
    ROBOROCK_S6_PURE,
    ROBOROCK_S7,
    ROBOROCK_S7_MAXV,
    ROBOROCK_S8,
    ROBOROCK_S8_MAXV_ULTRA,
    ROBOROCK_S8_PRO_ULTRA,
    ROBOROCK_SAROS_10,
    ROBOROCK_SAROS_10R,
    SENSOR_DIRTY_REPLACE_TIME,
    SIDE_BRUSH_REPLACE_TIME,
    STRAINER_REPLACE_TIME,
    ROBOROCK_G20S_Ultra,
)
from roborock.exceptions import RoborockException

from ..containers import RoborockBase, RoborockBaseTimer, _attr_repr
from .v1_code_mappings import (
    CleanFluidStatus,
    ClearWaterBoxStatus,
    DirtyWaterBoxStatus,
    DustBagStatus,
    RoborockCleanType,
    RoborockDockDustCollectionModeCode,
    RoborockDockErrorCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
    RoborockErrorCode,
    RoborockFanPowerCode,
    RoborockFanSpeedP10,
    RoborockFanSpeedQ7Max,
    RoborockFanSpeedQRevoCurv,
    RoborockFanSpeedQRevoMaster,
    RoborockFanSpeedQRevoMaxV,
    RoborockFanSpeedS6Pure,
    RoborockFanSpeedS7,
    RoborockFanSpeedS7MaxV,
    RoborockFanSpeedS8MaxVUltra,
    RoborockFanSpeedSaros10,
    RoborockFanSpeedSaros10R,
    RoborockFinishReason,
    RoborockInCleaning,
    RoborockMopIntensityCode,
    RoborockMopIntensityP10,
    RoborockMopIntensityQ7Max,
    RoborockMopIntensityQRevoCurv,
    RoborockMopIntensityQRevoMaster,
    RoborockMopIntensityQRevoMaxV,
    RoborockMopIntensityS5Max,
    RoborockMopIntensityS6MaxV,
    RoborockMopIntensityS7,
    RoborockMopIntensityS8MaxVUltra,
    RoborockMopIntensitySaros10,
    RoborockMopIntensitySaros10R,
    RoborockMopModeCode,
    RoborockMopModeQRevoCurv,
    RoborockMopModeQRevoMaster,
    RoborockMopModeQRevoMaxV,
    RoborockMopModeS7,
    RoborockMopModeS8MaxVUltra,
    RoborockMopModeS8ProUltra,
    RoborockMopModeSaros10,
    RoborockMopModeSaros10R,
    RoborockStartType,
    RoborockStateCode,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Status(RoborockBase):
    """This status will be depreciated in favor of StatusV2."""

    msg_ver: int | None = None
    msg_seq: int | None = None
    state: RoborockStateCode | None = None
    battery: int | None = None
    clean_time: int | None = None
    clean_area: int | None = None
    error_code: RoborockErrorCode | None = None
    map_present: int | None = None
    in_cleaning: RoborockInCleaning | None = None
    in_returning: int | None = None
    in_fresh_state: int | None = None
    lab_status: int | None = None
    water_box_status: int | None = None
    back_type: int | None = None
    wash_phase: int | None = None
    wash_ready: int | None = None
    fan_power: RoborockFanPowerCode | None = None
    dnd_enabled: int | None = None
    map_status: int | None = None
    is_locating: int | None = None
    lock_status: int | None = None
    water_box_mode: RoborockMopIntensityCode | None = None
    water_box_carriage_status: int | None = None
    mop_forbidden_enable: int | None = None
    camera_status: int | None = None
    is_exploring: int | None = None
    home_sec_status: int | None = None
    home_sec_enable_password: int | None = None
    adbumper_status: list[int] | None = None
    water_shortage_status: int | None = None
    dock_type: RoborockDockTypeCode | None = None
    dust_collection_status: int | None = None
    auto_dust_collection: int | None = None
    avoid_count: int | None = None
    mop_mode: RoborockMopModeCode | None = None
    debug_mode: int | None = None
    collision_avoid_status: int | None = None
    switch_map_mode: int | None = None
    dock_error_status: RoborockDockErrorCode | None = None
    charge_status: int | None = None
    unsave_map_reason: int | None = None
    unsave_map_flag: int | None = None
    wash_status: int | None = None
    distance_off: int | None = None
    in_warmup: int | None = None
    dry_status: int | None = None
    rdt: int | None = None
    clean_percent: int | None = None
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
    def water_box_mode_name(self) -> str | None:
        return self.water_box_mode.name if self.water_box_mode is not None else None

    @property
    def fan_power_options(self) -> list[str]:
        if self.fan_power is None:
            return []
        return list(self.fan_power.keys())

    @property
    def fan_power_name(self) -> str | None:
        return self.fan_power.name if self.fan_power is not None else None

    @property
    def mop_mode_name(self) -> str | None:
        return self.mop_mode.name if self.mop_mode is not None else None

    def get_fan_speed_code(self, fan_speed: str) -> int:
        if self.fan_power is None:
            raise RoborockException("Attempted to get fan speed before status has been updated.")
        return self.fan_power.as_dict().get(fan_speed)

    def get_mop_intensity_code(self, mop_intensity: str) -> int:
        if self.water_box_mode is None:
            raise RoborockException("Attempted to get mop_intensity before status has been updated.")
        return self.water_box_mode.as_dict().get(mop_intensity)

    def get_mop_mode_code(self, mop_mode: str) -> int:
        if self.mop_mode is None:
            raise RoborockException("Attempted to get mop_mode before status has been updated.")
        return self.mop_mode.as_dict().get(mop_mode)

    @property
    def current_map(self) -> int | None:
        """Returns the current map ID if the map is present."""
        if self.map_status is not None:
            map_flag = self.map_status >> 2
            if map_flag != NO_MAP:
                return map_flag
        return None

    @property
    def clear_water_box_status(self) -> ClearWaterBoxStatus | None:
        if self.dss:
            return ClearWaterBoxStatus((self.dss >> 2) & 3)
        return None

    @property
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

    def __repr__(self) -> str:
        return _attr_repr(self)


class StatusV2(RoborockBase):
    """
    This is a new version of the Status object.
    This is the result of GET_STATUS from the api.
    """

    msg_ver: int | None = None
    msg_seq: int | None = None
    state: RoborockStateCode | None = None
    battery: int | None = None
    clean_time: int | None = None
    clean_area: int | None = None
    error_code: RoborockErrorCode | None = None
    map_present: int | None = None
    in_cleaning: RoborockInCleaning | None = None
    in_returning: int | None = None
    in_fresh_state: int | None = None
    lab_status: int | None = None
    water_box_status: int | None = None
    back_type: int | None = None
    wash_phase: int | None = None
    wash_ready: int | None = None
    fan_power: int | None = None
    dnd_enabled: int | None = None
    map_status: int | None = None
    is_locating: int | None = None
    lock_status: int | None = None
    water_box_mode: int | None = None
    water_box_carriage_status: int | None = None
    mop_forbidden_enable: int | None = None
    camera_status: int | None = None
    is_exploring: int | None = None
    home_sec_status: int | None = None
    home_sec_enable_password: int | None = None
    adbumper_status: list[int] | None = None
    water_shortage_status: int | None = None
    dock_type: RoborockDockTypeCode | None = None
    dust_collection_status: int | None = None
    auto_dust_collection: int | None = None
    avoid_count: int | None = None
    mop_mode: int | None = None
    debug_mode: int | None = None
    collision_avoid_status: int | None = None
    switch_map_mode: int | None = None
    dock_error_status: RoborockDockErrorCode | None = None
    charge_status: int | None = None
    unsave_map_reason: int | None = None
    unsave_map_flag: int | None = None
    wash_status: int | None = None
    distance_off: int | None = None
    in_warmup: int | None = None
    dry_status: int | None = None
    rdt: int | None = None
    clean_percent: int | None = None
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
    def clear_water_box_status(self) -> ClearWaterBoxStatus | None:
        if self.dss:
            return ClearWaterBoxStatus((self.dss >> 2) & 3)
        return None

    @property
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
    def clean_fluid_status(self) -> int | None:
        if self.dss:
            return (self.dss >> 10) & 3
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

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class S4MaxStatus(Status):
    fan_power: RoborockFanSpeedS6Pure | None = None
    water_box_mode: RoborockMopIntensityS7 | None = None
    mop_mode: RoborockMopModeS7 | None = None


@dataclass
class S5MaxStatus(Status):
    fan_power: RoborockFanSpeedS6Pure | None = None
    water_box_mode: RoborockMopIntensityS5Max | None = None


@dataclass
class Q7MaxStatus(Status):
    fan_power: RoborockFanSpeedQ7Max | None = None
    water_box_mode: RoborockMopIntensityQ7Max | None = None


@dataclass
class QRevoMasterStatus(Status):
    fan_power: RoborockFanSpeedQRevoMaster | None = None
    water_box_mode: RoborockMopIntensityQRevoMaster | None = None
    mop_mode: RoborockMopModeQRevoMaster | None = None


@dataclass
class QRevoCurvStatus(Status):
    fan_power: RoborockFanSpeedQRevoCurv | None = None
    water_box_mode: RoborockMopIntensityQRevoCurv | None = None
    mop_mode: RoborockMopModeQRevoCurv | None = None


@dataclass
class QRevoMaxVStatus(Status):
    fan_power: RoborockFanSpeedQRevoMaxV | None = None
    water_box_mode: RoborockMopIntensityQRevoMaxV | None = None
    mop_mode: RoborockMopModeQRevoMaxV | None = None


@dataclass
class S6MaxVStatus(Status):
    fan_power: RoborockFanSpeedS7MaxV | None = None
    water_box_mode: RoborockMopIntensityS6MaxV | None = None


@dataclass
class S6PureStatus(Status):
    fan_power: RoborockFanSpeedS6Pure | None = None


@dataclass
class S7MaxVStatus(Status):
    fan_power: RoborockFanSpeedS7MaxV | None = None
    water_box_mode: RoborockMopIntensityS7 | None = None
    mop_mode: RoborockMopModeS7 | None = None


@dataclass
class S7Status(Status):
    fan_power: RoborockFanSpeedS7 | None = None
    water_box_mode: RoborockMopIntensityS7 | None = None
    mop_mode: RoborockMopModeS7 | None = None


@dataclass
class S8ProUltraStatus(Status):
    fan_power: RoborockFanSpeedS7MaxV | None = None
    water_box_mode: RoborockMopIntensityS7 | None = None
    mop_mode: RoborockMopModeS8ProUltra | None = None


@dataclass
class S8Status(Status):
    fan_power: RoborockFanSpeedS7MaxV | None = None
    water_box_mode: RoborockMopIntensityS7 | None = None
    mop_mode: RoborockMopModeS8ProUltra | None = None


@dataclass
class P10Status(Status):
    fan_power: RoborockFanSpeedP10 | None = None
    water_box_mode: RoborockMopIntensityP10 | None = None
    mop_mode: RoborockMopModeS8ProUltra | None = None


@dataclass
class S8MaxvUltraStatus(Status):
    fan_power: RoborockFanSpeedS8MaxVUltra | None = None
    water_box_mode: RoborockMopIntensityS8MaxVUltra | None = None
    mop_mode: RoborockMopModeS8MaxVUltra | None = None


@dataclass
class Saros10RStatus(Status):
    fan_power: RoborockFanSpeedSaros10R | None = None
    water_box_mode: RoborockMopIntensitySaros10R | None = None
    mop_mode: RoborockMopModeSaros10R | None = None


@dataclass
class Saros10Status(Status):
    fan_power: RoborockFanSpeedSaros10 | None = None
    water_box_mode: RoborockMopIntensitySaros10 | None = None
    mop_mode: RoborockMopModeSaros10 | None = None


ModelStatus: dict[str, type[Status]] = {
    ROBOROCK_S4_MAX: S4MaxStatus,
    ROBOROCK_S5_MAX: S5MaxStatus,
    ROBOROCK_Q7_MAX: Q7MaxStatus,
    ROBOROCK_QREVO_MASTER: QRevoMasterStatus,
    ROBOROCK_QREVO_CURV: QRevoCurvStatus,
    ROBOROCK_S6: S6PureStatus,
    ROBOROCK_S6_MAXV: S6MaxVStatus,
    ROBOROCK_S6_PURE: S6PureStatus,
    ROBOROCK_S7_MAXV: S7MaxVStatus,
    ROBOROCK_S7: S7Status,
    ROBOROCK_S8: S8Status,
    ROBOROCK_S8_PRO_ULTRA: S8ProUltraStatus,
    ROBOROCK_G10S_PRO: S7MaxVStatus,
    ROBOROCK_G20S_Ultra: QRevoMasterStatus,
    ROBOROCK_P10: P10Status,
    # These likely are not correct,
    # but i am currently unable to do my typical reverse engineering/ get any data from users on this,
    # so this will be here in the mean time.
    ROBOROCK_QREVO_S: P10Status,
    ROBOROCK_QREVO_MAXV: QRevoMaxVStatus,
    ROBOROCK_QREVO_PRO: P10Status,
    ROBOROCK_S8_MAXV_ULTRA: S8MaxvUltraStatus,
    ROBOROCK_SAROS_10R: Saros10RStatus,
    ROBOROCK_SAROS_10: Saros10Status,
}


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


@dataclass
class Consumable(RoborockBase):
    main_brush_work_time: int | None = None
    side_brush_work_time: int | None = None
    filter_work_time: int | None = None
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

    @property
    def mapFlag(self) -> int:
        """Alias for map_flag, returns the map flag as an integer."""
        return self.map_flag


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
    wash_mode: RoborockDockWashTowelModeCode | None = None


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
    new_feature_info: int
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

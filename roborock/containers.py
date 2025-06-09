from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import timezone
from enum import Enum
from typing import Any, NamedTuple, get_args, get_origin

from .code_mappings import (
    RoborockCategory,
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
    RoborockMopModeCode,
    RoborockMopModeQRevoCurv,
    RoborockMopModeQRevoMaster,
    RoborockMopModeQRevoMaxV,
    RoborockMopModeS7,
    RoborockMopModeS8MaxVUltra,
    RoborockMopModeS8ProUltra,
    RoborockStartType,
    RoborockStateCode,
)
from .const import (
    CLEANING_BRUSH_REPLACE_TIME,
    DUST_COLLECTION_REPLACE_TIME,
    FILTER_REPLACE_TIME,
    MAIN_BRUSH_REPLACE_TIME,
    MOP_ROLLER_REPLACE_TIME,
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
    SENSOR_DIRTY_REPLACE_TIME,
    SIDE_BRUSH_REPLACE_TIME,
    STRAINER_REPLACE_TIME,
    ROBOROCK_G20S_Ultra,
)
from .exceptions import RoborockException

_LOGGER = logging.getLogger(__name__)


def camelize(s: str):
    first, *others = s.split("_")
    if len(others) == 0:
        return s
    return "".join([first.lower(), *map(str.title, others)])


def decamelize(s: str):
    return re.sub("([A-Z]+)", "_\\1", s).lower()


def decamelize_obj(d: dict | list, ignore_keys: list[str]):
    if isinstance(d, RoborockBase):
        d = d.as_dict()
    if isinstance(d, list):
        return [decamelize_obj(i, ignore_keys) if isinstance(i, dict | list) else i for i in d]
    return {
        (decamelize(a) if a not in ignore_keys else a): decamelize_obj(b, ignore_keys)
        if isinstance(b, dict | list)
        else b
        for a, b in d.items()
    }


@dataclass
class RoborockBase:
    _ignore_keys = []  # type: ignore
    is_cached = False

    @staticmethod
    def convert_to_class_obj(type, value):
        try:
            class_type = eval(type)
            if get_origin(class_type) is list:
                return_list = []
                cls_type = get_args(class_type)[0]
                for obj in value:
                    if issubclass(cls_type, RoborockBase):
                        return_list.append(cls_type.from_dict(obj))
                    elif cls_type in {str, int, float}:
                        return_list.append(cls_type(obj))
                    else:
                        return_list.append(cls_type(**obj))
                return return_list
            if issubclass(class_type, RoborockBase):
                converted_value = class_type.from_dict(value)
            else:
                converted_value = class_type(value)
            return converted_value
        except NameError as err:
            _LOGGER.exception(err)
        except ValueError as err:
            _LOGGER.exception(err)
        except Exception as err:
            _LOGGER.exception(err)
        raise Exception("Fail")

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        if isinstance(data, dict):
            ignore_keys = cls._ignore_keys
            data = decamelize_obj(data, ignore_keys)
            cls_annotations: dict[str, str] = {}
            for base in reversed(cls.__mro__):
                cls_annotations.update(getattr(base, "__annotations__", {}))
            remove_keys = []
            for key, value in data.items():
                if key not in cls_annotations:
                    remove_keys.append(key)
                    continue
                if value == "None" or value is None:
                    data[key] = None
                    continue
                field_type: str = cls_annotations[key]
                if "|" in field_type:
                    # It's a union
                    types = field_type.split("|")
                    for type in types:
                        if "None" in type or "Any" in type:
                            continue
                        try:
                            data[key] = RoborockBase.convert_to_class_obj(type, value)
                            break
                        except Exception:
                            ...
                else:
                    try:
                        data[key] = RoborockBase.convert_to_class_obj(field_type, value)
                    except Exception:
                        ...
            for key in remove_keys:
                del data[key]
            return cls(**data)

    def as_dict(self) -> dict:
        return asdict(
            self,
            dict_factory=lambda _fields: {
                camelize(key): value.value if isinstance(value, Enum) else value
                for (key, value) in _fields
                if value is not None
            },
        )


@dataclass
class RoborockBaseTimer(RoborockBase):
    start_hour: int | None = None
    start_minute: int | None = None
    end_hour: int | None = None
    end_minute: int | None = None
    enabled: int | None = None
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None

    def __post_init__(self) -> None:
        self.start_time = (
            datetime.time(hour=self.start_hour, minute=self.start_minute)
            if self.start_hour is not None and self.start_minute is not None
            else None
        )
        self.end_time = (
            datetime.time(hour=self.end_hour, minute=self.end_minute)
            if self.end_hour is not None and self.end_minute is not None
            else None
        )


@dataclass
class Reference(RoborockBase):
    r: str | None = None
    a: str | None = None
    m: str | None = None
    l: str | None = None


@dataclass
class RRiot(RoborockBase):
    u: str
    s: str
    h: str
    k: str
    r: Reference


@dataclass
class UserData(RoborockBase):
    rriot: RRiot
    uid: int | None = None
    tokentype: str | None = None
    token: str | None = None
    rruid: str | None = None
    region: str | None = None
    countrycode: str | None = None
    country: str | None = None
    nickname: str | None = None
    tuya_device_state: int | None = None
    avatarurl: str | None = None


@dataclass
class HomeDataProductSchema(RoborockBase):
    id: Any | None = None
    name: Any | None = None
    code: Any | None = None
    mode: Any | None = None
    type: Any | None = None
    product_property: Any | None = None
    property: Any | None = None
    desc: Any | None = None


@dataclass
class HomeDataProduct(RoborockBase):
    id: str
    name: str
    model: str
    category: RoborockCategory
    code: str | None = None
    icon_url: str | None = None
    attribute: Any | None = None
    capability: int | None = None
    schema: list[HomeDataProductSchema] | None = None


@dataclass
class HomeDataDevice(RoborockBase):
    duid: str
    name: str
    local_key: str
    fv: str
    product_id: str
    attribute: Any | None = None
    active_time: int | None = None
    runtime_env: Any | None = None
    time_zone_id: str | None = None
    icon_url: str | None = None
    lon: Any | None = None
    lat: Any | None = None
    share: Any | None = None
    share_time: Any | None = None
    online: bool | None = None
    pv: str | None = None
    room_id: Any | None = None
    tuya_uuid: Any | None = None
    tuya_migrated: bool | None = None
    extra: Any | None = None
    sn: str | None = None
    feature_set: str | None = None
    new_feature_set: str | None = None
    device_status: dict | None = None
    silent_ota_switch: bool | None = None
    setting: Any | None = None
    f: bool | None = None
    device_features: DeviceFeatures | None = None

    # seemingly not just str like I thought - example: '0000000000002000' and '0000000000002F63'

    # def __post_init__(self):
    #     if self.feature_set is not None and self.new_feature_set is not None and self.new_feature_set != "":
    #         self.device_features = build_device_features(self.feature_set, self.new_feature_set)


@dataclass
class DeviceFeatures(RoborockBase):
    map_carpet_add_supported: bool
    show_clean_finish_reason_supported: bool
    resegment_supported: bool
    video_monitor_supported: bool
    any_state_transit_goto_supported: bool
    fw_filter_obstacle_supported: bool
    video_setting_supported: bool
    ignore_unknown_map_object_supported: bool
    set_child_supported: bool
    carpet_supported: bool
    mop_path_supported: bool
    multi_map_segment_timer_supported: bool
    custom_water_box_distance_supported: bool
    wash_then_charge_cmd_supported: bool
    room_name_supported: bool
    current_map_restore_enabled: bool
    photo_upload_supported: bool
    shake_mop_set_supported: bool
    map_beautify_internal_debug_supported: bool
    new_data_for_clean_history: bool
    new_data_for_clean_history_detail: bool
    flow_led_setting_supported: bool
    dust_collection_setting_supported: bool
    rpc_retry_supported: bool
    avoid_collision_supported: bool
    support_set_switch_map_mode: bool
    support_smart_scene: bool
    support_floor_edit: bool
    support_furniture: bool
    support_room_tag: bool
    support_quick_map_builder: bool
    support_smart_global_clean_with_custom_mode: bool
    record_allowed: bool
    careful_slow_map_supported: bool
    egg_mode_supported: bool
    unsave_map_reason_supported: bool
    carpet_show_on_map: bool
    supported_valley_electricity: bool
    drying_supported: bool
    download_test_voice_supported: bool
    support_backup_map: bool
    support_custom_mode_in_cleaning: bool
    support_remote_control_in_call: bool
    support_set_volume_in_call: bool
    support_clean_estimate: bool
    support_custom_dnd: bool
    carpet_deep_clean_supported: bool
    stuck_zone_supported: bool
    custom_door_sill_supported: bool
    clean_route_fast_mode_supported: bool
    cliff_zone_supported: bool
    smart_door_sill_supported: bool
    support_floor_direction: bool
    wifi_manage_supported: bool
    back_charge_auto_wash_supported: bool
    support_incremental_map: bool
    offline_map_supported: bool


def build_device_features(feature_set: str, new_feature_set: str) -> DeviceFeatures:
    new_feature_set_int = int(new_feature_set)
    feature_set_int = int(feature_set)
    new_feature_set_divided = int(new_feature_set_int / (2**32))
    # Convert last 8 digits of new feature set into hexadecimal number
    converted_new_feature_set = int("0x" + new_feature_set[-8:], 16)
    new_feature_set_mod_8: bool = len(new_feature_set) % 8 == 0
    return DeviceFeatures(
        map_carpet_add_supported=bool(1073741824 & new_feature_set_int),
        show_clean_finish_reason_supported=bool(1 & new_feature_set_int),
        resegment_supported=bool(4 & new_feature_set_int),
        video_monitor_supported=bool(8 & new_feature_set_int),
        any_state_transit_goto_supported=bool(16 & new_feature_set_int),
        fw_filter_obstacle_supported=bool(32 & new_feature_set_int),
        video_setting_supported=bool(64 & new_feature_set_int),
        ignore_unknown_map_object_supported=bool(128 & new_feature_set_int),
        set_child_supported=bool(256 & new_feature_set_int),
        carpet_supported=bool(512 & new_feature_set_int),
        mop_path_supported=bool(2048 & new_feature_set_int),
        multi_map_segment_timer_supported=bool(feature_set_int and 4096 & new_feature_set_int),
        custom_water_box_distance_supported=bool(new_feature_set_int and 2147483648 & new_feature_set_int),
        wash_then_charge_cmd_supported=bool((new_feature_set_divided >> 5) & 1),
        room_name_supported=bool(16384 & new_feature_set_int),
        current_map_restore_enabled=bool(8192 & new_feature_set_int),
        photo_upload_supported=bool(65536 & new_feature_set_int),
        shake_mop_set_supported=bool(262144 & new_feature_set_int),
        map_beautify_internal_debug_supported=bool(2097152 & new_feature_set_int),
        new_data_for_clean_history=bool(4194304 & new_feature_set_int),
        new_data_for_clean_history_detail=bool(8388608 & new_feature_set_int),
        flow_led_setting_supported=bool(16777216 & new_feature_set_int),
        dust_collection_setting_supported=bool(33554432 & new_feature_set_int),
        rpc_retry_supported=bool(67108864 & new_feature_set_int),
        avoid_collision_supported=bool(134217728 & new_feature_set_int),
        support_set_switch_map_mode=bool(268435456 & new_feature_set_int),
        support_smart_scene=bool(new_feature_set_divided & 2),
        support_floor_edit=bool(new_feature_set_divided & 8),
        support_furniture=bool((new_feature_set_divided >> 4) & 1),
        support_room_tag=bool((new_feature_set_divided >> 6) & 1),
        support_quick_map_builder=bool((new_feature_set_divided >> 7) & 1),
        support_smart_global_clean_with_custom_mode=bool((new_feature_set_divided >> 8) & 1),
        record_allowed=bool(1024 & new_feature_set_int),
        careful_slow_map_supported=bool((new_feature_set_divided >> 9) & 1),
        egg_mode_supported=bool((new_feature_set_divided >> 10) & 1),
        unsave_map_reason_supported=bool((new_feature_set_divided >> 14) & 1),
        carpet_show_on_map=bool((new_feature_set_divided >> 12) & 1),
        supported_valley_electricity=bool((new_feature_set_divided >> 13) & 1),
        # This one could actually be incorrect
        # ((t.robotNewFeatures / 2 ** 32) >> 15) & 1 && (module422.DMM.isTopazSV_CE || 'cn' == t.deviceLocation));
        drying_supported=bool((new_feature_set_divided >> 15) & 1),
        download_test_voice_supported=bool((new_feature_set_divided >> 16) & 1),
        support_backup_map=bool((new_feature_set_divided >> 17) & 1),
        support_custom_mode_in_cleaning=bool((new_feature_set_divided >> 18) & 1),
        support_remote_control_in_call=bool((new_feature_set_divided >> 19) & 1),
        support_set_volume_in_call=new_feature_set_mod_8 and bool(1 & converted_new_feature_set),
        support_clean_estimate=new_feature_set_mod_8 and bool(2 & converted_new_feature_set),
        support_custom_dnd=new_feature_set_mod_8 and bool(4 & converted_new_feature_set),
        carpet_deep_clean_supported=bool(8 & converted_new_feature_set),
        stuck_zone_supported=new_feature_set_mod_8 and bool(16 & converted_new_feature_set),
        custom_door_sill_supported=new_feature_set_mod_8 and bool(32 & converted_new_feature_set),
        clean_route_fast_mode_supported=bool(256 & converted_new_feature_set),
        cliff_zone_supported=new_feature_set_mod_8 and bool(512 & converted_new_feature_set),
        smart_door_sill_supported=new_feature_set_mod_8 and bool(1024 & converted_new_feature_set),
        support_floor_direction=new_feature_set_mod_8 and bool(2048 & converted_new_feature_set),
        wifi_manage_supported=bool(128 & converted_new_feature_set),
        back_charge_auto_wash_supported=bool(4096 & converted_new_feature_set),
        support_incremental_map=bool(8192 & converted_new_feature_set),
        offline_map_supported=bool(16384 & converted_new_feature_set),
    )


@dataclass
class HomeDataRoom(RoborockBase):
    id: int
    name: str


@dataclass
class HomeDataScene(RoborockBase):
    id: int
    name: str


@dataclass
class HomeData(RoborockBase):
    id: int
    name: str
    products: list[HomeDataProduct] = field(default_factory=lambda: [])
    devices: list[HomeDataDevice] = field(default_factory=lambda: [])
    received_devices: list[HomeDataDevice] = field(default_factory=lambda: [])
    lon: Any | None = None
    lat: Any | None = None
    geo_name: Any | None = None
    rooms: list[HomeDataRoom] = field(default_factory=list)

    def get_all_devices(self) -> list[HomeDataDevice]:
        devices = []
        if self.devices is not None:
            devices += self.devices
        if self.received_devices is not None:
            devices += self.received_devices
        return devices


@dataclass
class LoginData(RoborockBase):
    user_data: UserData
    email: str
    home_data: HomeData | None = None


@dataclass
class Status(RoborockBase):
    msg_ver: int | None = None
    msg_seq: int | None = None
    state: RoborockStateCode | None = None
    battery: int | None = None
    clean_time: int | None = None
    clean_area: int | None = None
    square_meter_clean_area: float | None = None
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
    error_code_name: str | None = None
    state_name: str | None = None
    water_box_mode_name: str | None = None
    fan_power_options: list[str] = field(default_factory=list)
    fan_power_name: str | None = None
    mop_mode_name: str | None = None

    def __post_init__(self) -> None:
        self.square_meter_clean_area = round(self.clean_area / 1000000, 1) if self.clean_area is not None else None
        if self.error_code is not None:
            self.error_code_name = self.error_code.name
        if self.state is not None:
            self.state_name = self.state.name
        if self.water_box_mode is not None:
            self.water_box_mode_name = self.water_box_mode.name
        if self.fan_power is not None:
            self.fan_power_options = self.fan_power.keys()
            self.fan_power_name = self.fan_power.name
        if self.mop_mode is not None:
            self.mop_mode_name = self.mop_mode.name

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
    square_meter_clean_area: float | None = None
    clean_count: int | None = None
    dust_collection_count: int | None = None
    records: list[int] | None = None
    last_clean_t: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.clean_area, list | str):
            _LOGGER.warning(f"Clean area is a unexpected type! Please give the following in a issue: {self.clean_area}")
        else:
            self.square_meter_clean_area = round(self.clean_area / 1000000, 1) if self.clean_area is not None else None


@dataclass
class CleanRecord(RoborockBase):
    begin: int | None = None
    begin_datetime: datetime.datetime | None = None
    end: int | None = None
    end_datetime: datetime.datetime | None = None
    duration: int | None = None
    area: int | None = None
    square_meter_area: float | None = None
    error: int | None = None
    complete: int | None = None
    start_type: RoborockStartType | None = None
    clean_type: RoborockCleanType | None = None
    finish_reason: RoborockFinishReason | None = None
    dust_collection_status: int | None = None
    avoid_count: int | None = None
    wash_count: int | None = None
    map_flag: int | None = None

    def __post_init__(self) -> None:
        self.square_meter_area = round(self.area / 1000000, 1) if self.area is not None else None
        self.begin_datetime = (
            datetime.datetime.fromtimestamp(self.begin).astimezone(timezone.utc) if self.begin else None
        )
        self.end_datetime = datetime.datetime.fromtimestamp(self.end).astimezone(timezone.utc) if self.end else None


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
    main_brush_time_left: int | None = None
    side_brush_time_left: int | None = None
    filter_time_left: int | None = None
    sensor_time_left: int | None = None
    strainer_time_left: int | None = None
    dust_collection_time_left: int | None = None
    cleaning_brush_time_left: int | None = None
    mop_roller_time_left: int | None = None

    def __post_init__(self) -> None:
        self.main_brush_time_left = (
            MAIN_BRUSH_REPLACE_TIME - self.main_brush_work_time if self.main_brush_work_time is not None else None
        )
        self.side_brush_time_left = (
            SIDE_BRUSH_REPLACE_TIME - self.side_brush_work_time if self.side_brush_work_time is not None else None
        )
        self.filter_time_left = (
            FILTER_REPLACE_TIME - self.filter_work_time if self.filter_work_time is not None else None
        )
        self.sensor_time_left = (
            SENSOR_DIRTY_REPLACE_TIME - self.sensor_dirty_time if self.sensor_dirty_time is not None else None
        )
        self.strainer_time_left = (
            STRAINER_REPLACE_TIME - self.strainer_work_times if self.strainer_work_times is not None else None
        )
        self.dust_collection_time_left = (
            DUST_COLLECTION_REPLACE_TIME - self.dust_collection_work_times
            if self.dust_collection_work_times is not None
            else None
        )
        self.cleaning_brush_time_left = (
            CLEANING_BRUSH_REPLACE_TIME - self.cleaning_brush_work_times
            if self.cleaning_brush_work_times is not None
            else None
        )
        self.mop_roller_time_left = (
            MOP_ROLLER_REPLACE_TIME - self.moproller_work_time if self.moproller_work_time is not None else None
        )


@dataclass
class MultiMapsListMapInfoBakMaps(RoborockBase):
    mapflag: Any | None = None
    add_time: Any | None = None


@dataclass
class MultiMapsListMapInfo(RoborockBase):
    _ignore_keys = ["mapFlag"]

    mapFlag: int
    name: str
    add_time: Any | None = None
    length: Any | None = None
    bak_maps: list[MultiMapsListMapInfoBakMaps] | None = None


@dataclass
class MultiMapsList(RoborockBase):
    _ignore_keys = ["mapFlag"]

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
class DeviceData(RoborockBase):
    device: HomeDataDevice
    model: str
    host: str | None = None


@dataclass
class RoomMapping(RoborockBase):
    segment_id: int
    iot_id: str


@dataclass
class ChildLockStatus(RoborockBase):
    lock_status: int


@dataclass
class FlowLedStatus(RoborockBase):
    status: int


@dataclass
class BroadcastMessage(RoborockBase):
    duid: str
    ip: str


class ServerTimer(NamedTuple):
    id: str
    status: str
    dontknow: int


@dataclass
class RoborockProductStateValue(RoborockBase):
    value: list
    desc: dict


@dataclass
class RoborockProductState(RoborockBase):
    dps: int
    desc: dict
    value: list[RoborockProductStateValue]


@dataclass
class RoborockProductSpec(RoborockBase):
    state: RoborockProductState
    battery: dict | None = None
    dry_countdown: dict | None = None
    extra: dict | None = None
    offpeak: dict | None = None
    countdown: dict | None = None
    mode: dict | None = None
    ota_nfo: dict | None = None
    pause: dict | None = None
    program: dict | None = None
    shutdown: dict | None = None
    washing_left: dict | None = None


@dataclass
class RoborockProduct(RoborockBase):
    id: int | None = None
    name: str | None = None
    model: str | None = None
    packagename: str | None = None
    ssid: str | None = None
    picurl: str | None = None
    cardpicurl: str | None = None
    mediumCardpicurl: str | None = None
    resetwifipicurl: str | None = None
    configPicUrl: str | None = None
    pluginPicUrl: str | None = None
    resetwifitext: dict | None = None
    tuyaid: str | None = None
    status: int | None = None
    rriotid: str | None = None
    pictures: list | None = None
    ncMode: str | None = None
    scope: str | None = None
    product_tags: list | None = None
    agreements: list | None = None
    cardspec: str | None = None
    plugin_pic_url: str | None = None
    products_specification: RoborockProductSpec | None = None

    def __post_init__(self):
        if self.cardspec:
            self.products_specification = RoborockProductSpec.from_dict(json.loads(self.cardspec).get("data"))


@dataclass
class RoborockProductCategory(RoborockBase):
    id: int
    display_name: str
    icon_url: str


@dataclass
class RoborockCategoryDetail(RoborockBase):
    category: RoborockProductCategory
    product_list: list[RoborockProduct]


@dataclass
class ProductResponse(RoborockBase):
    category_detail_list: list[RoborockCategoryDetail]


@dataclass
class DyadProductInfo(RoborockBase):
    sn: str
    ssid: str
    timezone: str
    posix_timezone: str
    ip: str
    mac: str
    oba: dict


@dataclass
class DyadSndState(RoborockBase):
    sid_in_use: int
    sid_version: int
    location: str
    bom: str
    language: str


@dataclass
class DyadOtaNfo(RoborockBase):
    mqttOtaData: dict

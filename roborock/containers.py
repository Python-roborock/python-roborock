from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import timezone
from enum import Enum, IntEnum
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
    RoborockMopIntensityS5Max,
    RoborockMopIntensityS6MaxV,
    RoborockMopIntensityS7,
    RoborockMopIntensityS8MaxVUltra,
    RoborockMopModeCode,
    RoborockMopModeQRevoCurv,
    RoborockMopModeQRevoMaster,
    RoborockMopModeS7,
    RoborockMopModeS8MaxVUltra,
    RoborockMopModeS8ProUltra,
    RoborockProductNickname,
    RoborockStartType,
    RoborockStateCode,
    short_model_to_enum,
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


class NewFeatureStrBit(IntEnum):
    TWO_KEY_REAL_TIME_VIDEO = 32
    TWO_KEY_RTV_IN_CHARGING = 33
    DIRTY_REPLENISH_CLEAN = 34
    AUTO_DELIVERY_FIELD_IN_GLOBAL_STATUS = 35
    AVOID_COLLISION_MODE = 36
    VOICE_CONTROL = 37
    NEW_ENDPOINT = 38
    PUMPING_WATER = 39
    CORNER_MOP_STRECH = 40
    HOT_WASH_TOWEL = 41
    FLOOR_DIR_CLEAN_ANY_TIME = 42
    PET_SUPPLIES_DEEP_CLEAN = 43
    MOP_SHAKE_WATER_MAX = 45
    EXACT_CUSTOM_MODE = 47
    CARPET_CUSTOM_CLEAN = 49
    PET_SNAPSHOT = 50
    CUSTOM_CLEAN_MODE_COUNT = 51
    NEW_AI_RECOGNITION = 52
    AUTO_COLLECTION_2 = 53
    RIGHT_BRUSH_STRETCH = 54
    SMART_CLEAN_MODE_SET = 55
    DIRTY_OBJECT_DETECT = 56
    NO_NEED_CARPET_PRESS_SET = 57
    VOICE_CONTROL_LED = 58
    WATER_LEAK_CHECK = 60
    MIN_BATTERY_15_TO_CLEAN_TASK = 62
    GAP_DEEP_CLEAN = 63
    OBJECT_DETECT_CHECK = 64
    IDENTIFY_ROOM = 66
    MATTER = 67
    WORKDAY_HOLIDAY = 69
    CLEAN_DIRECT_STATUS = 70
    MAP_ERASER = 71
    OPTIMIZE_BATTERY = 72
    ACTIVATE_VIDEO_CHARGING_AND_STANDBY = 73
    CARPET_LONG_HAIRED = 75
    CLEAN_HISTORY_TIME_LINE = 76
    MAX_ZONE_OPENED = 77
    EXHIBITION_FUNCTION = 78
    LDS_LIFTING = 79
    AUTO_TEAR_DOWN_MOP = 80
    SAMLL_SIDE_MOP = 81
    SUPPORT_SIDE_BRUSH_UP_DOWN = 82
    DRY_INTERVAL_TIMER = 83
    UVC_STERILIZE = 84
    MIDWAY_BACK_TO_DOCK = 85
    SUPPORT_MAIN_BRUSH_UP_DOWN = 86
    EGG_DANCE_MODE = 87


@dataclass
class DeviceFeatures(RoborockBase):
    """Represents the features supported by a Roborock device."""

    # Features derived from robot_new_features
    is_map_carpet_add_support: bool
    is_show_clean_finish_reason_supported: bool
    is_resegment_supported: bool
    is_video_monitor_supported: bool
    is_any_state_transit_goto_supported: bool
    is_fw_filter_obstacle_supported: bool
    is_video_settings_supported: bool
    is_ignore_unknown_map_object_supported: bool
    is_set_child_supported: bool
    is_carpet_supported: bool
    is_mop_path_supported: bool
    is_multi_map_segment_timer_supported: bool
    is_custom_water_box_distance_supported: bool
    is_wash_then_charge_cmd_supported: bool
    is_room_name_supported: bool
    is_current_map_restore_enabled: bool
    is_photo_upload_supported: bool
    is_shake_mop_set_supported: bool
    is_map_beautify_internal_debug_supported: bool
    is_new_data_for_clean_history_supported: bool
    is_new_data_for_clean_history_detail_supported: bool
    is_flow_led_setting_supported: bool
    is_dust_collection_setting_supported: bool
    is_rpc_retry_supported: bool
    is_avoid_collision_supported: bool
    is_support_set_switch_map_mode_supported: bool
    is_support_smart_scene_supported: bool
    is_support_floor_edit_supported: bool
    is_support_furniture_supported: bool
    is_support_room_tag_supported: bool
    is_support_quick_map_builder_supported: bool
    is_support_smart_global_clean_with_custom_mode_supported: bool
    is_record_allowed: bool
    is_careful_slow_mop_supported: bool
    is_egg_mode_supported: bool
    is_carpet_show_on_map_supported: bool
    is_supported_valley_electricity_supported: bool
    is_unsave_map_reason_supported: bool
    is_supported_drying_supported: bool
    is_supported_download_test_voice_supported: bool
    is_support_backup_map_supported: bool
    is_support_custom_mode_in_cleaning_supported: bool
    is_support_remote_control_in_call_supported: bool

    # Features derived from unhexed_feature_info
    is_support_set_volume_in_call: bool
    is_support_clean_estimate: bool
    is_support_custom_dnd: bool
    is_carpet_deep_clean_supported: bool
    is_support_stuck_zone: bool
    is_support_custom_door_sill: bool
    is_wifi_manage_supported: bool
    is_clean_route_fast_mode_supported: bool
    is_support_cliff_zone: bool
    is_support_smart_door_sill: bool
    is_support_floor_direction: bool
    is_back_charge_auto_wash_supported: bool
    is_super_deep_wash_supported: bool
    is_ces2022_supported: bool
    is_dss_believable_supported: bool
    is_main_brush_up_down_supported: bool
    is_goto_pure_clean_path_supported: bool
    is_water_up_down_drain_supported: bool
    is_setting_carpet_first_supported: bool
    is_clean_route_deep_slow_plus_supported: bool
    is_left_water_drain_supported: bool
    is_clean_count_setting_supported: bool
    is_corner_clean_mode_supported: bool

    # --- Features from new_feature_info_str ---
    is_two_key_real_time_video_supported: bool
    is_two_key_rtv_in_charging_supported: bool
    is_dirty_replenish_clean_supported: bool
    is_avoid_collision_mode_str_supported: bool
    is_voice_control_str_supported: bool
    is_new_endpoint_supported: bool
    is_corner_mop_strech_supported: bool
    is_hot_wash_towel_supported: bool
    is_floor_dir_clean_any_time_supported: bool
    is_pet_supplies_deep_clean_supported: bool
    is_mop_shake_water_max_supported: bool
    is_custom_clean_mode_count_supported: bool
    is_exact_custom_mode_supported: bool
    is_carpet_custom_clean_supported: bool
    is_pet_snapshot_supported: bool
    is_new_ai_recognition_supported: bool
    is_auto_collection_2_supported: bool
    is_right_brush_stretch_supported: bool
    is_smart_clean_mode_set_supported: bool
    is_dirty_object_detect_supported: bool
    is_no_need_carpet_press_set_supported: bool
    is_voice_control_led_supported: bool
    is_water_leak_check_supported: bool
    is_min_battery_15_to_clean_task_supported: bool
    is_gap_deep_clean_supported: bool
    is_object_detect_check_supported: bool
    is_identify_room_supported: bool
    is_matter_supported: bool

    @classmethod
    def _is_new_feature_str_support(cls, o: int, new_feature_info_str: str) -> bool:
        """
        Checks feature 'o' in hex string 'new_feature_info_str'.
        """
        try:
            l = o % 4
            target_index = -((o // 4) + 1)

            p = new_feature_info_str[target_index]

            hex_char_value = int(p, 16)

            is_set = (hex_char_value >> l) & 1

            return bool(is_set)
        except Exception:
            return False

    @classmethod
    def from_feature_flags(
        cls, robot_new_features: int, new_feature_set: str, product_nickname: RoborockProductNickname
    ) -> DeviceFeatures:
        """Creates a DeviceFeatures instance from raw feature flags."""
        unhexed_feature_info = int(new_feature_set[-8:], 16)

        upper_32_bits = robot_new_features // (2**32)

        return cls(
            is_map_carpet_add_support=bool(1073741824 & robot_new_features),
            is_show_clean_finish_reason_supported=bool(1 & robot_new_features),
            is_resegment_supported=bool(4 & robot_new_features),
            is_video_monitor_supported=bool(8 & robot_new_features),
            is_any_state_transit_goto_supported=bool(16 & robot_new_features),
            is_fw_filter_obstacle_supported=bool(32 & robot_new_features),
            is_video_settings_supported=bool(64 & robot_new_features),
            is_ignore_unknown_map_object_supported=bool(128 & robot_new_features),
            is_set_child_supported=bool(256 & robot_new_features),
            is_carpet_supported=bool(512 & robot_new_features),
            is_mop_path_supported=bool(2048 & robot_new_features),
            is_multi_map_segment_timer_supported=False,  # TODO
            is_custom_water_box_distance_supported=bool(2147483648 & robot_new_features),
            is_wash_then_charge_cmd_supported=bool(robot_new_features and ((upper_32_bits >> 5) & 1)),
            is_room_name_supported=bool(16384 & robot_new_features),
            is_current_map_restore_enabled=bool(8192 & robot_new_features),
            is_photo_upload_supported=bool(65536 & robot_new_features),
            is_shake_mop_set_supported=bool(262144 & robot_new_features),
            is_map_beautify_internal_debug_supported=bool(2097152 & robot_new_features),
            is_new_data_for_clean_history_supported=bool(4194304 & robot_new_features),
            is_new_data_for_clean_history_detail_supported=bool(8388608 & robot_new_features),
            is_flow_led_setting_supported=bool(16777216 & robot_new_features),
            is_dust_collection_setting_supported=bool(33554432 & robot_new_features),
            is_rpc_retry_supported=bool(67108864 & robot_new_features),
            is_avoid_collision_supported=bool(134217728 & robot_new_features),
            is_support_set_switch_map_mode_supported=bool(268435456 & robot_new_features),
            is_support_smart_scene_supported=bool(robot_new_features and (upper_32_bits & 2)),
            is_support_floor_edit_supported=bool(robot_new_features and (upper_32_bits & 8)),
            is_support_furniture_supported=bool(robot_new_features and ((upper_32_bits >> 4) & 1)),
            is_support_room_tag_supported=bool(robot_new_features and ((upper_32_bits >> 6) & 1)),
            is_support_quick_map_builder_supported=bool(robot_new_features and ((upper_32_bits >> 7) & 1)),
            is_support_smart_global_clean_with_custom_mode_supported=bool(
                robot_new_features and ((upper_32_bits >> 8) & 1)
            ),
            is_record_allowed=bool(1024 & robot_new_features),
            is_careful_slow_mop_supported=bool(robot_new_features and ((upper_32_bits >> 9) & 1)),
            is_egg_mode_supported=bool(robot_new_features and ((upper_32_bits >> 10) & 1)),
            is_carpet_show_on_map_supported=bool(robot_new_features and ((upper_32_bits >> 12) & 1)),
            is_supported_valley_electricity_supported=bool(robot_new_features and ((upper_32_bits >> 13) & 1)),
            is_unsave_map_reason_supported=bool(robot_new_features and ((upper_32_bits >> 14) & 1)),
            is_supported_drying_supported=False,  # TODO
            is_supported_download_test_voice_supported=bool(robot_new_features and ((upper_32_bits >> 16) & 1)),
            is_support_backup_map_supported=bool(robot_new_features and ((upper_32_bits >> 17) & 1)),
            is_support_custom_mode_in_cleaning_supported=bool(robot_new_features and ((upper_32_bits >> 18) & 1)),
            is_support_remote_control_in_call_supported=bool(robot_new_features and ((upper_32_bits >> 19) & 1)),
            # Features from unhexed_feature_info
            is_support_set_volume_in_call=bool(1 & unhexed_feature_info),
            is_support_clean_estimate=bool(2 & unhexed_feature_info),
            is_support_custom_dnd=bool(4 & unhexed_feature_info),
            is_carpet_deep_clean_supported=bool(8 & unhexed_feature_info),
            is_support_stuck_zone=bool(16 & unhexed_feature_info),
            is_support_custom_door_sill=bool(32 & unhexed_feature_info),
            is_wifi_manage_supported=bool(128 & unhexed_feature_info),
            is_clean_route_fast_mode_supported=bool(256 & unhexed_feature_info),
            is_support_cliff_zone=bool(512 & unhexed_feature_info),
            is_support_smart_door_sill=bool(1024 & unhexed_feature_info),
            is_support_floor_direction=bool(2048 & unhexed_feature_info),
            is_back_charge_auto_wash_supported=bool(4096 & unhexed_feature_info),
            is_super_deep_wash_supported=bool(32768 & unhexed_feature_info),
            is_ces2022_supported=bool(65536 & unhexed_feature_info),
            is_dss_believable_supported=bool(131072 & unhexed_feature_info),
            is_main_brush_up_down_supported=bool(262144 & unhexed_feature_info),
            is_goto_pure_clean_path_supported=bool(524288 & unhexed_feature_info),
            is_water_up_down_drain_supported=bool(1048576 & unhexed_feature_info),
            is_setting_carpet_first_supported=bool(8388608 & unhexed_feature_info),
            is_clean_route_deep_slow_plus_supported=bool(16777216 & unhexed_feature_info),
            is_left_water_drain_supported=bool(134217728 & unhexed_feature_info),
            is_clean_count_setting_supported=bool(1073741824 & unhexed_feature_info),
            is_corner_clean_mode_supported=bool(2147483648 & unhexed_feature_info),
            # Features from is_new_feature_str_support
            is_two_key_real_time_video_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.TWO_KEY_REAL_TIME_VIDEO, new_feature_set
            ),
            is_two_key_rtv_in_charging_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.TWO_KEY_RTV_IN_CHARGING, new_feature_set
            ),
            is_dirty_replenish_clean_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.DIRTY_REPLENISH_CLEAN, new_feature_set
            ),
            is_avoid_collision_mode_str_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.AVOID_COLLISION_MODE, new_feature_set
            ),
            is_voice_control_str_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.VOICE_CONTROL, new_feature_set
            ),
            is_new_endpoint_supported=cls._is_new_feature_str_support(NewFeatureStrBit.NEW_ENDPOINT, new_feature_set),
            is_corner_mop_strech_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.CORNER_MOP_STRECH, new_feature_set
            ),
            is_hot_wash_towel_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.HOT_WASH_TOWEL, new_feature_set
            ),
            is_floor_dir_clean_any_time_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.FLOOR_DIR_CLEAN_ANY_TIME, new_feature_set
            ),
            is_pet_supplies_deep_clean_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.PET_SUPPLIES_DEEP_CLEAN, new_feature_set
            ),
            is_mop_shake_water_max_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.MOP_SHAKE_WATER_MAX, new_feature_set
            ),
            is_custom_clean_mode_count_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.CUSTOM_CLEAN_MODE_COUNT, new_feature_set
            ),
            is_exact_custom_mode_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.EXACT_CUSTOM_MODE, new_feature_set
            ),
            is_carpet_custom_clean_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.CARPET_CUSTOM_CLEAN, new_feature_set
            ),
            is_pet_snapshot_supported=cls._is_new_feature_str_support(NewFeatureStrBit.PET_SNAPSHOT, new_feature_set),
            is_new_ai_recognition_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.NEW_AI_RECOGNITION, new_feature_set
            ),
            is_auto_collection_2_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.AUTO_COLLECTION_2, new_feature_set
            ),
            is_right_brush_stretch_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.RIGHT_BRUSH_STRETCH, new_feature_set
            ),
            is_smart_clean_mode_set_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.SMART_CLEAN_MODE_SET, new_feature_set
            ),
            is_dirty_object_detect_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.DIRTY_OBJECT_DETECT, new_feature_set
            ),
            is_no_need_carpet_press_set_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.NO_NEED_CARPET_PRESS_SET, new_feature_set
            ),
            is_voice_control_led_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.VOICE_CONTROL_LED, new_feature_set
            ),
            is_water_leak_check_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.WATER_LEAK_CHECK, new_feature_set
            ),
            is_min_battery_15_to_clean_task_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.MIN_BATTERY_15_TO_CLEAN_TASK, new_feature_set
            ),
            is_gap_deep_clean_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.GAP_DEEP_CLEAN, new_feature_set
            ),
            is_object_detect_check_supported=cls._is_new_feature_str_support(
                NewFeatureStrBit.OBJECT_DETECT_CHECK, new_feature_set
            ),
            is_identify_room_supported=cls._is_new_feature_str_support(NewFeatureStrBit.IDENTIFY_ROOM, new_feature_set),
            is_matter_supported=cls._is_new_feature_str_support(NewFeatureStrBit.MATTER, new_feature_set),
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
    ROBOROCK_QREVO_MAXV: P10Status,
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
    product_nickname: RoborockProductNickname | None = None
    device_features: DeviceFeatures | None = None

    def __post_init__(self):
        self.product_nickname = short_model_to_enum.get(self.model.split(".")[-1], RoborockProductNickname.PEARLPLUS)
        robot_new_features = int(self.device.feature_set) if self.device.feature_set else 0
        self.device_features = DeviceFeatures.from_feature_flags(
            robot_new_features,
            self.device.new_feature_set if self.device.new_feature_set is not None else "00000000",
            self.product_nickname,
        )

    @property
    def duid(self) -> str:
        """Get the duid of the device."""
        return self.device.duid


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

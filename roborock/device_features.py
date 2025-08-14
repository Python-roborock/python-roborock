from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import IntEnum, StrEnum
from typing import Any

from .code_mappings import RoborockProductNickname


class NewFeatureStrBit(IntEnum):
    TWO_KEY_REAL_TIME_VIDEO = 32
    TWO_KEY_RTV_IN_CHARGING = 33
    DIRTY_REPLENISH_CLEAN = 34
    AUTO_DELIVERY_FIELD_IN_GLOBAL_STATUS = 35
    AVOID_COLLISION_MODE = 36
    VOICE_CONTROL = 37
    NEW_ENDPOINT = 38
    PUMPING_WATER = 39
    CORNER_MOP_STRETCH = 40
    HOT_WASH_TOWEL = 41
    FLOOR_DIR_CLEAN_ANY_TIME = 42
    PET_SUPPLIES_DEEP_CLEAN = 43
    MOP_SHAKE_WATER_MAX = 45
    EXACT_CUSTOM_MODE = 47
    VIDEO_PATROL = 48
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
    SMALL_SIDE_MOP = 81
    SUPPORT_SIDE_BRUSH_UP_DOWN = 82
    DRY_INTERVAL_TIMER = 83
    UVC_STERILIZE = 84
    MIDWAY_BACK_TO_DOCK = 85
    SUPPORT_MAIN_BRUSH_UP_DOWN = 86
    EGG_DANCE_MODE = 87


class ProductFeatures(StrEnum):
    REMOTE_BACK = "remote_back"
    CLEANMODE_MAXPLUS = "cleanmode_maxplus"
    CLEANMODE_PURECLEANMOP = "cleanmode_purecleanmop"
    CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS = "cleanmode_none_purecleanmop_with_maxplus"
    MOP_ELECTRONIC_MODULE = "mop_electronic_module"
    MOP_SHAKE_MODULE = "mop_shake_module"
    MOP_SPIN_MODULE = "mop_spin_module"
    DEFAULT_MAP3D = "map3d"
    DEFAULT_CLEANMODECUSTOM = "custom_cleanmode"
    REALTIMEVIDEO = "realtimevideo"
    REALTIMEVIDEO_LIVECALL = "realtimevideo_livecall"
    REALTIMEVIDEO_RECORDANDSHORTCUT = "realtimevideo_livecall"
    CAMERA_SINGLELINE = "camera_singleline"
    CAMERA_DUALLINE = "camera_dualline"
    CAMERA_RGB = "camera_rgb"
    CAMERA_DOUBLERGB = "camera_doublergb"
    AIRECOGNITION_SETTING = "airecognition_setting"
    AIRECOGNITION_SCENE = "airecognition_scene"
    AIRECOGNITION_PET = "airecognition_pet"
    AIRECOGNITION_OBSTACLE = "airecognition_obstacle"


# The following combinations are pulled directly from decompiled source code.
AIRECOGNITION_OBSTACLE = [ProductFeatures.AIRECOGNITION_OBSTACLE]
RGB_CAMERA_FEATURES = [
    ProductFeatures.CAMERA_RGB,
    ProductFeatures.AIRECOGNITION_SETTING,
    ProductFeatures.AIRECOGNITION_SCENE,
    ProductFeatures.AIRECOGNITION_PET,
    ProductFeatures.AIRECOGNITION_OBSTACLE,
    ProductFeatures.REALTIMEVIDEO,
    ProductFeatures.REALTIMEVIDEO_LIVECALL,
    ProductFeatures.REALTIMEVIDEO_RECORDANDSHORTCUT,
]
DOUBLE_RGB_CAMERA_FEATURES = [
    ProductFeatures.CAMERA_DOUBLERGB,
    ProductFeatures.AIRECOGNITION_SETTING,
    ProductFeatures.AIRECOGNITION_PET,
    ProductFeatures.AIRECOGNITION_OBSTACLE,
    ProductFeatures.REALTIMEVIDEO,
]
SINGLE_LINE_CAMERA_FEATURES = [
    ProductFeatures.CAMERA_SINGLELINE,
    ProductFeatures.AIRECOGNITION_SETTING,
    ProductFeatures.AIRECOGNITION_OBSTACLE,
]
DUAL_LINE_CAMERA_FEATURES = [
    ProductFeatures.CAMERA_DUALLINE,
    ProductFeatures.AIRECOGNITION_SETTING,
    ProductFeatures.AIRECOGNITION_OBSTACLE,
    ProductFeatures.AIRECOGNITION_PET,
]

NEW_DEFAULT_FEATURES = [ProductFeatures.REMOTE_BACK, ProductFeatures.CLEANMODE_MAXPLUS]


PEARL_FEATURES = NEW_DEFAULT_FEATURES + SINGLE_LINE_CAMERA_FEATURES + [ProductFeatures.MOP_SPIN_MODULE]
PEARL_PLUS_FEATURES = NEW_DEFAULT_FEATURES + RGB_CAMERA_FEATURES + [ProductFeatures.MOP_SPIN_MODULE]
ULTRON_FEATURES = NEW_DEFAULT_FEATURES + DUAL_LINE_CAMERA_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE]
ULTRONSV_FEATURES = NEW_DEFAULT_FEATURES + RGB_CAMERA_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE]
TANOSS_FEATURES = NEW_DEFAULT_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE]
TOPAZSPOWER_FEATURES = NEW_DEFAULT_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE]

product_feature_map = {
    RoborockProductNickname.PEARL: PEARL_FEATURES,
    RoborockProductNickname.PEARLS: PEARL_FEATURES,
    RoborockProductNickname.PEARLPLUS: PEARL_PLUS_FEATURES,
    RoborockProductNickname.VIVIAN: PEARL_PLUS_FEATURES,
    RoborockProductNickname.CORAL: PEARL_PLUS_FEATURES,
    RoborockProductNickname.ULTRON: ULTRON_FEATURES,
    RoborockProductNickname.ULTRONE: [ProductFeatures.CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS],
    RoborockProductNickname.ULTRONSV: ULTRONSV_FEATURES,
    RoborockProductNickname.TOPAZSPOWER: TOPAZSPOWER_FEATURES,
    RoborockProductNickname.TANOSS: TANOSS_FEATURES,
    RoborockProductNickname.PEARLC: PEARL_FEATURES,
    RoborockProductNickname.PEARLPLUSS: PEARL_PLUS_FEATURES,
    RoborockProductNickname.PEARLSLITE: PEARL_FEATURES,
    RoborockProductNickname.PEARLE: PEARL_FEATURES,
    RoborockProductNickname.PEARLELITE: PEARL_FEATURES,
    RoborockProductNickname.VIVIANC: PEARL_PLUS_FEATURES,
    RoborockProductNickname.CORALPRO: PEARL_PLUS_FEATURES,
    RoborockProductNickname.ULTRONLITE: SINGLE_LINE_CAMERA_FEATURES
    + [ProductFeatures.CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS, ProductFeatures.MOP_ELECTRONIC_MODULE],
    RoborockProductNickname.ULTRONSC: ULTRON_FEATURES,
    RoborockProductNickname.ULTRONSE: [
        ProductFeatures.CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS,
        ProductFeatures.MOP_ELECTRONIC_MODULE,
    ],
    RoborockProductNickname.ULTRONSPLUS: ULTRON_FEATURES,
    RoborockProductNickname.VERDELITE: ULTRONSV_FEATURES,
    RoborockProductNickname.TOPAZS: NEW_DEFAULT_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE],
    RoborockProductNickname.TOPAZSPLUS: NEW_DEFAULT_FEATURES
    + DUAL_LINE_CAMERA_FEATURES
    + [ProductFeatures.MOP_SHAKE_MODULE],
    RoborockProductNickname.TOPAZSC: TOPAZSPOWER_FEATURES + SINGLE_LINE_CAMERA_FEATURES,
    RoborockProductNickname.TOPAZSV: NEW_DEFAULT_FEATURES + RGB_CAMERA_FEATURES + [ProductFeatures.MOP_SHAKE_MODULE],
    RoborockProductNickname.TANOSSPLUS: TANOSS_FEATURES + DUAL_LINE_CAMERA_FEATURES,
    RoborockProductNickname.TANOSSLITE: [ProductFeatures.MOP_ELECTRONIC_MODULE],
    RoborockProductNickname.TANOSSC: [],
    RoborockProductNickname.TANOSSE: [],
    RoborockProductNickname.TANOSSMAX: NEW_DEFAULT_FEATURES
    + DUAL_LINE_CAMERA_FEATURES
    + [ProductFeatures.MOP_SHAKE_MODULE],
    RoborockProductNickname.TANOS: [ProductFeatures.REMOTE_BACK],
    RoborockProductNickname.TANOSE: [ProductFeatures.MOP_ELECTRONIC_MODULE, ProductFeatures.REMOTE_BACK],
    RoborockProductNickname.TANOSV: DOUBLE_RGB_CAMERA_FEATURES
    + [ProductFeatures.REMOTE_BACK, ProductFeatures.MOP_ELECTRONIC_MODULE],
    RoborockProductNickname.RUBYPLUS: [],
    RoborockProductNickname.RUBYSC: [],
    RoborockProductNickname.RUBYSE: [],
    RoborockProductNickname.RUBYSLITE: [ProductFeatures.MOP_ELECTRONIC_MODULE],
}


@dataclass
class DeviceFeatures:
    """Represents the features supported by a Roborock device."""

    # Features from robot_new_features (lower 32 bits)
    is_show_clean_finish_reason_supported: bool = field(metadata={"robot_new_features": 1})
    is_re_segment_supported: bool = field(metadata={"robot_new_features": 4})
    is_video_monitor_supported: bool = field(metadata={"robot_new_features": 8})
    is_any_state_transit_goto_supported: bool = field(metadata={"robot_new_features": 16})
    is_fw_filter_obstacle_supported: bool = field(metadata={"robot_new_features": 32})
    is_video_setting_supported: bool = field(metadata={"robot_new_features": 64})
    is_ignore_unknown_map_object_supported: bool = field(metadata={"robot_new_features": 128})
    is_set_child_supported: bool = field(metadata={"robot_new_features": 256})
    is_carpet_supported: bool = field(metadata={"robot_new_features": 512})
    is_record_allowed: bool = field(metadata={"robot_new_features": 1024})
    is_mop_path_supported: bool = field(metadata={"robot_new_features": 2048})
    is_multi_map_segment_timer_supported: bool = field(metadata={"robot_new_features": 4096})
    is_current_map_restore_enabled: bool = field(metadata={"robot_new_features": 8192})
    is_room_name_supported: bool = field(metadata={"robot_new_features": 16384})
    is_shake_mop_set_supported: bool = field(metadata={"robot_new_features": 262144})
    is_map_beautify_internal_debug_supported: bool = field(metadata={"robot_new_features": 2097152})
    is_new_data_for_clean_history: bool = field(metadata={"robot_new_features": 4194304})
    is_new_data_for_clean_history_detail: bool = field(metadata={"robot_new_features": 8388608})
    is_flow_led_setting_supported: bool = field(metadata={"robot_new_features": 16777216})
    is_dust_collection_setting_supported: bool = field(metadata={"robot_new_features": 33554432})
    is_rpc_retry_supported: bool = field(metadata={"robot_new_features": 67108864})
    is_avoid_collision_supported: bool = field(metadata={"robot_new_features": 134217728})
    is_support_set_switch_map_mode: bool = field(metadata={"robot_new_features": 268435456})
    is_map_carpet_add_support: bool = field(metadata={"robot_new_features": 1073741824})
    is_custom_water_box_distance_supported: bool = field(metadata={"robot_new_features": 2147483648})

    # Features from robot_new_features (upper 32 bits)
    is_support_smart_scene: bool = field(metadata={"upper_32_bits": 1})
    is_support_floor_edit: bool = field(metadata={"upper_32_bits": 3})
    is_support_furniture: bool = field(metadata={"upper_32_bits": 4})
    is_wash_then_charge_cmd_supported: bool = field(metadata={"upper_32_bits": 5})
    is_support_room_tag: bool = field(metadata={"upper_32_bits": 6})
    is_support_quick_map_builder: bool = field(metadata={"upper_32_bits": 7})
    is_support_smart_global_clean_with_custom_mode: bool = field(metadata={"upper_32_bits": 8})
    is_careful_slow_mop_supported: bool = field(metadata={"upper_32_bits": 9})
    is_egg_mode_supported_from_new_features: bool = field(metadata={"upper_32_bits": 10})
    is_carpet_show_on_map: bool = field(metadata={"upper_32_bits": 12})
    is_supported_valley_electricity: bool = field(metadata={"upper_32_bits": 13})
    is_unsave_map_reason_supported: bool = field(metadata={"upper_32_bits": 14})
    is_supported_drying: bool = field(metadata={"upper_32_bits": 15})
    is_supported_download_test_voice: bool = field(metadata={"upper_32_bits": 16})
    is_support_backup_map: bool = field(metadata={"upper_32_bits": 17})
    is_support_custom_mode_in_cleaning: bool = field(metadata={"upper_32_bits": 18})
    is_support_remote_control_in_call: bool = field(metadata={"upper_32_bits": 19})

    # Features from new_feature_info_str (masking last 8 chars / 32 bits)
    is_support_set_volume_in_call: bool = field(metadata={"new_feature_str_mask": (1, 8)})
    is_support_clean_estimate: bool = field(metadata={"new_feature_str_mask": (2, 8)})
    is_support_custom_dnd: bool = field(metadata={"new_feature_str_mask": (4, 8)})
    is_carpet_deep_clean_supported: bool = field(metadata={"new_feature_str_mask": (8, 8)})
    is_support_stuck_zone: bool = field(metadata={"new_feature_str_mask": (16, 8)})
    is_support_custom_door_sill: bool = field(metadata={"new_feature_str_mask": (32, 8)})
    is_wifi_manage_supported: bool = field(metadata={"new_feature_str_mask": (128, 8)})
    is_clean_route_fast_mode_supported: bool = field(metadata={"new_feature_str_mask": (256, 8)})
    is_support_cliff_zone: bool = field(metadata={"new_feature_str_mask": (512, 8)})
    is_support_smart_door_sill: bool = field(metadata={"new_feature_str_mask": (1024, 8)})
    is_support_floor_direction: bool = field(metadata={"new_feature_str_mask": (2048, 8)})
    is_back_charge_auto_wash_supported: bool = field(metadata={"new_feature_str_mask": (4096, 8)})
    is_support_incremental_map: bool = field(metadata={"new_feature_str_mask": (4194304, 8)})
    is_offline_map_supported: bool = field(metadata={"new_feature_str_mask": (16384, 8)})
    is_super_deep_wash_supported: bool = field(metadata={"new_feature_str_mask": (32768, 8)})
    is_ces2022_supported: bool = field(metadata={"new_feature_str_mask": (65536, 8)})
    is_dss_believable: bool = field(metadata={"new_feature_str_mask": (131072, 8)})
    is_main_brush_up_down_supported_from_str: bool = field(metadata={"new_feature_str_mask": (262144, 8)})
    is_goto_pure_clean_path_supported: bool = field(metadata={"new_feature_str_mask": (524288, 8)})
    is_water_up_down_drain_supported: bool = field(metadata={"new_feature_str_mask": (1048576, 8)})
    is_setting_carpet_first_supported: bool = field(metadata={"new_feature_str_mask": (8388608, 8)})
    is_clean_route_deep_slow_plus_supported: bool = field(metadata={"new_feature_str_mask": (16777216, 8)})
    is_dynamically_skip_clean_zone_supported: bool = field(metadata={"new_feature_str_mask": (33554432, 8)})
    is_dynamically_add_clean_zones_supported: bool = field(metadata={"new_feature_str_mask": (67108864, 8)})
    is_left_water_drain_supported: bool = field(metadata={"new_feature_str_mask": (134217728, 8)})
    is_clean_count_setting_supported: bool = field(metadata={"new_feature_str_mask": (1073741824, 8)})
    is_corner_clean_mode_supported: bool = field(metadata={"new_feature_str_mask": (2147483648, 8)})

    # Features from new_feature_info_str (by bit index)
    is_two_key_real_time_video_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.TWO_KEY_REAL_TIME_VIDEO}
    )
    is_two_key_rtv_in_charging_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.TWO_KEY_RTV_IN_CHARGING}
    )
    is_dirty_replenish_clean_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.DIRTY_REPLENISH_CLEAN}
    )
    is_auto_delivery_field_in_global_status_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.AUTO_DELIVERY_FIELD_IN_GLOBAL_STATUS}
    )
    is_avoid_collision_mode_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.AVOID_COLLISION_MODE}
    )
    is_voice_control_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.VOICE_CONTROL})
    is_new_endpoint_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.NEW_ENDPOINT})
    is_pumping_water_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.PUMPING_WATER})
    is_corner_mop_stretch_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.CORNER_MOP_STRETCH})
    is_hot_wash_towel_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.HOT_WASH_TOWEL})
    is_floor_dir_clean_any_time_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.FLOOR_DIR_CLEAN_ANY_TIME}
    )
    is_pet_supplies_deep_clean_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.PET_SUPPLIES_DEEP_CLEAN}
    )
    is_mop_shake_water_max_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.MOP_SHAKE_WATER_MAX}
    )
    is_exact_custom_mode_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.EXACT_CUSTOM_MODE})
    is_video_patrol_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.VIDEO_PATROL})
    is_carpet_custom_clean_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.CARPET_CUSTOM_CLEAN}
    )
    is_pet_snapshot_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.PET_SNAPSHOT})
    is_custom_clean_mode_count_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.CUSTOM_CLEAN_MODE_COUNT}
    )
    is_new_ai_recognition_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.NEW_AI_RECOGNITION})
    is_auto_collection_2_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.AUTO_COLLECTION_2})
    is_right_brush_stretch_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.RIGHT_BRUSH_STRETCH}
    )
    is_smart_clean_mode_set_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.SMART_CLEAN_MODE_SET}
    )
    is_dirty_object_detect_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.DIRTY_OBJECT_DETECT}
    )
    is_no_need_carpet_press_set_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.NO_NEED_CARPET_PRESS_SET}
    )
    is_voice_control_led_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.VOICE_CONTROL_LED})
    is_water_leak_check_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.WATER_LEAK_CHECK})
    is_min_battery_15_to_clean_task_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.MIN_BATTERY_15_TO_CLEAN_TASK}
    )
    is_gap_deep_clean_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.GAP_DEEP_CLEAN})
    is_object_detect_check_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.OBJECT_DETECT_CHECK}
    )
    is_identify_room_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.IDENTIFY_ROOM})
    is_matter_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.MATTER})
    is_workday_holiday_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.WORKDAY_HOLIDAY})
    is_clean_direct_status_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.CLEAN_DIRECT_STATUS}
    )
    is_map_eraser_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.MAP_ERASER})
    is_optimize_battery_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.OPTIMIZE_BATTERY})
    is_activate_video_charging_and_standby_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.ACTIVATE_VIDEO_CHARGING_AND_STANDBY}
    )
    is_carpet_long_haired_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.CARPET_LONG_HAIRED})
    is_clean_history_time_line_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.CLEAN_HISTORY_TIME_LINE}
    )
    is_max_zone_opened_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.MAX_ZONE_OPENED})
    is_exhibition_function_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.EXHIBITION_FUNCTION}
    )
    is_lds_lifting_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.LDS_LIFTING})
    is_auto_tear_down_mop_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.AUTO_TEAR_DOWN_MOP})
    is_small_side_mop_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.SMALL_SIDE_MOP})
    is_support_side_brush_up_down_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.SUPPORT_SIDE_BRUSH_UP_DOWN}
    )
    is_dry_interval_timer_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.DRY_INTERVAL_TIMER})
    is_uvc_sterilize_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.UVC_STERILIZE})
    is_midway_back_to_dock_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.MIDWAY_BACK_TO_DOCK}
    )
    is_support_main_brush_up_down_supported: bool = field(
        metadata={"new_feature_str_bit": NewFeatureStrBit.SUPPORT_MAIN_BRUSH_UP_DOWN}
    )
    is_egg_dance_mode_supported: bool = field(metadata={"new_feature_str_bit": NewFeatureStrBit.EGG_DANCE_MODE})

    # Features from feature_info list
    is_led_status_switch_supported: bool = field(metadata={"robot_features": 119})
    is_multi_floor_supported: bool = field(metadata={"robot_features": 120})
    is_support_fetch_timer_summary: bool = field(metadata={"robot_features": 122})
    is_order_clean_supported: bool = field(metadata={"robot_features": 123})
    is_analysis_supported: bool = field(metadata={"robot_features": 124})
    is_remote_supported: bool = field(metadata={"robot_features": 125})
    is_support_voice_control_debug: bool = field(metadata={"robot_features": 130})

    # Features from model whitelists/blacklists or other flags
    is_mop_forbidden_supported: bool = field(
        metadata={
            "model_whitelist": [
                RoborockProductNickname.TANOSV,
                RoborockProductNickname.TOPAZSV,
                RoborockProductNickname.TANOS,
                RoborockProductNickname.TANOSE,
                RoborockProductNickname.TANOSSLITE,
                RoborockProductNickname.TANOSS,
                RoborockProductNickname.TANOSSPLUS,
                RoborockProductNickname.TANOSSMAX,
                RoborockProductNickname.ULTRON,
                RoborockProductNickname.ULTRONLITE,
                RoborockProductNickname.PEARL,
                RoborockProductNickname.RUBYSLITE,
            ]
        }
    )
    is_soft_clean_mode_supported: bool = field(
        metadata={
            "model_whitelist": [
                RoborockProductNickname.TANOSV,
                RoborockProductNickname.TANOSE,
                RoborockProductNickname.TANOS,
            ]
        }
    )
    is_custom_mode_supported: bool = field(metadata={"model_blacklist": [RoborockProductNickname.TANOS]})
    is_support_custom_carpet: bool = field(metadata={"model_whitelist": [RoborockProductNickname.ULTRONLITE]})
    is_show_general_obstacle_supported: bool = field(metadata={"model_whitelist": [RoborockProductNickname.TANOSSPLUS]})
    is_show_obstacle_photo_supported: bool = field(
        metadata={
            "model_whitelist": [
                RoborockProductNickname.TANOSSPLUS,
                RoborockProductNickname.TANOSSMAX,
                RoborockProductNickname.ULTRON,
            ]
        }
    )
    is_rubber_brush_carpet_supported: bool = field(metadata={"model_whitelist": [RoborockProductNickname.ULTRONLITE]})
    is_carpet_pressure_use_origin_paras_supported: bool = field(
        metadata={"model_whitelist": [RoborockProductNickname.ULTRONLITE]}
    )
    is_support_mop_back_pwm_set: bool = field(metadata={"model_whitelist": [RoborockProductNickname.PEARL]})
    is_collect_dust_mode_supported: bool = field(metadata={"model_blacklist": [RoborockProductNickname.PEARL]})
    is_support_water_mode: bool = field(
        metadata={
            "product_features": [
                ProductFeatures.MOP_ELECTRONIC_MODULE,
                ProductFeatures.MOP_SHAKE_MODULE,
                ProductFeatures.MOP_SPIN_MODULE,
            ]
        }
    )
    is_pure_clean_mop_supported: bool = field(metadata={"product_features": [ProductFeatures.CLEANMODE_PURECLEANMOP]})
    is_new_remote_view_supported: bool = field(metadata={"product_features": [ProductFeatures.REMOTE_BACK]})
    is_max_plus_mode_supported: bool = field(metadata={"product_features": [ProductFeatures.CLEANMODE_MAXPLUS]})
    is_none_pure_clean_mop_with_max_plus: bool = field(
        metadata={"product_features": [ProductFeatures.CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS]}
    )
    is_clean_route_setting_supported: bool = field(
        metadata={"product_features": [ProductFeatures.MOP_SHAKE_MODULE, ProductFeatures.MOP_SPIN_MODULE]}
    )
    is_mop_shake_module_supported: bool = field(metadata={"product_features": [ProductFeatures.MOP_SHAKE_MODULE]})

    @classmethod
    def from_feature_flags(
        cls,
        new_feature_info: int,
        new_feature_info_str: str,
        feature_info: list[int],
        product_nickname: RoborockProductNickname | None,
    ) -> DeviceFeatures:
        """Creates a DeviceFeatures instance from raw feature flags.
        :param new_feature_info: A int from get_init_status (sometimes can be found in homedata, but it is not always)
        :param new_feature_info_str: A hex string from get_init_status or home_data.
        :param feature_info: A list of ints from get_init_status
        :param product_nickname: The product nickname of the device."""
        # For any future reverse engineerining:
        # RobotNewFeatures = new_feature_info
        # newFeatureInfoStr = new_feature_info_str
        # feature_info =robotFeatures
        kwargs: dict[str, Any] = {}

        for f in fields(cls):
            # Default all features to False.
            kwargs[f.name] = False
            if not f.metadata:
                continue

            if (mask := f.metadata.get("robot_new_features")) is not None:
                kwargs[f.name] = bool(mask & new_feature_info)
            elif (bit_index := f.metadata.get("upper_32_bits")) is not None:
                # Check bits in the upper 32-bit integer of new_feature_info
                if new_feature_info:
                    kwargs[f.name] = bool(((new_feature_info >> 32) >> bit_index) & 1)
            elif (mask_info := f.metadata.get("new_feature_str_mask")) is not None:
                # Check bitmask against a slice of the hex string
                if new_feature_info_str:
                    try:
                        mask, slice_count = mask_info
                        if len(new_feature_info_str) >= slice_count:
                            last_chars = new_feature_info_str[-slice_count:]
                            value = int(last_chars, 16)
                            kwargs[f.name] = bool(mask & value)
                    except (ValueError, IndexError):
                        pass  # Keep it False
            elif (bit := f.metadata.get("new_feature_str_bit")) is not None:
                # Check a specific bit in the hex string using its index
                if new_feature_info_str:
                    try:
                        # Bit index defines which character and which bit inside it to check
                        char_index_from_end = 1 + bit.value // 4
                        if char_index_from_end <= len(new_feature_info_str):
                            char_hex = new_feature_info_str[-char_index_from_end]
                            nibble = int(char_hex, 16)
                            bit_in_nibble = bit.value % 4
                            kwargs[f.name] = bool((nibble >> bit_in_nibble) & 1)
                    except (ValueError, IndexError):
                        pass  # Keep it False
            elif (feature_id := f.metadata.get("robot_features")) is not None:
                kwargs[f.name] = feature_id in feature_info
            elif (whitelist := f.metadata.get("model_whitelist")) is not None:
                # If product_nickname is None, assume it is not in the whitelist
                kwargs[f.name] = product_nickname in whitelist or product_nickname is None
            elif (blacklist := f.metadata.get("model_blacklist")) is not None:
                # If product_nickname is None, assume it is not in the blacklist.
                if product_nickname is None:
                    kwargs[f.name] = True
                else:
                    kwargs[f.name] = product_nickname not in blacklist
            elif (product_features := f.metadata.get("product_features")) is not None:
                if product_nickname is not None:
                    available_features = product_feature_map.get(product_nickname, [])
                    if any(feat in available_features for feat in product_features):  # type: ignore
                        kwargs[f.name] = True

        return cls(**kwargs)

    def get_supported_features(self) -> list[str]:
        """Returns a list of supported features (Primarily used for logging purposes)."""
        return [k for k, v in vars(self).items() if v]

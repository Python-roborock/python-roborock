from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .containers import (
    CleanRecord,
    CleanSummary,
    Consumable,
    DustCollectionMode,
    RoborockBase,
    SmartWashParams,
    Status,
    WashTowelMode,
)


class RoborockCommand(str, Enum):
    ADD_MOP_TEMPLATE_PARAMS = "add_mop_template_params"
    APP_AMETHYST_SELF_CHECK = "app_amethyst_self_check"
    APP_CHARGE = "app_charge"
    APP_DELETE_WIFI = "app_delete_wifi"
    APP_GET_AMETHYST_STATUS = "app_get_amethyst_status"
    APP_GET_CARPET_DEEP_CLEAN_STATUS = "app_get_carpet_deep_clean_status"
    APP_GET_CLEAN_ESTIMATE_INFO = "app_get_clean_estimate_info"
    APP_GET_DRYER_SETTING = "app_get_dryer_setting"
    APP_GET_INIT_STATUS = "app_get_init_status"
    APP_GET_LOCALE = "app_get_locale"
    APP_GET_WIFI_LIST = "app_get_wifi_list"
    APP_GOTO_TARGET = "app_goto_target"
    APP_KEEP_EASTER_EGG = "app_keep_easter_egg"
    APP_PAUSE = "app_pause"
    APP_RC_END = "app_rc_end"
    APP_RC_MOVE = "app_rc_move"
    APP_RC_START = "app_rc_start"
    APP_RC_STOP = "app_rc_stop"
    APP_RESUME_BUILD_MAP = "app_resume_build_map"
    APP_RESUME_PATROL = "app_resume_patrol"
    APP_SEGMENT_CLEAN = "app_segment_clean"
    APP_SET_AMETHYST_STATUS = "app_set_amethyst_status"
    APP_SET_CARPET_DEEP_CLEAN_STATUS = "app_set_carpet_deep_clean_status"
    APP_SET_CROSS_CARPET_CLEANING_STATUS = "app_set_cross_carpet_cleaning_status"
    APP_SET_DOOR_SILL_BLOCKS = "app_set_door_sill_blocks"
    APP_SET_DIRTY_REPLENISH_CLEAN_STATUS = "app_set_dirty_replenish_clean_status"
    APP_SET_DRYER_SETTING = "app_set_dryer_setting"
    APP_SET_DRYER_STATUS = "app_set_dryer_status"
    APP_SET_DYNAMIC_CONFIG = "app_set_dynamic_config"
    APP_SET_IGNORE_STUCK_POINT = "app_set_ignore_stuck_point"
    APP_SET_SMART_CLIFF_FORBIDDEN = "app_set_smart_cliff_forbidden"
    APP_SET_SMART_DOOR_SILL = "app_set_smart_door_sill"
    APP_SPOT = "app_spot"
    APP_START = "app_start"
    APP_START_BUILD_MAP = "app_start_build_map"
    APP_START_COLLECT_DUST = "app_start_collect_dust"
    APP_START_EASTER_EGG = "app_start_easter_egg"
    APP_START_PATROL = "app_start_patrol"
    APP_START_PET_PATROL = "app_start_pet_patrol"
    APP_START_WASH = "app_start_wash"
    APP_STAT = "app_stat"
    APP_STOP = "app_stop"
    APP_STOP_COLLECT_DUST = "app_stop_collect_dust"
    APP_STOP_WASH = "app_stop_wash"
    APP_UPDATE_UNSAVE_MAP = "app_update_unsave_map"
    APP_WAKEUP_ROBOT = "app_wakeup_robot"
    APP_ZONED_CLEAN = "app_zoned_clean"
    CHANGE_SOUND_VOLUME = "change_sound_volume"
    CHECK_HOMESEC_PASSWORD = "check_homesec_password"
    CLOSE_DND_TIMER = "close_dnd_timer"
    CLOSE_VALLEY_ELECTRICITY_TIMER = "close_valley_electricity_timer"
    DEL_CLEAN_RECORD = "del_clean_record"
    DEL_CLEAN_RECORD_MAP_V2 = "del_clean_record_map_v2"
    DEL_MAP = "del_map"
    DEL_MOP_TEMPLATE_PARAMS = "del_mop_template_params"
    DEL_SERVER_TIMER = "del_server_timer"
    DEL_TIMER = "del_timer"
    DNLD_INSTALL_SOUND = "dnld_install_sound"
    ENABLE_HOMESEC_VOICE = "enable_homesec_voice"
    ENABLE_LOG_UPLOAD = "enable_log_upload"
    END_EDIT_MAP = "end_edit_map"
    FIND_ME = "find_me"
    GET_AUTO_DELIVERY_CLEANING_FLUID = "get_auto_delivery_cleaning_fluid"
    GET_CAMERA_STATUS = "get_camera_status"
    GET_CARPET_CLEAN_MODE = "get_carpet_clean_mode"
    GET_CARPET_MODE = "get_carpet_mode"
    GET_CHILD_LOCK_STATUS = "get_child_lock_status"
    GET_CLEAN_FOLLOW_GROUND_MATERIAL_STATUS = "get_clean_follow_ground_material_status"
    GET_CLEAN_MOTOR_MODE = "get_clean_motor_mode"
    GET_CLEAN_RECORD = "get_clean_record"
    GET_CLEAN_RECORD_MAP = "get_clean_record_map"
    GET_CLEAN_SEQUENCE = "get_clean_sequence"
    GET_CLEAN_SUMMARY = "get_clean_summary"
    GET_COLLISION_AVOID_STATUS = "get_collision_avoid_status"
    GET_CONSUMABLE = "get_consumable"
    GET_CURRENT_SOUND = "get_current_sound"
    GET_CUSTOM_MODE = "get_custom_mode"
    GET_CUSTOMIZE_CLEAN_MODE = "get_customize_clean_mode"
    GET_DEVICE_ICE = "get_device_ice"
    GET_DEVICE_SDP = "get_device_sdp"
    GET_DND_TIMER = "get_dnd_timer"
    GET_DOCK_INFO = "get_dock_info"
    GET_DUST_COLLECTION_MODE = "get_dust_collection_mode"
    GET_DUST_COLLECTION_SWITCH_STATUS = "get_dust_collection_switch_status"
    GET_DYNAMIC_DATA = "get_dynamic_data"
    GET_DYNAMIC_MAP_DIFF = "get_dynamic_map_diff"
    GET_FAN_MOTOR_WORK_TIMEOUT = "get_fan_motor_work_timeout"
    GET_FLOW_LED_STATUS = "get_flow_led_status"
    GET_FRESH_MAP = "get_fresh_map"
    GET_FW_FEATURES = "get_fw_features"
    GET_HOMESEC_CONNECT_STATUS = "get_homesec_connect_status"
    GET_IDENTIFY_FURNITURE_STATUS = "get_identify_furniture_status"
    GET_IDENTIFY_GROUND_MATERIAL_STATUS = "get_identify_ground_material_status"
    GET_LED_STATUS = "get_led_status"
    GET_LOG_UPLOAD_STATUS = "get_log_upload_status"
    GET_MAP = "get_map"
    GET_MAP_BEAUTIFICATION_STATUS = "get_map_beautification_status"
    GET_MAP_STATUS = "get_map_status"
    GET_MAP_V1 = "get_map_v1"
    GET_MAP_V2 = "get_map_v2"
    GET_MAP_CALIBRATION = "get_map_calibration"  # Custom command
    GET_MOP_MOTOR_STATUS = "get_mop_motor_status"
    GET_MOP_TEMPLATE_PARAMS_BY_ID = "get_mop_template_params_by_id"
    GET_MOP_TEMPLATE_PARAMS_SUMMARY = "get_mop_template_params_summary"
    GET_MULTI_MAP = "get_multi_map"
    GET_MULTI_MAPS_LIST = "get_multi_maps_list"
    GET_NETWORK_INFO = "get_network_info"
    GET_OFFLINE_MAP_STATUS = "get_offline_map_status"
    GET_PERSIST = "get_persist_map"
    GET_PROP = "get_prop"
    GET_RANDOM_PKEY = "get_random_pkey"
    GET_RECOVER_MAP = "get_recover_map"
    GET_RECOVER_MAPS = "get_recover_maps"
    GET_ROOM_MAPPING = "get_room_mapping"
    GET_SCENES_VALID_TIDS = "get_scenes_valid_tids"
    GET_SEGMENT_STATUS = "get_segment_status"
    GET_SERIAL_NUMBER = "get_serial_number"
    GET_SERVER_TIMER = "get_server_timer"
    GET_SMART_WASH_PARAMS = "get_smart_wash_params"
    GET_SOUND_PROGRESS = "get_sound_progress"
    GET_SOUND_VOLUME = "get_sound_volume"
    GET_STATUS = "get_status"
    GET_TESTID = "get_testid"
    GET_TIMER = "get_timer"
    GET_TIMER_DETAIL = "get_timer_detail"
    GET_TIMER_SUMMARY = "get_timer_summary"
    GET_TIMEZONE = "get_timezone"
    GET_TURN_SERVER = "get_turn_server"
    GET_VALLEY_ELECTRICITY_TIMER = "get_valley_electricity_timer"
    GET_WASH_DEBUG_PARAMS = "get_wash_debug_params"
    GET_WASH_TOWEL_MODE = "get_wash_towel_mode"
    GET_WASH_TOWEL_PARAMS = "get_wash_towel_params"
    GET_WATER_BOX_CUSTOM_MODE = "get_water_box_custom_mode"
    LOAD_MULTI_MAP = "load_multi_map"
    MANUAL_BAK_MAP = "manual_bak_map"
    MANUAL_SEGMENT_MAP = "manual_segment_map"
    MERGE_SEGMENT = "merge_segment"
    MOP_MODE = "mop_mode"
    MOP_TEMPLATE_ID = "mop_template_id"
    NAME_MULTI_MAP = "name_multi_map"
    NAME_SEGMENT = "name_segment"
    PLAY_AUDIO = "play_audio"
    RECOVER_MAP = "recover_map"
    RECOVER_MULTI_MAP = "recover_multi_map"
    RESET_CONSUMABLE = "reset_consumable"
    RESET_HOMESEC_PASSWORD = "reset_homesec_password"
    RESET_MAP = "reset_map"
    RESOLVE_ERROR = "resolve_error"
    RESUME_SEGMENT_CLEAN = "resume_segment_clean"
    RESUME_ZONED_CLEAN = "resume_zoned_clean"
    RETRY_REQUEST = "retry_request"
    REUNION_SCENES = "reunion_scenes"
    SAVE_FURNITURES = "save_furnitures"
    SAVE_MAP = "save_map"
    SEND_ICE_TO_ROBOT = "send_ice_to_robot"
    SEND_SDP_TO_ROBOT = "send_sdp_to_robot"
    SET_AIRDRY_HOURS = "set_airdry_hours"
    SET_APP_TIMEZONE = "set_app_timezone"
    SET_AUTO_DELIVERY_CLEANING_FLUID = "set_auto_delivery_cleaning_fluid"
    SET_CAMERA_STATUS = "set_camera_status"
    SET_CARPET_AREA = "set_carpet_area"
    SET_CARPET_CLEAN_MODE = "set_carpet_clean_mode"
    SET_CARPET_MODE = "set_carpet_mode"
    SET_CHILD_LOCK_STATUS = "set_child_lock_status"
    SET_CLEAN_FOLLOW_GROUND_MATERIAL_STATUS = "set_clean_follow_ground_material_status"
    SET_CLEAN_MOTOR_MODE = "set_clean_motor_mode"
    SET_CLEAN_SEQUENCE = "set_clean_sequence"
    SET_CLEAN_REPEAT_TIMES = "set_clean_repeat_times"
    SET_COLLISION_AVOID_STATUS = "set_collision_avoid_status"
    SET_CUSTOM_MODE = "set_custom_mode"
    SET_CUSTOMIZE_CLEAN_MODE = "set_customize_clean_mode"
    SET_DND_TIMER = "set_dnd_timer"
    SET_DND_TIMER_ACTIONS = "set_dnd_timer_actions"
    SET_DUST_COLLECTION_MODE = "set_dust_collection_mode"
    SET_DUST_COLLECTION_SWITCH_STATUS = "set_dust_collection_switch_status"
    SET_FAN_MOTOR_WORK_TIMEOUT = "set_fan_motor_work_timeout"
    SET_FDS_ENDPOINT = "set_fds_endpoint"
    SET_FLOW_LED_STATUS = "set_flow_led_status"
    SET_HOMESEC_PASSWORD = "set_homesec_password"
    SET_IDENTIFY_FURNITURE_STATUS = "set_identify_furniture_status"
    SET_IDENTIFY_GROUND_MATERIAL_STATUS = "set_identify_ground_material_status"
    SET_IGNORE_CARPET_ZONE = "set_ignore_carpet_zone"
    SET_IGNORE_IDENTIFY_AREA = "set_ignore_identify_area"
    SET_LAB_STATUS = "set_lab_status"
    SET_LED_STATUS = "set_led_status"
    SET_MAP_BEAUTIFICATION_STATUS = "set_map_beautification_status"
    SET_MOP_MODE = "set_mop_mode"
    SET_MOP_MOTOR_STATUS = "set_mop_motor_status"
    SET_MOP_TEMPLATE_ID = "set_mop_template_id"
    SET_OFFLINE_MAP_STATUS = "set_offline_map_status"
    SET_SCENES_SEGMENTS = "set_scenes_segments"
    SET_SCENES_ZONES = "set_scenes_zones"
    SET_SEGMENT_GROUND_MATERIAL = "set_segment_ground_material"
    SET_SERVER_TIMER = "set_server_timer"
    SET_SMART_WASH_PARAMS = "set_smart_wash_params"
    SET_SWITCH_MOP_MODE = "set_switch_map_mode"
    SET_TIMER = "set_timer"
    SET_TIMEZONE = "set_timezone"
    SET_VALLEY_ELECTRICITY_TIMER = "set_valley_electricity_timer"
    SET_VOICE_CHAT_VOLUME = "set_voice_chat_volume"
    SET_WASH_DEBUG_PARAMS = "set_wash_debug_params"
    SET_WASH_TOWEL_MODE = "set_wash_towel_mode"
    SET_WASH_TOWEL_PARAMS = "set_wash_towel_params"
    SET_WATER_BOX_CUSTOM_MODE = "set_water_box_custom_mode"
    SET_WATER_BOX_DISTANCE_OFF = "set_water_box_distance_off"
    SORT_MOP_TEMPLATE_PARAMS = "sort_mop_template_params"
    SPLIT_SEGMENT = "split_segment"
    START_CAMERA_PREVIEW = "start_camera_preview"
    START_CLEAN = "start_clean"
    START_EDIT_MAP = "start_edit_map"
    START_VOICE_CHAT = "start_voice_chat"
    START_WASH_THEN_CHARGE = "start_wash_then_charge"
    STOP_CAMERA_PREVIEW = "stop_camera_preview"
    STOP_FAN_MOTOR_WORK = "stop_fan_motor_work"
    STOP_GOTO_TARGET = "stop_goto_target"
    STOP_SEGMENT_CLEAN = "stop_segment_clean"
    STOP_VOICE_CHAT = "stop_voice_chat"
    STOP_ZONED_CLEAN = "stop_zoned_clean"
    SWITCH_VIDEO_QUALITY = "switch_video_quality"
    SWITCH_WATER_MARK = "switch_water_mark"
    TEST_SOUND_VOLUME = "test_sound_volume"
    UPD_SERVER_TIMER = "upd_server_timer"
    UPD_TIMER = "upd_timer"
    UPDATE_DOCK = "update_dock"
    UPDATE_MOP_TEMPLATE_PARAMS = "update_mop_template_params"
    UPLOAD_DATA_FOR_DEBUG_MODE = "upload_data_for_debug_mode"
    UPLOAD_PHOTO = "upload_photo"
    USE_NEW_MAP = "use_new_map"
    USE_OLD_MAP = "use_old_map"
    USER_UPLOAD_LOG = "user_upload_log"
    SET_STRETCH_TAG_STATUS = "set_stretch_tag_status"
    GET_STRETCH_TAG_STATUS = "get_stretch_tag_status"
    SET_RIGHT_BRUSH_STRETCH_STATUS = "set_right_brush_stretch_status"
    GET_RIGHT_BRUSH_STRETCH_STATUS = "get_right_brush_stretch_status"
    SET_DIRTY_OBJECT_DETECT_STATUS = "set_dirty_object_detect_status"
    GET_DIRTY_OBJECT_DETECT_STATUS = "get_dirty_object_detect_status"
    SET_WASH_WATER_TEMPERATURE = "set_wash_water_temperature"
    GET_WASH_WATER_TEMPERATURE = "get_wash_water_temperature"
    APP_EMPTY_RINSE_TANK_WATER = "app_empty_rinse_tank_water"
    SET_PET_SUPPLIES_DEEP_CLEAN_STATUS = "set_pet_supplies_deep_clean_status"
    GET_PET_SUPPLIES_DEEP_CLEAN_STATUS = "get_pet_supplies_deep_clean_status"
    SET_AP_MIC_LED_STATUS = "set_ap_mic_led_status"
    GET_AP_MIC_LED_STATUS = "get_ap_mic_led_status"
    SET_HANDLE_LEAK_WATER_STATUS = "set_handle_leak_water_status"
    GET_HANDLE_LEAK_WATER_STATUS = "get_handle_leak_water_status"
    APP_IGNORE_DIRTY_OBJECTS = "app_ignore_dirty_objects"
    MATTER_GET_STATUS = "matter.get_status"
    MATTER_DNLD_KEY = "matter.dnld_key"
    MATTER_RESET = "matter.reset"
    SET_GAP_DEEP_CLEAN_STATUS = "set_gap_deep_clean_status"
    GET_GAP_DEEP_CLEAN_STATUS = "get_gap_deep_clean_status"
    APP_SET_ROBOT_SETTING = "app_set_robot_setting"
    APP_GET_ROBOT_SETTING = "app_get_robot_setting"


@dataclass
class CommandInfo:
    params: list | dict | int | None = None


CommandInfoMap: dict[RoborockCommand | None, CommandInfo] = {
    RoborockCommand.APP_CHARGE: CommandInfo(params=[]),
    RoborockCommand.APP_GET_DRYER_SETTING: CommandInfo(params=None),
    RoborockCommand.APP_GET_INIT_STATUS: CommandInfo(params=[]),
    RoborockCommand.APP_GOTO_TARGET: CommandInfo(params=[25000, 24850]),
    RoborockCommand.APP_PAUSE: CommandInfo(params=[]),
    RoborockCommand.APP_RC_END: CommandInfo(params=[]),
    RoborockCommand.APP_RC_MOVE: CommandInfo(params=None),
    RoborockCommand.APP_RC_START: CommandInfo(params=[]),
    RoborockCommand.APP_RC_STOP: CommandInfo(params=[]),
    RoborockCommand.APP_SEGMENT_CLEAN: CommandInfo(params=[{"segments": 16, "repeat": 2}]),
    # RoborockCommand.APP_SEGMENT_CLEAN: CommandInfo(prefix=b"\x00\x00\x00\x87", params=None),
    RoborockCommand.APP_SET_DRYER_SETTING: CommandInfo(params=None),
    RoborockCommand.APP_SET_SMART_CLIFF_FORBIDDEN: CommandInfo(params={"zones": [], "map_index": 0}),
    RoborockCommand.APP_SPOT: CommandInfo(params=[]),
    RoborockCommand.APP_START: CommandInfo(params=None),
    # RoborockCommand.APP_START: CommandInfo(prefix=b"\x00\x00\x00\x87", params=[{"use_new_map": 1}]),
    RoborockCommand.APP_START_COLLECT_DUST: CommandInfo(params=None),
    RoborockCommand.APP_START_WASH: CommandInfo(params=None),
    RoborockCommand.APP_STAT: CommandInfo(
        params=[
            {
                "ver": "0.1",
                "data": [
                    {
                        "times": [1682723478],
                        "data": {
                            "region": "America/Sao_Paulo",
                            "pluginVersion": "2820",
                            "mnc": "*",
                            "os": "ios",
                            "osVersion": "16.1",
                            "mcc": "not-cn",
                            "language": "en_BR",
                            "mobileBrand": "*",
                            "appType": "roborock",
                            "mobileModel": "iPhone13,1",
                        },
                        "type": 2,
                    }
                ],
            }
        ],
    ),
    RoborockCommand.APP_STOP: CommandInfo(params=[]),
    RoborockCommand.APP_STOP_WASH: CommandInfo(params=None),
    RoborockCommand.APP_WAKEUP_ROBOT: CommandInfo(params=[]),
    RoborockCommand.APP_ZONED_CLEAN: CommandInfo(params=[[24900, 25100, 26300, 26450, 1]]),
    RoborockCommand.CHANGE_SOUND_VOLUME: CommandInfo(params=None),
    RoborockCommand.CLOSE_DND_TIMER: CommandInfo(params=[]),
    RoborockCommand.CLOSE_VALLEY_ELECTRICITY_TIMER: CommandInfo(params=[]),
    RoborockCommand.DNLD_INSTALL_SOUND: CommandInfo(
        params={"url": "https://awsusor0.fds.api.xiaomi.com/app/topazsv/voice-pkg/package/en.pkg", "sid": 3, "sver": 5},
    ),
    RoborockCommand.ENABLE_LOG_UPLOAD: CommandInfo(params=[9, 2]),
    RoborockCommand.END_EDIT_MAP: CommandInfo(params=[]),
    RoborockCommand.FIND_ME: CommandInfo(params=None),
    RoborockCommand.GET_CAMERA_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_CARPET_CLEAN_MODE: CommandInfo(params=[]),
    RoborockCommand.GET_CARPET_MODE: CommandInfo(params=[]),
    RoborockCommand.GET_CHILD_LOCK_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_CLEAN_RECORD: CommandInfo(params=[1682257961]),
    RoborockCommand.GET_CLEAN_RECORD_MAP: CommandInfo(params={"start_time": 1682597877}),
    RoborockCommand.GET_CLEAN_SEQUENCE: CommandInfo(params=[]),
    RoborockCommand.GET_CLEAN_SUMMARY: CommandInfo(params=[]),
    RoborockCommand.GET_COLLISION_AVOID_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_CONSUMABLE: CommandInfo(params=[]),
    RoborockCommand.GET_CURRENT_SOUND: CommandInfo(params=[]),
    RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE: CommandInfo(params=[]),
    RoborockCommand.GET_CUSTOM_MODE: CommandInfo(params=None),
    RoborockCommand.GET_DEVICE_ICE: CommandInfo(params=[]),
    RoborockCommand.GET_DEVICE_SDP: CommandInfo(params=[]),
    RoborockCommand.GET_DND_TIMER: CommandInfo(params=[]),
    RoborockCommand.GET_DUST_COLLECTION_MODE: CommandInfo(params=None),
    RoborockCommand.GET_FLOW_LED_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_HOMESEC_CONNECT_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_IDENTIFY_FURNITURE_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_IDENTIFY_GROUND_MATERIAL_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_LED_STATUS: CommandInfo(params=[]),
    RoborockCommand.GET_MAP_V1: CommandInfo(params={}),
    RoborockCommand.GET_MOP_TEMPLATE_PARAMS_SUMMARY: CommandInfo(params={}),
    RoborockCommand.GET_MULTI_MAP: CommandInfo(params={"map_index": 0}),
    RoborockCommand.GET_MULTI_MAPS_LIST: CommandInfo(params=[]),
    RoborockCommand.GET_NETWORK_INFO: CommandInfo(params=[]),
    RoborockCommand.GET_PROP: CommandInfo(params=["get_status"]),
    RoborockCommand.GET_ROOM_MAPPING: CommandInfo(params=[]),
    RoborockCommand.GET_SCENES_VALID_TIDS: CommandInfo(params={}),
    RoborockCommand.GET_SERIAL_NUMBER: CommandInfo(params=[]),
    RoborockCommand.GET_SERVER_TIMER: CommandInfo(params=[]),
    RoborockCommand.GET_SMART_WASH_PARAMS: CommandInfo(params=None),
    RoborockCommand.GET_SOUND_PROGRESS: CommandInfo(params=[]),
    RoborockCommand.GET_SOUND_VOLUME: CommandInfo(params=[]),
    RoborockCommand.GET_STATUS: CommandInfo(params=None),
    RoborockCommand.GET_TIMEZONE: CommandInfo(params=[]),
    RoborockCommand.GET_TURN_SERVER: CommandInfo(params=[]),
    RoborockCommand.GET_VALLEY_ELECTRICITY_TIMER: CommandInfo(params=[]),
    RoborockCommand.GET_WASH_TOWEL_MODE: CommandInfo(params=None),
    RoborockCommand.LOAD_MULTI_MAP: CommandInfo(params=None),
    RoborockCommand.NAME_SEGMENT: CommandInfo(params=None),
    RoborockCommand.REUNION_SCENES: CommandInfo(params={"data": [{"tid": "1687830208457"}]}),
    RoborockCommand.RESET_CONSUMABLE: CommandInfo(params=None),
    RoborockCommand.RESUME_SEGMENT_CLEAN: CommandInfo(params=None),
    RoborockCommand.RESUME_ZONED_CLEAN: CommandInfo(params=None),
    RoborockCommand.RETRY_REQUEST: CommandInfo(params={"retry_id": 439374, "retry_count": 8, "method": "save_map"}),
    RoborockCommand.SAVE_MAP: CommandInfo(
        params={
            "data": [
                [1, 25043, 24952, 26167, 24952],
                [0, 25043, 25514, 26167, 25514, 26167, 24390, 25043, 24390],
                [2, 25038, 26782, 26162, 26782, 26162, 25658, 25038, 25658],
                [100, 0],
            ],
            "need_retry": 1,
        },
    ),
    RoborockCommand.SEND_ICE_TO_ROBOT: CommandInfo(
        params={
            "app_ice": "eyJjYW5kaWRhdGUiOiAiY2FuZGlkYXRlOjE1MzE5NzE5NTEgMSB1ZHAgNDE4MTk5MDMgNTQuMTc0LjE4Ni4yNDkgNTQxNzU"
            "gdHlwIHJlbGF5IHJhZGRyIDE3Ny4xOC4xMzQuOTkgcnBvcnQgNjQ2OTEgZ2VuZXJhdGlvbiAwIHVmcmFnIDVOMVogbmV0d2"
            "9yay1pZCAxIG5ldHdvcmstY29zdCAxMCIsICJzZHBNTGluZUluZGV4IjogMSwgInNkcE1pZCI6ICIxIn0="
        },
    ),
    RoborockCommand.SET_APP_TIMEZONE: CommandInfo(params=["America/Sao_Paulo", 2]),
    RoborockCommand.SET_CAMERA_STATUS: CommandInfo(params=[3493]),
    RoborockCommand.SET_CARPET_CLEAN_MODE: CommandInfo(params={"carpet_clean_mode": 0}),
    RoborockCommand.SET_CARPET_MODE: CommandInfo(
        params=[{"enable": 1, "current_high": 500, "current_integral": 450, "current_low": 400, "stall_time": 10}],
    ),
    RoborockCommand.SET_CHILD_LOCK_STATUS: CommandInfo(params={"lock_status": 0}),
    RoborockCommand.SET_CLEAN_MOTOR_MODE: CommandInfo(
        params=[{"fan_power": 106, "mop_mode": 302, "water_box_mode": 204}]
    ),
    RoborockCommand.SET_COLLISION_AVOID_STATUS: CommandInfo(params={"status": 1}),
    RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE: CommandInfo(params={"data": [], "need_retry": 1}),
    RoborockCommand.SET_CUSTOM_MODE: CommandInfo(params=[108]),
    RoborockCommand.SET_DND_TIMER: CommandInfo(params=[22, 0, 8, 0]),
    RoborockCommand.SET_DUST_COLLECTION_MODE: CommandInfo(params=None),
    RoborockCommand.SET_FDS_ENDPOINT: CommandInfo(params=["awsusor0.fds.api.xiaomi.com"]),
    RoborockCommand.SET_FLOW_LED_STATUS: CommandInfo(params={"status": 1}),
    RoborockCommand.SET_IDENTIFY_FURNITURE_STATUS: CommandInfo(params={"status": 1}),
    RoborockCommand.SET_IDENTIFY_GROUND_MATERIAL_STATUS: CommandInfo(params={"status": 1}),
    RoborockCommand.SET_LED_STATUS: CommandInfo(params=[1]),
    RoborockCommand.SET_MOP_MODE: CommandInfo(params=None),
    RoborockCommand.SET_SCENES_SEGMENTS: CommandInfo(
        params={"data": [{"tid": "1687831528786", "segs": [{"sid": 22}, {"sid": 18}]}]}
    ),
    RoborockCommand.SET_SCENES_ZONES: CommandInfo(
        params={"data": [{"zones": [{"zid": 0, "range": [27700, 23750, 30850, 26900]}], "tid": "1687831073722"}]}
    ),
    RoborockCommand.SET_SERVER_TIMER: CommandInfo(
        params={
            "data": [["1687793948482", ["39 12 * * 0,1,2,3,4,5,6", ["start_clean", 106, "0", -1]]]],
            "need_retry": 1,
        }
    ),
    RoborockCommand.SET_SMART_WASH_PARAMS: CommandInfo(params=None),
    RoborockCommand.SET_TIMEZONE: CommandInfo(params=["America/Sao_Paulo"]),
    RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER: CommandInfo(params=[0, 0, 8, 0]),
    RoborockCommand.SET_WASH_TOWEL_MODE: CommandInfo(params=None),
    RoborockCommand.SET_WATER_BOX_CUSTOM_MODE: CommandInfo(params=[203]),
    RoborockCommand.START_CAMERA_PREVIEW: CommandInfo(params={"client_id": "443f8636", "quality": "SD"}),
    RoborockCommand.START_EDIT_MAP: CommandInfo(params=[]),
    RoborockCommand.START_WASH_THEN_CHARGE: CommandInfo(params=None),
    RoborockCommand.STOP_CAMERA_PREVIEW: CommandInfo(params={"client_id": "443f8636"}),
    RoborockCommand.SWITCH_WATER_MARK: CommandInfo(params={"waterMark": "OFF"}),
    RoborockCommand.TEST_SOUND_VOLUME: CommandInfo(params=None),
    RoborockCommand.UPD_SERVER_TIMER: CommandInfo(params=[["1687793948482", "off"]]),
    RoborockCommand.DEL_SERVER_TIMER: CommandInfo(params=["1687793948482"]),
}


@dataclass
class DockSummary(RoborockBase):
    dust_collection_mode: DustCollectionMode | None = None
    wash_towel_mode: WashTowelMode | None = None
    smart_wash_params: SmartWashParams | None = None


@dataclass
class DeviceProp(RoborockBase):
    status: Status = field(default_factory=Status)
    clean_summary: CleanSummary = field(default_factory=CleanSummary)
    consumable: Consumable = field(default_factory=Consumable)
    last_clean_record: CleanRecord | None = None
    dock_summary: DockSummary | None = None
    dust_collection_mode_name: str | None = None

    def __post_init__(self) -> None:
        if (
            self.dock_summary
            and self.dock_summary.dust_collection_mode is not None
            and self.dock_summary.dust_collection_mode.mode is not None
        ):
            self.dust_collection_mode_name = self.dock_summary.dust_collection_mode.mode.name

    def update(self, device_prop: DeviceProp) -> None:
        if device_prop.status:
            self.status = device_prop.status
        if device_prop.clean_summary:
            self.clean_summary = device_prop.clean_summary
        if device_prop.consumable:
            self.consumable = device_prop.consumable
        if device_prop.last_clean_record:
            self.last_clean_record = device_prop.last_clean_record
        if device_prop.dock_summary:
            self.dock_summary = device_prop.dock_summary
        self.__post_init__()

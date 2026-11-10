"""Code mappings for Roborock mower devices."""

import logging
from typing import Self, cast

from roborock.data.code_mappings import RoborockModeEnum

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "MowerAfsStatus",
    "MowerChargeState",
    "MowerChargeType",
    "MowerConfMode",
    "MowerDetailState",
    "MowerDockState",
    "MowerEffMode",
    "MowerEnum",
    "MowerErrorCode",
    "MowerFcState",
    "MowerMappingState",
    "MowerMappingType",
    "MowerMowState",
    "MowerMowType",
    "MowerNetworkChannel",
    "MowerOffDockNoTaskStatus",
    "MowerOfflineStatus",
    "MowerOtaState",
    "MowerPattern",
    "MowerPendType",
    "MowerRemoteState",
    "MowerStartType",
    "MowerRemoteMsgType",
    "MowerRobotMsgType",
    "MowerAppButton",
    "MowerFsmEvent",
    "MowerFsmState",
    "MowerAckResult",
    "MowerPreferenceEffective",
    "MowerDirectionType",
    "MowerBoundaryPerception",
    "MowerPreferenceMode",
    "MowerPlanType",
    "MowerPlanStatus",
    "MowerWeekday",
    "MowerRainType",
    "MowerNavSolution",
    "MowerDriveMode",
    "MowerMobile4GMode",
    "MowerSkuRegion",
    "MowerStartDpType",
    "MowerFeature",
    "MowerMcuType",
    "MowerRtkMode",
]


class MowerEnum(RoborockModeEnum):
    """Base for mower enums."""

    @classmethod
    def from_code(cls, code: int | str) -> Self:
        """Resolve a wire value by name, string value, or integer code."""
        if (member := cls.from_any_optional(code)) is not None:
            return member
        _LOGGER.debug("Unknown %s code %r; defaulting to UNKNOWN", cls.__name__, code)
        return cast(Self, cls.UNKNOWN)  # type: ignore[attr-defined]


class MowerMowType(MowerEnum):
    """Mowing task selection reported by DPS 122."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    GLOBAL = ("global", 1)
    EDGE = ("edge", 2)
    SELECTION = ("selection", 3)
    ZONING = ("zoning", 4)
    REMOTE = ("remote", 5)
    RANDOM = ("random", 6)


class MowerMowState(MowerEnum):
    """Compact mowing state (MowStateDpValue.Type)."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    ZIGZAG_MOWING = ("zigzag_mowing", 1)
    EDGE_MOWING = ("edge_mowing", 2)
    TRANSITION = ("transition", 3)
    SUSPENDED = ("suspended", 4)
    REMOTE_WALKING = ("remote_walking", 5)
    REMOTE_MOWING = ("remote_mowing", 6)


class MowerMappingType(MowerEnum):
    """Mapping operation reported by DPS 124."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    LAWN_MAPPING = ("lawn_mapping", 1)
    FORBIDDEN_ZONE_MAPPING = ("forbidden_zone_mapping", 2)
    CHANNEL_MAPPING = ("channel_mapping", 3)
    SPLIT_WORKSPACE = ("split_workspace", 4)
    MERGE_WORKSPACE = ("merge_workspace", 5)
    BOUNDARY_MODIFY = ("boundary_modify", 6)


class MowerMappingState(MowerEnum):
    """Mapping activity reported by DPS 125."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    AUTO_MAPPING = ("auto_mapping", 1)
    TRACK_ERASE = ("track_erase", 2)
    SUSPENDED = ("suspended", 3)
    SAVING_MAP = ("saving_map", 4)
    REMOTE_WALKING = ("remote_walking", 5)
    REMOTE_MAPPING = ("remote_mapping", 6)


class MowerOtaState(MowerEnum):
    """Firmware update state reported by DPS 126."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    DOWNLOADING = ("downloading", 1)
    INSTALLING = ("installing", 2)
    REBOOTING = ("rebooting", 3)


class MowerChargeState(MowerEnum):
    """Charging state reported by DPS 127."""

    UNKNOWN = ("unknown", -1)
    NOT_CHARGING = ("not_charging", 0)
    CHARGING = ("charging", 1)
    CHARGE_COMPLETED = ("charge_completed", 2)
    WAITING_CHARGE = ("waiting_charge", 3)
    LOW_POWER = ("low_power", 4)
    CHARGE_ERROR = ("charge_error", 5)


class MowerDockState(MowerEnum):
    """Return-to-dock state reported by DPS 128."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    MOVING_TO_TARGET = ("moving_to_target", 1)
    DOCKING = ("docking", 2)
    SUSPENDED = ("suspended", 3)


class MowerChargeType(MowerEnum):
    """Reason for returning to charge reported by DPS 129."""

    UNKNOWN = ("unknown", 0)
    MANUAL_DOCK = ("manual_dock", 1)
    RAIN_DOCK = ("rain_dock", 2)
    DO_NOT_DISTURB_DOCK = ("do_not_disturb_dock", 3)
    STANDBY_TIMEOUT_DOCK = ("standby_timeout_dock", 4)
    LOW_BATTERY_DOCK = ("low_battery_dock", 5)
    TASK_FINISHED_DOCK = ("task_finished_dock", 6)
    MOW_FAULT_DOCK = ("mow_fault_dock", 7)


class MowerPendType(MowerEnum):
    """Pause or interruption reason reported by DPS 130."""

    UNKNOWN = ("unknown", -1)
    NOT_SUSPENDED = ("not_suspended", 0)
    APP_PAUSE = ("app_pause", 1)
    BUTTON_EMERGENCY_STOP = ("button_emergency_stop", 2)
    FAULT = ("fault", 3)
    BREAKPOINT_PAUSE = ("breakpoint_pause", 4)
    OTHER = ("other", 5)


class MowerRemoteState(MowerEnum):
    """Remote control state reported by DPS 131."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    VIDEO_REMOTE = ("video_remote", 1)
    REMOTE_WALKING = ("remote_walking", 2)


class MowerStartType(MowerEnum):
    """Task start trigger reported by DPS 132."""

    UNKNOWN = ("unknown", -1)
    DEFAULT = ("default", 0)
    APP_START = ("app_start", 1)
    BUTTON_START = ("button_start", 2)
    SCHEDULE_START = ("schedule_start", 3)


class MowerEffMode(MowerEnum):
    """Reported efficiency mode on DPS 133."""

    UNKNOWN = ("unknown", 0)
    DAILY = ("daily", 1)
    PRECISE = ("precise", 2)
    FAST = ("fast", 3)


class MowerPattern(MowerEnum):
    """Reported mowing pattern on DPS 136."""

    UNKNOWN = ("unknown", 0)
    ZIGZAG = ("zigzag", 1)
    WELL = ("well", 2)
    DIAMOND = ("diamond", 3)
    TRIANGLE = ("triangle", 4)
    AUTO_DEFLECT = ("auto_deflect", 5)
    RANDOM = ("random", 6)


class MowerConfMode(MowerEnum):
    """Preference configuration scope on DPS 137."""

    UNKNOWN = ("unknown", 0)
    GLOBAL_CONFIG = ("global_config", 1)
    ZONE_CUSTOM = ("zone_custom", 2)


class MowerOfflineStatus(MowerEnum):
    """Shutdown or reboot reason on DPS 138."""

    UNKNOWN = ("unknown", -1)
    ONLINE = ("online", 0)
    MANUAL_SHUTDOWN = ("manual_shutdown", 1)
    SLEEP_SHUTDOWN = ("sleep_shutdown", 2)
    LOW_BATTERY_SHUTDOWN = ("low_battery_shutdown", 3)
    UPGRADE_REBOOT = ("upgrade_reboot", 4)


class MowerFcState(MowerEnum):
    """Factory or test mode indicator on DPS 141."""

    UNKNOWN = ("unknown", -1)
    NOT_FC = ("not_fc", 0)
    FC = ("fc", 1)


class MowerOffDockNoTaskStatus(MowerEnum):
    """Mower off-dock status without an active task on DPS 143."""

    UNKNOWN = ("unknown", 0)
    WAITING = ("waiting", 1)
    SUSPENDING = ("suspending", 2)
    DOCKING = ("docking", 3)
    REMOTING = ("remoting", 4)


class MowerAfsStatus(MowerEnum):
    """Service status on DPS 144."""

    UNKNOWN = ("unknown", -1)
    IDLE = ("idle", 0)
    BIT = ("bit", 1)
    MMT_OBA = ("mmt_oba", 2)
    CALIBRATION = ("calibration", 3)
    ACTIVE = ("active", 4)
    INACTIVE = ("inactive", 5)


class MowerNetworkChannel(MowerEnum):
    """Current network route on DPS 145."""

    UNKNOWN = ("unknown", 0)
    WLAN0 = ("wlan0", 1)
    WLAN1 = ("wlan1", 2)
    MOBILE_4G = ("mobile_4g", 3)


class MowerDetailState(MowerEnum):
    """Detailed task state reported on DPS 123 and in GET_ROBOT_INFO replies."""

    UNKNOWN = ("unknown", 0)

    MAP_INITIALIZING = ("map_initializing", 1)
    MAP_UNDOCKING = ("map_undocking", 2)
    MAP_UNDOCK_FAULT = ("map_undock_fault", 3)
    MAP_LOCATING = ("map_locating", 4)
    MAP_PREPARE_BOUNDARY = ("map_prepare_boundary", 5)
    MAP_PREPARE_ISLAND = ("map_prepare_island", 6)
    MAP_PREPARE_PATH = ("map_prepare_path", 7)
    MAP_BOUNDARY = ("map_boundary", 8)
    MAP_ISLAND = ("map_island", 9)
    MAP_PATH = ("map_path", 10)
    MAP_BOUNDARY_AUTO = ("map_boundary_auto", 11)
    # The protocol spelling "MAP_ERASEING" is intentional.
    MAP_ERASING = ("map_eraseing", 12)
    MAP_SAVE = ("map_save", 13)
    MAP_WAIT = ("map_wait", 14)
    MAP_RECOVERABLE_FAULT = ("map_recoverable_fault", 15)
    MAP_FAULT = ("map_fault", 16)
    MAP_EMERGENCY_STOP = ("map_emergency_stop", 17)
    MAP_WAITING_FAULT = ("map_waiting_fault", 18)
    MAP_NO_AVOID = ("map_no_avoid", 19)
    MAP_PREPARE_NO_AVOID = ("map_prepare_no_avoid", 20)
    MAP_RESET_PASSAGE = ("map_reset_passage", 21)
    MAP_PREPARE_RESET_PASSAGE = ("map_prepare_reset_passage", 22)
    MAP_EDIT_BOUNDARY = ("map_edit_boundary", 23)
    MAP_PREPARE_EDIT_BOUNDARY = ("map_prepare_edit_boundary", 24)
    MAP_CONFIRM_EDIT_BOUNDARY = ("map_confirm_edit_boundary", 25)

    MOW_INITIALIZING = ("mow_initializing", 51)
    MOW_UNDOCKING = ("mow_undocking", 52)
    MOW_LOCATING = ("mow_locating", 53)
    MOW_ADJUST_CUTTER = ("mow_adjust_cutter", 54)
    MOW_ZIG_ZAG = ("mow_zig_zag", 55)
    MOW_EDGE = ("mow_edge", 56)
    MOW_GOTO = ("mow_goto", 57)
    MOW_SUSPEND = ("mow_suspend", 58)
    MOW_RECOVERABLE_FAULT = ("mow_recoverable_fault", 59)
    MOW_FAULT = ("mow_fault", 60)
    MOW_DOCK_RAINFALL = ("mow_dock_rainfall", 61)
    MOW_DOCK_NOTDISTURB = ("mow_dock_notdisturb", 62)
    MOW_DOCK_LOW_BATTERY = ("mow_dock_low_battery", 63)
    MOW_WAIT = ("mow_wait", 64)
    MOW_PREPARE_REMOTE = ("mow_prepare_remote", 65)
    MOW_REMOTE = ("mow_remote", 66)
    MOW_EMERGENCY_STOP = ("mow_emergency_stop", 67)
    MOW_DOCK_MANUAL = ("mow_dock_manual", 68)
    MOW_DOCK_FAULT = ("mow_dock_fault", 69)
    MOW_REMOTE_UNDOCKING = ("mow_remote_undocking", 70)
    MOW_TO_DOCK_INITIALIZING = ("mow_to_dock_initializing", 71)
    MOW_TO_DOCK_LOCATING = ("mow_to_dock_locating", 72)
    MOW_TO_DOCK_RECOVERABLE_FAULT = ("mow_to_dock_recoverable_fault", 73)
    MOW_TO_DOCK_FAULT = ("mow_to_dock_fault", 74)
    MOW_TO_DOCK_EMERGENCY_STOP = ("mow_to_dock_emergency_stop", 75)
    MOW_TO_DOCK_CHARGING = ("mow_to_dock_charging", 76)
    MOW_TO_DOCK_CHARGE_COMPLETED = ("mow_to_dock_charge_completed", 77)
    MOW_PAUSE = ("mow_pause", 78)

    FREE = ("free", 101)
    FREE_INITIALIZING = ("free_initializing", 102)
    FREE_LOCATING = ("free_locating", 103)
    FREE_DOCK_MANUAL = ("free_dock_manual", 104)
    FREE_DOCK_MOW_END = ("free_dock_mow_end", 105)
    FREE_DOCK_PLAN_END = ("free_dock_plan_end", 106)
    FREE_EMERGENCY_STOP = ("free_emergency_stop", 107)
    FREE_RECOVERABLE_FAULT = ("free_recoverable_fault", 108)
    FREE_FAULT = ("free_fault", 109)
    FREE_BATTERY_HOLD_MODE = ("free_battery_hold_mode", 110)

    CHARGING = ("charging", 151)
    CHARGE_COMPLETED = ("charge_completed", 152)
    CHARGE_WAITING = ("charge_waiting", 153)
    CHARGE_FAULT = ("charge_fault", 154)


class MowerErrorCode(MowerEnum):
    """User-facing error code reported by DPS 120."""

    UNKNOWN = ("unknown", 0)
    MAIN_CUTTER_OVER_CURRENT = ("main_cutter_over_current", 1)
    MAIN_CUTTER_OVER_TEMPERATURE = ("main_cutter_over_temperature", 2)
    MAIN_CUTTER_DYNAMIC_UNBALANCE = ("main_cutter_dynamic_unbalance", 3)
    EDGE_CUTTER_OVER_CURRENT = ("edge_cutter_over_current", 4)
    EDGE_CUTTER_OVER_TEMPERATURE = ("edge_cutter_over_temperature", 5)
    EDGE_CUTTER_DYNAMIC_UNBALANCE = ("edge_cutter_dynamic_unbalance", 6)
    HEIGHT_MODULE_ADJUSTING_INCOMPLETE = ("height_module_adjusting_incomplete", 7)
    TRAVEL_MOTOR_LEFT_FRONT_OVER_CURRENT = ("travel_motor_left_front_over_current", 8)
    TRAVEL_MOTOR_RIGHT_FRONT_OVER_CURRENT = ("travel_motor_right_front_over_current", 9)
    TRAVEL_MOTOR_LEFT_REAR_OVER_CURRENT = ("travel_motor_left_rear_over_current", 10)
    TRAVEL_MOTOR_RIGHT_REAR_OVER_CURRENT = ("travel_motor_right_rear_over_current", 11)
    TRAVEL_MOTOR_OVER_TEMPERATURE = ("travel_motor_over_temperature", 12)
    STEERING_MOTOR_LEFT_FRONT_OVER_CURRENT = ("steering_motor_left_front_over_current", 13)
    STEERING_MOTOR_RIGHT_FRONT_OVER_CURRENT = ("steering_motor_right_front_over_current", 14)
    STEERING_MOTOR_OVER_TEMPERATURE = ("steering_motor_over_temperature", 15)
    STOP = ("stop", 16)
    TILT = ("tilt", 17)
    LIFT = ("lift", 18)
    FLIP = ("flip", 19)
    OUT_OF_BOUND = ("out_of_bound", 20)
    BUMPER = ("bumper", 21)
    BATTERY_DISCHARGE_OVER_TEMPERATURE = ("battery_discharge_over_temperature", 22)
    BATTERY_DISCHARGE_LOW_TEMPERATURE = ("battery_discharge_low_temperature", 23)
    BATTERY_UNOFFICIAL = ("battery_unofficial", 24)
    DIRTY_CHARGING_CLIPS = ("dirty_charging_clips", 25)
    CHARGE_STATION_NO_POWER = ("charge_station_no_power", 26)
    CAMERA_DIRTY_OR_OBSTRUCTED = ("camera_dirty_or_obstructed", 27)
    CAMERA_OVER_TEMPERATURE = ("camera_over_temperature", 28)
    CAMERA_LED_OBSTRUCTED = ("camera_led_obstructed", 29)
    LIDAR_DIRTY = ("lidar_dirty", 30)
    LIDAR_OVER_TEMPERATURE = ("lidar_over_temperature", 31)
    LOCATION_FAILED = ("location_failed", 32)
    LOCATION_AT_ISLAND = ("location_at_island", 33)
    LOCATION_AT_NON_COMPLIANT_SLOPE = ("location_at_non_compliant_slope", 34)
    BE_TRAPPED = ("be_trapped", 35)
    CHARGE_STATION_OR_RTK_SLIGHT_MOVEMENT_DOCK = ("charge_station_or_rtk_slight_movement_dock", 36)
    N_RTK_SIGNIFICANT_MOVEMENT = ("n_rtk_significant_movement", 37)
    RTK_SIGNIFICANT_MOVEMENT = ("rtk_significant_movement", 38)
    DOCK_CHARGE_STATION_SEARCH_FAIL = ("dock_charge_station_search_fail", 39)
    DOCK_QRCODE_SCAN_FAIL = ("dock_qrcode_scan_fail", 40)
    DOCK_ADJUST_ERROR = ("dock_adjust_error", 41)
    UNDOCK_ERROR = ("undock_error", 42)
    BATTERY_CHARGE_OVER_TEMPERATURE = ("battery_charge_over_temperature", 43)
    BATTERY_CHARGE_LOW_TEMPERATURE = ("battery_charge_low_temperature", 44)
    CAMERA_SEVERELY_DIRTY = ("camera_severely_dirty", 45)
    NO_PLUGIN_KEY = ("no_plugin_key", 46)
    CAMERA_REAR_SIDE_DIRTY = ("camera_rear_side_dirty", 48)
    N_RTK_NETWORK_ERROR = ("n_rtk_network_error", 55)
    MAIN_CUTTER_FAULT = ("main_cutter_fault", 101)
    EDGE_CUTTER_FAULT = ("edge_cutter_fault", 102)
    HEIGHT_MODULE_FAULT = ("height_module_fault", 103)
    BATTERY_FAULT = ("battery_fault", 104)
    CAMERA_FAULT = ("camera_fault", 105)
    CAMERA_LED_FAULT = ("camera_led_fault", 106)
    MAIN_BOARD_FAULT = ("main_board_fault", 107)
    LIDAR_FAULT = ("lidar_fault", 108)
    TRAVEL_MOTOR_LEFT_FRONT_FAULT = ("travel_motor_left_front_fault", 109)
    TRAVEL_MOTOR_RIGHT_FRONT_FAULT = ("travel_motor_right_front_fault", 110)
    TRAVEL_MOTOR_LEFT_REAR_FAULT = ("travel_motor_left_rear_fault", 111)
    TRAVEL_MOTOR_RIGHT_REAR_FAULT = ("travel_motor_right_rear_fault", 112)
    STEERING_MOTOR_LEFT_FRONT_FAULT = ("steering_motor_left_front_fault", 113)
    STEERING_MOTOR_RIGHT_FRONT_FAULT = ("steering_motor_right_front_fault", 114)
    LED_SCREEN_FAULT = ("led_screen_fault", 115)
    LEFT_SIDE_CAMERA_FAULT = ("left_side_camera_fault", 116)
    RIGHT_SIDE_CAMERA_FAULT = ("right_side_camera_fault", 117)
    REAR_SIDE_CAMERA_FAULT = ("rear_side_camera_fault", 118)


class MowerRemoteMsgType(MowerEnum):
    """Structured command type sent in `RemoteMsg.type` (`rock.common.remote.RemoteMsg.Type`)."""

    UNKNOWN = ("unknown", 0)
    ACK = ("ack", 1)
    GET_FULL_MAP = ("get_full_map", 2)
    GET_ROBOT_STATUS = ("get_robot_status", 3)
    GET_SELF_CHECK_STATUS = ("get_self_check_status", 4)
    REMOTE_CONTROL = ("remote_control", 5)
    APP_BUTTON = ("app_button", 6)
    START_GET_INC_MAP = ("start_get_inc_map", 7)
    STOP_GET_INC_MAP = ("stop_get_inc_map", 8)
    GET_MAP_DIFF = ("get_map_diff", 9)
    GOTO_TARGET = ("goto_target", 10)
    GET_MAP_NAMES = ("get_map_names", 11)
    DELETE_MAP = ("delete_map", 12)
    GET_MAP_DIFFS = ("get_map_diffs", 13)
    PIN_CODE = ("pin_code", 14)
    LORA = ("lora", 15)
    PLAY_AUDIO = ("play_audio", 16)
    REMOTE_CMD = ("remote_cmd", 17)
    REMOTE_INFO_REQUEST = ("remote_info_request", 18)
    MOW_RECORD_REQUEST = ("mow_record_request", 19)
    SET_MOW_PREFERENCE = ("set_mow_preference", 20)
    DELETE_SINGLE_MOW_RECORD = ("delete_single_mow_record", 21)
    GET_SINGLE_DETAIL_MOW_RECORD = ("get_single_detail_mow_record", 22)
    SET_DEBUG_PARAMETER = ("set_debug_parameter", 23)
    GET_DEBUG_PARAMETER = ("get_debug_parameter", 24)
    CHANGE_MOW_PREFERENCE = ("change_mow_preference", 25)
    GET_MOW_PREFERENCE_CONFIG = ("get_mow_preference_config", 26)
    SET_NOT_DISTURB = ("set_not_disturb", 27)
    SET_RAINFALL = ("set_rainfall", 28)
    GET_USER_MODE_CONFIG = ("get_user_mode_config", 29)
    SET_AI_OBSTACLE_AVOIDANCE = ("set_ai_obstacle_avoidance", 30)
    GET_CURRENT_MOW_RECORDER = ("get_current_mow_recorder", 31)
    GET_FEATURESET = ("get_featureset", 32)
    GET_MAP_MOW_SNAPSHOT = ("get_map_mow_snapshot", 33)
    GET_HEIGHT_MOTOR_PARAMETER = ("get_height_motor_parameter", 34)
    DP_POINTS = ("dp_points", 35)
    CREATE_MOWING_PLAN = ("create_mowing_plan", 36)
    CHANGE_MOWING_PLAN = ("change_mowing_plan", 37)
    DELETE_MOWING_PLAN = ("delete_mowing_plan", 38)
    GET_MOW_SCHEDULE = ("get_mow_schedule", 39)
    DELETE_MOW_SCHEDULE = ("delete_mow_schedule", 40)
    GET_ROBOT_TIME_ZONE = ("get_robot_time_zone", 41)
    BIT_CHECK = ("bit_check", 42)
    MIDNIGHT_RESET = ("midnight_reset", 43)
    CHANGE_RUNTIME_TASK = ("change_runtime_task", 44)
    FIND_ME = ("find_me", 45)
    # The protocol spelling "GET_BlACK_BOX" is intentional.
    GET_BLACK_BOX = ("get_black_box", 46)
    SET_E_FENCE_RANGE = ("set_e_fence_range", 47)
    SET_ANTI_THEFT = ("set_anti_theft", 48)
    EDIT_MAP = ("edit_map", 49)
    GET_MAP_SELF_CHECK_RESULT = ("get_map_self_check_result", 50)
    SET_AUDIO = ("set_audio", 51)
    INJECT_ERRORS = ("inject_errors", 52)
    GET_E_FENCE_AREA = ("get_e_fence_area", 53)
    CLEAR_CACHE_FSM_EVENT = ("clear_cache_fsm_event", 54)
    GET_SKU_INFO = ("get_sku_info", 55)
    GET_BIT_HISTORY = ("get_bit_history", 56)
    SET_AP_BOARD_SN = ("set_ap_board_sn", 57)
    SET_NETWORK_MODE = ("set_network_mode", 58)
    UPDATE_TIMEZONE = ("update_timezone", 59)
    GET_SW_VERSION = ("get_sw_version", 60)
    GET_BIT_CHECK_LISTS = ("get_bit_check_lists", 61)
    GET_REMOTE_MOW_SELF_CHECK_RESULT = ("get_remote_mow_self_check_result", 62)
    SWITCH_TO_CUSTOM_AUDIO = ("switch_to_custom_audio", 63)
    GET_MCU_VERSION = ("get_mcu_version", 64)
    GET_PROJECT = ("get_project", 65)
    GET_ROBOT_INFO = ("get_robot_info", 66)
    GET_ROBOT_NETWORK_INFO = ("get_robot_network_info", 67)
    GET_ROBOT_BLUETOOTH_INFO = ("get_robot_bluetooth_info", 68)
    GET_ESIM_ACTIVE_STATUS = ("get_esim_active_status", 69)
    ACTIVE_ESIM = ("active_esim", 70)
    GET_ESIM_ACTIVE_RESULT = ("get_esim_active_result", 71)
    GET_ESIM_INFO = ("get_esim_info", 72)
    QUERY_SKU_CONFIG_STATUS = ("query_sku_config_status", 73)
    DOWNLOAD_SKU_CONFIG = ("download_sku_config", 74)
    SET_NAV_COMMON_CONFIG = ("set_nav_common_config", 75)
    GET_BOOT_INFO = ("get_boot_info", 76)
    GET_MOWING_ZONES = ("get_mowing_zones", 77)
    QUERY_BOARD_SN_INFO = ("query_board_sn_info", 78)
    UPDATE_BOARD_SN_INFO = ("update_board_sn_info", 79)
    GET_FEATURE_INFO = ("get_feature_info", 80)
    CLEAR_MOW_TASK = ("clear_mow_task", 90)
    GET_MIDNIGHT_RESET_FROM_ROBOT = ("get_midnight_reset_from_robot", 91)
    APP_BUTTON_WITH_MAP_SELF_CHECK_RESULT = ("app_button_with_map_self_check_result", 92)
    GET_SERIAL_NUMBER = ("get_serial_number", 93)
    USER_UPLOAD_LOG = ("user_upload_log", 94)
    SET_FDS_ENDPOINT = ("set_fds_endpoint", 95)
    ENABLE_LOG_UPLOAD = ("enable_log_upload", 96)
    APP_GET_INIT_STATUS = ("app_get_init_status", 97)
    GET_CURRENT_SOUND = ("get_current_sound", 98)
    DNLD_INSTALL_SOUND = ("dnld_install_sound", 99)
    GET_SOUND_PROGRESS = ("get_sound_progress", 100)
    APP_GET_WIFI_LIST = ("app_get_wifi_list", 101)
    APP_DELETE_WIFI = ("app_delete_wifi", 102)
    DISABLE_LOG_UPLOAD = ("disable_log_upload", 103)
    APP_GET_LOCALE = ("app_get_locale", 104)
    GET_INSTALLATION_WIZARD = ("get_installation_wizard", 105)
    SET_INSTALLATION_WIZARD = ("set_installation_wizard", 106)
    GET_TEST_ID = ("get_test_id", 107)
    GET_ZONES_PLAN_INFO = ("get_zones_plan_info", 108)
    SET_MOW_PREFERENCE_CONFIG = ("set_mow_preference_config", 109)
    GET_FAULT_RECORDS = ("get_fault_records", 110)
    GET_MAP_ABSTRACTS = ("get_map_abstracts", 111)
    UPDATE_GPS_INFO = ("update_gps_info", 112)
    APP_PROXY_INIT_OK = ("app_proxy_init_ok", 113)
    REQUEST_MAINTENANCE_STATUS = ("request_maintenance_status", 114)
    RESET_MAINTENANCE = ("reset_maintenance", 115)
    MAINTENANCE_REMINDER = ("maintenance_reminder", 116)
    CLEAR_REGION_PROGRESS = ("clear_region_progress", 117)
    GET_LOG_LTE_EVENTS = ("get_log_lte_events", 118)
    SET_LOG_LTE_REQUEST = ("set_log_lte_request", 119)
    GET_LOG_LTE_UPLOAD_INFO = ("get_log_lte_upload_info", 120)
    LOG_LTE_ACTIVATE = ("log_lte_activate", 121)
    WAKEUP_ROBOT = ("wakeup_robot", 122)
    EMC_MODE_REQUEST = ("emc_mode_request", 123)
    EMC_MODE_CONTROL = ("emc_mode_control", 124)
    EMC_MODE_INFO = ("emc_mode_info", 125)
    EMC_MODE_REQUEST_INFO = ("emc_mode_request_info", 126)
    SET_CUSTOM_MOW_PREFERENCE = ("set_custom_mow_preference", 127)
    GET_RTK_DEVICE_TYPE = ("get_rtk_device_type", 128)
    TRY_SWITCH_LTE_TYPE = ("try_switch_lte_type", 129)
    SIM_INSERT_TO_RC = ("sim_insert_to_rc", 130)
    SIM_ABUSE_TO_RC = ("sim_abuse_to_rc", 131)
    GET_SWITCH_LTE_RESULT = ("get_switch_lte_result", 132)
    SET_REMOTE_MOW_CONFIG = ("set_remote_mow_config", 133)
    SET_GRASS_ROPE = ("set_grass_rope", 134)
    NRTK_MSG_TO_MOWER = ("nrtk_msg_to_mower", 135)
    NRTK_ACCOUNT_STATUS = ("nrtk_account_status", 136)
    NRTK_APP_CONNECT = ("nrtk_app_connect", 137)
    GET_DOCK_LIST = ("get_dock_list", 138)
    SET_DOCK_PAIR = ("set_dock_pair", 139)
    GET_DOCK_PAIR_RESULT = ("get_dock_pair_result", 140)
    GET_DOCK_PAIRED_STATUS = ("get_dock_paired_status", 141)
    REMOVE_DOCK_PAIR = ("remove_dock_pair", 142)
    UPDATE_DOCK_PAIR = ("update_dock_pair", 143)
    SET_REALTIME_VIDEO = ("set_realtime_video", 144)
    GET_REALTIME_VIDEO = ("get_realtime_video", 145)
    SET_REALTIME_VIDEO_CONFIG = ("set_realtime_video_config", 146)
    MAP_FILE_REQUEST = ("map_file_request", 147)
    GET_PANORAMA_MAP_ABSTRACTS = ("get_panorama_map_abstracts", 148)
    GET_DOCK_CONNECT_STATUS = ("get_dock_connect_status", 149)
    SET_LIFT_ALARM_ENABLE = ("set_lift_alarm_enable", 150)
    DOCK_LORA_INIT = ("dock_lora_init", 151)
    SET_CHILD_LOCK_ENABLE = ("set_child_lock_enable", 152)
    NRTK_CLOUD_CONNECT = ("nrtk_cloud_connect", 153)
    GET_S1G_INFO_LIST = ("get_s1g_info_list", 160)
    CONNECT_TO_S1G = ("connect_to_s1g", 161)
    GET_S1G_SCAN_WIFI_LIST = ("get_s1g_scan_wifi_list", 162)
    SET_S1G_PAIR = ("set_s1g_pair", 163)
    REMOVE_S1G_PAIR = ("remove_s1g_pair", 164)
    GET_S1G_PAIR_STATUS = ("get_s1g_pair_status", 165)
    SAVE_S1G_IOT_CONFIG = ("save_s1g_iot_config", 166)


class MowerRobotMsgType(MowerEnum):
    """Reply or event type in `RobotMsg.type` (`rock.common.RobotMsg.Type`)."""

    UNKNOWN = ("unknown", 0)
    ACK = ("ack", 1)
    MAP_DATA = ("map_data", 2)
    MAP_NAME = ("map_name", 3)
    MAP_NAMES = ("map_names", 4)
    ROBOT_STATUS = ("robot_status", 5)
    SELF_CHECK_STATUS = ("self_check_status", 6)
    SLAM_STATUS = ("slam_status", 7)
    NAVIGATION_STATUS = ("navigation_status", 8)
    CLEAR_MAP_DIFF = ("clear_map_diff", 9)
    MAP_UPDATE = ("map_update", 10)
    WATCHDOG_UPDATE_RESULT = ("watchdog_update_result", 11)
    SYSUPD_RESULT = ("sysupd_result", 12)
    FACTORY_RESET = ("factory_reset", 13)
    CLEAR_INC_POSES = ("clear_inc_poses", 14)
    REMOTE_MODE_INFO = ("remote_mode_info", 15)
    ROBOT_ERROR = ("robot_error", 16)
    RECORD_MOW_TRAJECTORY = ("record_mow_trajectory", 17)
    UNRECORD_MOW_TRAJECTORY = ("unrecord_mow_trajectory", 18)
    CLEAR_MOW_TRAJECTORY = ("clear_mow_trajectory", 19)
    MOW_RECORD = ("mow_record", 20)
    MOW_PROGRESS = ("mow_progress", 21)
    ALL_MOW_RECORDERS = ("all_mow_recorders", 22)
    DEBUG_PARAMETER = ("debug_parameter", 23)
    MOW_PREFERENCE_CONFIG = ("mow_preference_config", 24)
    USER_MODE_CONFIG = ("user_mode_config", 25)
    CURRENT_MOW_RECORDER = ("current_mow_recorder", 26)
    POPUP = ("popup", 27)
    FEATURESET = ("featureset", 28)
    RECORD_SNAPSHOT_MAP = ("record_snapshot_map", 29)
    HEIGHT_MOTOR_PARAMETER = ("height_motor_parameter", 30)
    DP_POINTS = ("dp_points", 31)
    PUSH_NOTIFICATION = ("push_notification", 32)
    LORA_PAIR_RESULT = ("lora_pair_result", 33)
    MOW_SCHEDULE = ("mow_schedule", 34)
    ROBOT_TIME_ZONE = ("robot_time_zone", 35)
    BIT_RESULTS = ("bit_results", 36)
    BLACK_BOX_RESULTS = ("black_box_results", 37)
    ROBOT_STATUS_UPDATE = ("robot_status_update", 38)
    MAP_SELF_CHECK_RESULT = ("map_self_check_result", 39)
    ROBOT_GPS_UPLOAD = ("robot_gps_upload", 40)
    MMT_RESULTS = ("mmt_results", 41)
    SKU_INFO = ("sku_info", 42)
    BIT_HISTORY = ("bit_history", 43)
    MMT_ABNORMAL_EXIT = ("mmt_abnormal_exit", 44)
    SW_VERSION = ("sw_version", 45)
    RESTART_BIT_RESULTS = ("restart_bit_results", 46)
    BIT_CHECK_LISTS = ("bit_check_lists", 47)
    REMOTE_MOW_SELF_CHECK_RESULT = ("remote_mow_self_check_result", 48)
    MCU_VERSION = ("mcu_version", 49)
    PROJECT = ("project", 50)
    BROADCAST_FSM_EVENT = ("broadcast_fsm_event", 51)
    ROBOT_INFO = ("robot_info", 52)
    ROBOT_NETWORK_INFO = ("robot_network_info", 53)
    ROBOT_BLUETOOTH_INFO = ("robot_bluetooth_info", 54)
    ESIM_ACTIVE_STATUS = ("esim_active_status", 55)
    ESIM_ACTIVE_RESULT = ("esim_active_result", 56)
    ESIM_INFO = ("esim_info", 57)
    SKU_CONFIG = ("sku_config", 58)
    AFS_CALIBRATION_RES = ("afs_calibration_res", 59)
    MOWING_ZONES = ("mowing_zones", 60)
    QUERY_BOARD_SN_RES = ("query_board_sn_res", 61)
    SPARE_BOARD_SN_RES = ("spare_board_sn_res", 62)
    MAP_CREATE_FAIL = ("map_create_fail", 63)
    FEATURE_INFO = ("feature_info", 64)
    MIDNIGHT_RESET_TO_APP_PROXY = ("midnight_reset_to_app_proxy", 65)
    ROBOT_BUMPER_ACTIVE_ONCE = ("robot_bumper_active_once", 66)
    SERIAL_NUMBER = ("serial_number", 67)
    INIT_STATUS = ("init_status", 68)
    CURRENT_SOUND = ("current_sound", 69)
    DNLD_INSTALL_SOUND_RESULT = ("dnld_install_sound_result", 70)
    SOUND_PROGRESS = ("sound_progress", 71)
    WIFI_LIST = ("wifi_list", 72)
    LOCAL_INFO = ("local_info", 73)
    APP_RESPONSE_ERROR = ("app_response_error", 74)
    INSTALLATION_WIZARD = ("installation_wizard", 75)
    TEST_ID = ("test_id", 76)
    ZONES_PLAN_INFO = ("zones_plan_info", 77)
    MAP_CREATE_STATE = ("map_create_state", 78)
    BATTERY_PERCENT = ("battery_percent", 79)
    FAULT_RECORDS = ("fault_records", 80)
    MAP_ABSTRACTS = ("map_abstracts", 81)
    SET_SERVO_CALIB = ("set_servo_calib", 82)
    MAINTENANCE_STATUS = ("maintenance_status", 83)
    RESET_MAINTENANCE = ("reset_maintenance", 84)
    MOW_TRAJECTORY_EVENT = ("mow_trajectory_event", 85)
    AFS_LINE_DIFF_CHECK_RES = ("afs_line_diff_check_res", 86)
    AFS_LINE_DIFF_CALIBRATION_RES = ("afs_line_diff_calibration_res", 87)
    LOG_LTE_EVENTS = ("log_lte_events", 88)
    LOG_LTE_UPLOAD_INFO = ("log_lte_upload_info", 89)
    LORA_CONFIG_RESULT = ("lora_config_result", 90)
    ROBO_EMC_MODE_REQUEST = ("robo_emc_mode_request", 91)
    ROBO_EMC_DEVICE_INFO = ("robo_emc_device_info", 92)
    RTK_DEVICE_TYPE = ("rtk_device_type", 93)
    SWITCH_LTE_RESULT = ("switch_lte_result", 94)
    NRTK_REQUEST = ("nrtk_request", 95)
    NRTK_RETURN = ("nrtk_return", 96)
    NRTK_SYNCHRONIZATION = ("nrtk_synchronization", 97)
    RTK_MODE = ("rtk_mode", 98)
    NRTK_MSG_TO_APP = ("nrtk_msg_to_app", 99)
    DOCK_LIST_INFO = ("dock_list_info", 100)
    DOCK_PAIR_INFO = ("dock_pair_info", 101)
    DOCK_PAIRED_STATUS = ("dock_paired_status", 102)
    SET_DOCK_CHARGING_TYPE = ("set_dock_charging_type", 103)
    REALTIME_VIDEO = ("realtime_video", 104)
    PANORAMA_MAP_ABSTRACTS = ("panorama_map_abstracts", 105)
    MAP_TRAJECTORY_EVENT = ("map_trajectory_event", 106)
    LIFT_ALARM_ENABLE = ("lift_alarm_enable", 107)
    DOCK_LORA_CONFIG_RESULT = ("dock_lora_config_result", 108)
    NRTK_SEND = ("nrtk_send", 109)
    NRTK_RECYCLE = ("nrtk_recycle", 110)
    CHILD_LOCK_ENABLE = ("child_lock_enable", 111)
    S1G_INFO_LIST = ("s1g_info_list", 120)
    S1G_SCAN_WIFI_LIST = ("s1g_scan_wifi_list", 121)
    S1G_PAIR_STATUS = ("s1g_pair_status", 122)


class MowerAppButton(MowerEnum):
    """Button sent with `RemoteMsg.type = APP_BUTTON` (`rock.common.remote.AppButton.Type`)."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    START = ("start", 1)
    PAUSE = ("pause", 2)
    STOP = ("stop", 3)
    RESUME = ("resume", 4)
    CHARGE = ("charge", 5)
    CREATE_MAP = ("create_map", 6)
    RESUME_CREATE_MAP = ("resume_create_map", 7)
    TO_CLOSE = ("to_close", 8)
    ERASE = ("erase", 9)
    EXIT_MAPPING_PAGE = ("exit_mapping_page", 10)
    BUILD_BOUNDARY = ("build_boundary", 11)
    BUILD_ISLAND = ("build_island", 12)
    BUILD_PATH = ("build_path", 13)
    MOW_GLOBAL = ("mow_global", 14)
    MOW_EDGE = ("mow_edge", 15)
    MOW_SELECT = ("mow_select", 16)
    DOCK_START = ("dock_start", 17)
    SAVE_MAP = ("save_map", 18)
    MAP_PAUSE = ("map_pause", 19)
    MOW_PAUSE = ("mow_pause", 20)
    MAP_RESUME = ("map_resume", 21)
    MOW_RESUME = ("mow_resume", 22)
    MAP_END = ("map_end", 23)
    MOW_END = ("mow_end", 24)
    DOCK_END = ("dock_end", 25)
    PREPARE_BUILD_PATH = ("prepare_build_path", 26)
    BUILD_BOUNDARY_AUTO = ("build_boundary_auto", 27)
    PREPARE_BUILD_BOUNDARY = ("prepare_build_boundary", 28)
    PREPARE_BUILD_ISLAND = ("prepare_build_island", 29)
    MAP_EDIT_ENTER = ("map_edit_enter", 30)
    MAP_EDIT_EXIT = ("map_edit_exit", 31)
    MAP_TERMINATE = ("map_terminate", 32)
    STOP_BIT_TASK = ("stop_bit_task", 33)
    ANTI_THEFT_ENABLE = ("anti_theft_enable", 34)
    ANTI_THEFT_DISABLE = ("anti_theft_disable", 35)
    STOP_MMT_TASK = ("stop_mmt_task", 36)
    TRIGGER_MIDNIGHT_RESET_ONCE = ("trigger_midnight_reset_once", 37)
    STOP_AFS_CALIBRATION_TASK = ("stop_afs_calibration_task", 38)
    CLEAR_ERROR = ("clear_error", 39)
    CHARGE_WITH_NORMAL_MOW_RESERVE = ("charge_with_normal_mow_reserve", 40)
    CHARGE_WITH_PLAN_MOW_RESERVE = ("charge_with_plan_mow_reserve", 41)
    RESUME_PREPARE_BUILD = ("resume_prepare_build", 42)
    MOW_AUTO_TO_REMOTE = ("mow_auto_to_remote", 43)
    DP_CHARGE = ("dp_charge", 44)
    CLEAR_ONLY_APP_ERROR = ("clear_only_app_error", 45)
    # The protocol spelling "ClEAR_ROBOT_AND_APP_ERROR" is intentional.
    CLEAR_ROBOT_AND_APP_ERROR = ("clear_robot_and_app_error", 46)
    ERROR_RETRY = ("error_retry", 47)
    CLEAR_MAP_KEY = ("clear_map_key", 48)
    TO_DOCK_FAULT_CHARGE = ("to_dock_fault_charge", 49)
    RESET_UNDOCK = ("reset_undock", 50)
    BUILD_NO_AVOID = ("build_no_avoid", 51)
    PREPARE_BUILD_NO_AVOID = ("prepare_build_no_avoid", 52)
    RESET_PASSAGE = ("reset_passage", 53)
    PREPARE_RESET_PASSAGE = ("prepare_reset_passage", 54)
    EDIT_BOUNDARY = ("edit_boundary", 55)
    PREPARE_EDIT_BOUNDARY = ("prepare_edit_boundary", 56)
    CONFIRM_EDIT_BOUNDARY = ("confirm_edit_boundary", 57)
    HUMAN_BIT_DONE = ("human_bit_done", 100)
    SCREEN_CHECK_PASS = ("screen_check_pass", 101)
    SCREEN_CHECK_FAILED = ("screen_check_failed", 102)
    GET_BIT_CHECK_INFOS = ("get_bit_check_infos", 103)
    SERVO_CALIB_START = ("servo_calib_start", 104)
    SERVO_START_VALIDATION = ("servo_start_validation", 105)
    SERVO_MOVE_LEFT_45 = ("servo_move_left_45", 106)
    SERVO_MOVE_RIGHT_45 = ("servo_move_right_45", 107)
    SERVO_RESET_0 = ("servo_reset_0", 108)
    SERVO_END_CALIBRATION = ("servo_end_calibration", 109)
    START_AFS_LINE_DIFF_CHECK = ("start_afs_line_diff_check", 110)
    STOP_AFS_LINE_DIFF_CHECK = ("stop_afs_line_diff_check", 111)
    START_AFS_LINE_DIFF_CALIBRATION = ("start_afs_line_diff_calibration", 112)
    STOP_AFS_LINE_DIFF_CALIBRATION = ("stop_afs_line_diff_calibration", 113)
    RETURN_TO_RUNTIME_MENU = ("return_to_runtime_menu", 114)
    DETECT_CHARGE_STATION = ("detect_charge_station", 115)


class MowerFsmEvent(MowerEnum):
    """Mapping-preparation events for `button_with_map_selfcheck_result`."""

    UNKNOWN = ("unknown", -1)
    APP_BUTTON_START = ("app_button_start", 301)
    APP_BUTTON_PAUSE = ("app_button_pause", 302)
    APP_BUTTON_STOP = ("app_button_stop", 303)
    APP_BUTTON_RESUME = ("app_button_resume", 304)
    APP_BUTTON_CHARGE = ("app_button_charge", 305)
    APP_BUTTON_CREATE_MAP = ("app_button_create_map", 306)
    APP_BUTTON_RESUME_CREATE_MAP = ("app_button_resume_create_map", 307)
    APP_BUTTON_TO_CLOSE = ("app_button_to_close", 308)
    APP_BUTTON_ERASE = ("app_button_erase", 309)
    APP_BUTTON_EXIT_MAPPING_PAGE = ("app_button_exit_mapping_page", 310)
    APP_BUTTON_BUILD_BOUNDARY = ("app_button_build_boundary", 311)
    APP_BUTTON_BUILD_ISLAND = ("app_button_build_island", 312)
    APP_BUTTON_BUILD_PATH = ("app_button_build_path", 313)
    APP_BUTTON_MOW_GLOBAL = ("app_button_mow_global", 314)
    APP_BUTTON_MOW_EDGE = ("app_button_mow_edge", 315)
    APP_BUTTON_MOW_SELECT = ("app_button_mow_select", 316)
    APP_BUTTON_DOCK_START = ("app_button_dock_start", 317)
    APP_BUTTON_SAVE_MAP = ("app_button_save_map", 318)
    APP_BUTTON_MAP_PAUSE = ("app_button_map_pause", 319)
    APP_BUTTON_MOW_PAUSE = ("app_button_mow_pause", 320)
    APP_BUTTON_MAP_RESUME = ("app_button_map_resume", 321)
    APP_BUTTON_MOW_RESUME = ("app_button_mow_resume", 322)
    APP_BUTTON_MAP_END = ("app_button_map_end", 323)
    APP_BUTTON_MOW_END = ("app_button_mow_end", 324)
    APP_BUTTON_DOCK_END = ("app_button_dock_end", 325)
    APP_BUTTON_PREPARE_BUILD_PATH = ("app_button_prepare_build_path", 326)
    APP_BUTTON_BUILD_BOUNDARY_AUTO = ("app_button_build_boundary_auto", 327)
    APP_BUTTON_PREPARE_BUILD_BOUNDARY = ("app_button_prepare_build_boundary", 328)
    APP_BUTTON_PREPARE_BUILD_ISLAND = ("app_button_prepare_build_island", 329)
    APP_BUTTON_MAP_EDIT_ENTER = ("app_button_map_edit_enter", 330)
    APP_BUTTON_MAP_EDIT_EXIT = ("app_button_map_edit_exit", 331)
    APP_BUTTON_MAP_TERMINATE = ("app_button_map_terminate", 332)
    APP_BUTTON_STOP_BIT_TASK = ("app_button_stop_bit_task", 333)
    APP_BUTTON_ANTI_THEFT_ENABLE = ("app_button_anti_theft_enable", 334)
    APP_BUTTON_ANTI_THEFT_DISABLE = ("app_button_anti_theft_disable", 335)
    APP_BUTTON_STOP_MMT_TASK = ("app_button_stop_mmt_task", 336)
    APP_BUTTON_TRIGGER_MIDNIGHT_RESET_ONCE = ("app_button_trigger_midnight_reset_once", 337)
    APP_BUTTON_STOP_AFS_CALIBRATION_TASK = ("app_button_stop_afs_calibration_task", 338)
    APP_BUTTON_CLEAR_ERROR = ("app_button_clear_error", 339)
    APP_BUTTON_CHARGE_WITH_NORMAL_MOW_RESERVE = ("app_button_charge_with_normal_mow_reserve", 340)
    APP_BUTTON_CHARGE_WITH_PLAN_MOW_RESERVE = ("app_button_charge_with_plan_mow_reserve", 341)
    APP_BUTTON_RESUME_PREPARE_BUILD = ("app_button_resume_prepare_build", 342)
    APP_BUTTON_DP_CHARGE = ("app_button_dp_charge", 343)
    APP_BUTTON_TO_DOCK_FAULT_CHARGE = ("app_button_to_dock_fault_charge", 344)
    APP_BUTTON_STOP_AFS_LINE_DIFF_CALIBRATION_TASK = ("app_button_stop_afs_line_diff_calibration_task", 345)
    APP_BUTTON_RETURN_TO_RUNTIME_MENU_AFS = ("app_button_return_to_runtime_menu_afs", 346)
    APP_BUTTON_RESET_UNDOCK = ("app_button_reset_undock", 347)
    APP_BUTTON_BUILD_NO_AVOID = ("app_button_build_no_avoid", 348)
    APP_BUTTON_PREPARE_BUILD_NO_AVOID = ("app_button_prepare_build_no_avoid", 349)
    APP_BUTTON_RESET_PASSAGE = ("app_button_reset_passage", 350)
    APP_BUTTON_PREPARE_RESET_PASSAGE = ("app_button_prepare_reset_passage", 351)
    APP_BUTTON_EDIT_BOUNDARY = ("app_button_edit_boundary", 352)
    APP_BUTTON_PREPARE_EDIT_BOUNDARY = ("app_button_prepare_edit_boundary", 353)
    APP_BUTTON_CONFIRM_EDIT_BOUNDARY = ("app_button_confirm_edit_boundary", 354)


class MowerFsmState(MowerEnum):
    """Task-machine state (`rock.fsm.FsmState.Type`)."""

    UNKNOWN = ("unknown", 0)
    IDLE = ("idle", 1)
    FAULT = ("fault", 2)
    SUSPEND = ("suspend", 3)
    CHARGING = ("charging", 4)
    CHARGE_COMPLETED = ("charge_completed", 5)
    CHARGE_WAITING = ("charge_waiting", 6)
    RETURN = ("return", 7)
    DOWNLOADING = ("downloading", 8)
    INSTALLING = ("installing", 9)
    REBOOTING = ("rebooting", 10)
    GOTO_TARGET = ("goto_target", 11)
    BUILDING_BOUNDARY = ("building_boundary", 12)
    BUILDING_ISLAND = ("building_island", 13)
    BUILDING_PATH = ("building_path", 14)
    SAVE = ("save", 15)
    ERASING = ("erasing", 16)
    SWITCH_SCENES = ("switch_scenes", 17)
    MOW_GLOBAL = ("mow_global", 18)
    MOW_EDGE = ("mow_edge", 19)
    MOW_SELECT = ("mow_select", 20)
    AT = ("at", 21)
    STANDBY = ("standby", 22)
    RUN = ("run", 23)
    EMERGENCY_STOP = ("emergency_stop", 24)


class MowerAckResult(MowerEnum):
    """Request acceptance result (`rock.common.Ack.Type`)."""

    UNKNOWN = ("unknown", -1)
    OK = ("ok", 0)
    FAIL = ("fail", 1)


class MowerPreferenceEffective(MowerEnum):
    """Mowing-efficiency preference (`MowPreference.Effective`)."""

    UNKNOWN = ("unknown", 0)
    DAILY = ("daily", 1)
    EFFICIENT = ("efficient", 2)
    MANICURE = ("manicure", 3)
    CUSTOM_MOW = ("custom_mow", 4)


class MowerDirectionType(MowerEnum):
    """Mowing direction mode (`MowPreference.DirectionType`)."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    CUSTOM = ("custom", 1)
    NAV_EFFICIENT = ("nav_efficient", 2)
    AUTO_DEFLECTION = ("auto_deflection", 3)


class MowerBoundaryPerception(MowerEnum):
    """Boundary perception preference (`MowPreference.BoundaryPerception`)."""

    UNKNOWN = ("unknown_bp", 0)
    STANDARD = ("standard", 1)
    INTELLIGENCE = ("intelligence", 2)


class MowerPreferenceMode(MowerEnum):
    """Preference scope used by preferences, configs and plans."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    GLOBAL = ("global", 1)
    CUSTOM = ("custom", 2)


class MowerPlanType(MowerEnum):
    """Schedule plan recurrence (`MowingPlan.Type`)."""

    UNKNOWN = ("unknown", -1)
    NONE = ("none", 0)
    ONE_TIME = ("one_time", 1)
    WEEKLY = ("weekly", 2)


class MowerPlanStatus(MowerEnum):
    """Schedule plan status (`MowingPlan.Status`)."""

    UNKNOWN = ("unknown", 0)
    OPEN = ("open", 1)
    CLOSE = ("close", 2)
    INVALID = ("invalid", 3)


class MowerWeekday(MowerEnum):
    """Weekday for weekly plans (`rock.common.Week.Type`), Sunday first."""

    UNKNOWN = ("unknown", -1)
    SUNDAY = ("sunday", 0)
    MONDAY = ("monday", 1)
    TUESDAY = ("tuesday", 2)
    WEDNESDAY = ("wednesday", 3)
    THURSDAY = ("thursday", 4)
    FRIDAY = ("friday", 5)
    SATURDAY = ("saturday", 6)


class MowerRainType(MowerEnum):
    """Reported rain intensity (`rock.common.RainFall.Type`)."""

    UNKNOWN = ("unknown", 0)
    RAIN_NO = ("rain_no", 1)
    RAIN_LOW = ("rain_low", 2)
    RAIN_MID = ("rain_mid", 3)
    RAIN_HIGH = ("rain_high", 4)


class MowerNavSolution(MowerEnum):
    """Positioning hardware (`rock.common.NavFeature.Solution`)."""

    UNKNOWN = ("unknown_solution", 0)
    RTK_VISION = ("rtk_vision", 1)
    LIDAR_VISION = ("lidar_vision", 2)


class MowerDriveMode(MowerEnum):
    """Drive train (`rock.common.DriveFeature.Mode`)."""

    UNKNOWN = ("unknown_mode", 0)
    TWO_WHEEL_DRIVE = ("two_wheel_drive", 1)
    FOUR_WHEEL_DRIVE = ("four_wheel_drive", 2)


class MowerMobile4GMode(MowerEnum):
    """Cellular hardware (`rock.common.Mobile4GFeature.Mode`)."""

    UNKNOWN = ("unknown_mode", 0)
    INTERNAL_ESIM = ("internal_esim", 1)
    EXTERNAL_ESIM = ("external_esim", 2)


class MowerSkuRegion(MowerEnum):
    """Market region (`rock.common.SkuInfo.Region`)."""

    UNKNOWN = ("unknown_region", 0)
    US = ("us", 1)
    EU = ("eu", 2)


class MowerStartDpType(MowerEnum):
    """Structured start request type (`rock.iot.StartDpValue.Type`)."""

    UNKNOWN = ("unknown", 0)
    GLOBAL = ("global", 1)
    SELECTION_WITH_ID = ("selection_with_id", 2)
    EDGE_WITH_ID = ("edge_with_id", 3)
    ZONING_WITH_PARAMS = ("zoning_with_params", 4)


class MowerFeature(MowerEnum):
    """Capability bit positions in `FeatureSet.details` (`rock.common.FeatureSet.Type`)."""

    UNKNOWN = ("unknown", -1)
    RTK = ("rtk", 0)
    LIDAR = ("lidar", 1)
    HEIGHT_MOTOR = ("height_motor", 2)
    FOUR_WHEELS_DRIVE = ("four_wheels_drive", 3)
    SIGN_LED = ("sign_led", 4)
    FEATURESET_NEW = ("featureset_new", 6)
    LTE_LOG = ("lte_log", 7)
    AFS_LINE_DIFF_CALIBRATION = ("afs_line_diff_calibration", 8)
    PREFERENCE_AUTO_DEFLECTION = ("preference_auto_deflection", 9)
    EXHIBITION = ("exhibition", 10)
    MAP_RENAME = ("map_rename", 11)
    LORA_LOGIC_OPTIMIZATION = ("lora_logic_optimization", 12)
    RESET_UNDOCK = ("reset_undock", 13)
    SUPPORT_SIM = ("support_sim", 14)
    REMOTE_EDGE_CUTTER = ("remote_edge_cutter", 15)
    NO_AVOID = ("no_avoid", 16)
    RGB_MOWER = ("rgb_mower", 17)
    GRASS_ROPE = ("grass_rope", 18)
    NRTK_MODE = ("nrtk_mode", 19)
    DOCK_NRTK_MODE = ("dock_nrtk_mode", 20)
    DOCK_WIFI = ("dock_wifi", 21)
    REALTIME_VIDEO = ("realtime_video", 22)
    LIVING_OBSTACLE = ("living_obstacle", 23)
    EDGE_VISION_AVOID = ("edge_vision_avoid", 24)
    DOCK_WIFI_LORA = ("dock_wifi_lora", 25)
    OBS_IMAGE = ("obs_image", 26)
    PANORAMA = ("panorama", 27)
    LIFT_AND_SAFETY_LOCK = ("lift_and_safety_lock", 28)
    CHILD_LOCKED = ("child_locked", 29)
    RESET_PASSAGE = ("reset_passage", 30)
    REMOTE_DOUBLE_AXIS_JOYSTICK = ("remote_double_axis_joystick", 31)
    BOUNDARY_TYPE = ("boundary_type", 32)
    S1G = ("s1g", 33)
    EDIT_BOUNDARY = ("edit_boundary", 34)
    NETWORK_INFO_V1 = ("network_info_v1", 35)
    STATIC_OBSTACLE = ("static_obstacle", 36)


class MowerMcuType(MowerEnum):
    """Controller identity in MCU version reports (`rock.common.McuType.Type`)."""

    UNKNOWN = ("unknown", -1)
    MAIN_MCU = ("main_mcu", 0)
    REAR_DRV_MCU = ("rear_drv_mcu", 1)
    BORDER_DRV_MCU = ("border_drv_mcu", 2)
    MOVE_STATION_MCU = ("move_station_mcu", 4)
    MOVE_STATION_RTK = ("move_station_rtk", 5)
    MOVE_STATION_LORA = ("move_station_lora", 6)
    BASE_STATION_MCU = ("base_station_mcu", 7)
    BASE_STATION_RTK = ("base_station_rtk", 8)
    BASE_STATION_LORA = ("base_station_lora", 9)
    FRONT_DRV_MCU = ("front_drv_mcu", 10)
    FRONT_STEER_MCU = ("front_steer_mcu", 11)
    FRONT_LEFT_DRIVE_MCU = ("front_left_drive_mcu", 14)
    FRONT_LEFT_STEER_MCU = ("front_left_steer_mcu", 15)
    FRONT_RIGHT_DRIVE_MCU = ("front_right_drive_mcu", 16)
    FRONT_RIGHT_STEER_MCU = ("front_right_steer_mcu", 17)
    REAR_LEFT_DRIVE_MCU = ("rear_left_drive_mcu", 18)
    REAR_RIGHT_DRIVE_MCU = ("rear_right_drive_mcu", 19)
    TRIM0_MCU = ("trim0_mcu", 20)
    TRIM1_MCU = ("trim1_mcu", 21)


class MowerRtkMode(MowerEnum):
    """RTK correction mode (`rock.common.RtkMode.Mode`)."""

    UNKNOWN = ("unknown", -1)
    DEFAULT = ("default", 0)
    BASE_RTK = ("base_rtk", 1)
    BASE_NRTK = ("base_nrtk", 2)
    DOCK_NRTK = ("dock_nrtk", 3)
    AUTO_NRTK = ("auto_nrtk", 4)

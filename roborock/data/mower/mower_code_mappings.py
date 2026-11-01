"""Code mappings for Roborock mower devices."""

from typing import Self, cast

from roborock.data.code_mappings import RoborockModeEnum

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
]


class MowerEnum(RoborockModeEnum):
    """Base for mower enums."""

    @classmethod
    def from_code(cls, code: int | str) -> Self:
        """Resolve a wire value by name, string value, or integer code."""
        if (member := cls.from_any_optional(code)) is not None:
            return member
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

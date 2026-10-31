"""Code mappings for Roborock mower devices.

Status data points carry integer values, while structured ``remote_pb`` JSON
replies use protobuf enum names. The compact mowing state and detailed robot
task state are separate numeric domains and must not be interchanged.

The new enums are :class:`RoborockModeEnum` classes whose string value is the
protobuf enum name and whose ``code`` is the integer wire value. The existing
integer-valued :class:`RoborockMowerStateCode` remains available for callers
using its original names and values.

Enums whose protocol domain has no unknown value additionally define a
synthetic ``UNKNOWN = ("UNKNOWN", -1)`` member. It is never sent on the wire;
:meth:`MowerEnum.from_code` resolves unrecognized firmware values to it so
consumers always see an explicit unknown rather than a stale or missing value.
"""

from typing import Self, cast

from roborock.data.code_mappings import RoborockEnum, RoborockModeEnum

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
    "RoborockMowerStateCode",
]


class RoborockMowerStateCode(RoborockEnum):
    """Legacy detailed state codes, retained with their original names and values."""

    unknown = -999
    idle = 0

    map_initializing = 1
    map_undocking = 2
    map_undock_fault = 3
    map_locating = 4
    map_prepare_boundary = 5
    map_prepare_island = 6
    map_prepare_path = 7
    map_boundary = 8
    map_island = 9
    map_path = 10
    map_boundary_auto = 11
    map_erasing = 12
    map_save = 13
    map_wait = 14
    map_recoverable_fault = 15
    map_fault = 16
    map_emergency_stop = 17
    map_waiting_fault = 18

    mow_initializing = 51
    mow_undocking = 52
    mow_locating = 53
    mow_adjust_cutter = 54
    mow_zig_zag = 55
    mow_edge = 56
    mow_goto = 57
    mow_suspend = 58
    mow_recoverable_fault = 59
    mow_fault = 60
    mow_docked_rainfall = 61
    mow_docked_do_not_disturb = 62
    mow_docked_low_battery = 63
    mow_wait = 64
    mow_prepare_remote = 65
    mow_remote = 66
    mow_emergency_stop = 67
    mow_docked_manual = 68
    mow_dock_fault = 69
    mow_remote_undocking = 70
    mow_to_dock_initializing = 71
    mow_to_dock_locating = 72
    mow_to_dock_recoverable_fault = 73
    mow_to_dock_fault = 74
    mow_to_dock_emergency_stop = 75
    mow_to_dock_charging = 76
    mow_to_dock_charge_completed = 77

    free = 101
    free_initializing = 102
    free_locating = 103
    free_docked_manual = 104
    free_docked_mow_end = 105
    free_docked_plan_end = 106
    free_emergency_stop = 107
    free_recoverable_fault = 108
    free_fault = 109

    charge_charging = 151
    charge_completed = 152
    charge_waiting = 153
    charge_fault = 154


class MowerEnum(RoborockModeEnum):
    """Base for mower enums parsed from the JSON route.

    Wire data carries the protobuf member name (``"DAILY"``), occasionally the
    integer code, or the code as a decimal string. ``from_code`` accepts all
    three so model fields parse through the standard conversion path, and it
    maps unrecognized values to the enum's unknown member when it has one (the
    member whose name starts with ``UNKNOWN`` and whose code is zero or
    negative), following the Q7 ``WorkStatusMapping`` precedent.
    """

    @classmethod
    def from_code(cls, code: int | str) -> Self:
        """Resolve a wire value by name, string value, or integer code."""
        if (member := cls.from_any_optional(code)) is not None:
            return member
        return cast(Self, cls.UNKNOWN)  # type: ignore[attr-defined]


class MowerMowType(MowerEnum):
    """Mowing task selection reported by DPS 122 (``MowTypeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    NONE = ("NONE", 0)
    GLOBAL = ("GLOBAL", 1)
    EDGE = ("EDGE", 2)
    SELECTION = ("SELECTION", 3)
    ZONING = ("ZONING", 4)
    REMOTE = ("REMOTE", 5)
    RANDOM = ("RANDOM", 6)


class MowerMowState(MowerEnum):
    """Compact mowing state (``MowStateDpValue.Type``).

    This is the documented compact domain for DPS 123. Live captures report the
    detailed :class:`MowerDetailState` on that data point instead, which is why
    ``MowerStatus.mow_state`` uses the detailed enum; this enum remains for the
    structured ``dp_points`` payloads that carry ``mow_state.type``.
    """

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    ZIGZAG_MOWING = ("ZIGZAG_MOWING", 1)
    EDGE_MOWING = ("EDGE_MOWING", 2)
    TRANSITION = ("TRANSITION", 3)
    SUSPENDED = ("SUSPENDED", 4)
    REMOTE_WALKING = ("REMOTE_WALKING", 5)
    REMOTE_MOWING = ("REMOTE_MOWING", 6)


class MowerMappingType(MowerEnum):
    """Mapping operation reported by DPS 124 (``MappingTypeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    NONE = ("NONE", 0)
    LAWN_MAPPING = ("LAWN_MAPPING", 1)
    FORBIDDEN_ZONE_MAPPING = ("FORBIDDEN_ZONE_MAPPING", 2)
    CHANNEL_MAPPING = ("CHANNEL_MAPPING", 3)
    SPLIT_WORKSPACE = ("SPLIT_WORKSPACE", 4)
    MERGE_WORKSPACE = ("MERGE_WORKSPACE", 5)
    BOUNDARY_MODIFY = ("BOUNDARY_MODIFY", 6)


class MowerMappingState(MowerEnum):
    """Mapping activity reported by DPS 125 (``MappingStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    AUTO_MAPPING = ("AUTO_MAPPING", 1)
    TRACK_ERASE = ("TRACK_ERASE", 2)
    SUSPENDED = ("SUSPENDED", 3)
    SAVING_MAP = ("SAVING_MAP", 4)
    REMOTE_WALKING = ("REMOTE_WALKING", 5)
    REMOTE_MAPPING = ("REMOTE_MAPPING", 6)


class MowerOtaState(MowerEnum):
    """Firmware update state reported by DPS 126 (``OtaStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    DOWNLOADING = ("DOWNLOADING", 1)
    INSTALLING = ("INSTALLING", 2)
    REBOOTING = ("REBOOTING", 3)


class MowerChargeState(MowerEnum):
    """Charging state reported by DPS 127 (``ChargeStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    NOT_CHARGING = ("NOT_CHARGING", 0)
    CHARGING = ("CHARGING", 1)
    CHARGE_COMPLETED = ("CHARGE_COMPLETED", 2)
    WAITING_CHARGE = ("WAITING_CHARGE", 3)
    LOW_POWER = ("LOW_POWER", 4)
    CHARGE_ERROR = ("CHARGE_ERROR", 5)


class MowerDockState(MowerEnum):
    """Return-to-dock state reported by DPS 128 (``DockStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    MOVING_TO_TARGET = ("MOVING_TO_TARGET", 1)
    DOCKING = ("DOCKING", 2)
    SUSPENDED = ("SUSPENDED", 3)


class MowerChargeType(MowerEnum):
    """Why the mower returned to charge, DPS 129 (``ChargeTypeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", 0)
    MANUAL_DOCK = ("MANUAL_DOCK", 1)
    RAIN_DOCK = ("RAIN_DOCK", 2)
    DO_NOT_DISTURB_DOCK = ("DO_NOT_DISTURB_DOCK", 3)
    STANDBY_TIMEOUT_DOCK = ("STANDBY_TIMEOUT_DOCK", 4)
    LOW_BATTERY_DOCK = ("LOW_BATTERY_DOCK", 5)
    TASK_FINISHED_DOCK = ("TASK_FINISHED_DOCK", 6)
    MOW_FAULT_DOCK = ("MOW_FAULT_DOCK", 7)


class MowerPendType(MowerEnum):
    """Pause or interruption reason, DPS 130 (``PendTypeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    NOT_SUSPENDED = ("NOT_SUSPENDED", 0)
    APP_PAUSE = ("APP_PAUSE", 1)
    BUTTON_EMERGENCY_STOP = ("BUTTON_EMERGENCY_STOP", 2)
    FAULT = ("FAULT", 3)
    BREAKPOINT_PAUSE = ("BREAKPOINT_PAUSE", 4)
    OTHER = ("OTHER", 5)


class MowerRemoteState(MowerEnum):
    """Remote control state, DPS 131 (``RemoteStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    VIDEO_REMOTE = ("VIDEO_REMOTE", 1)
    REMOTE_WALKING = ("REMOTE_WALKING", 2)


class MowerStartType(MowerEnum):
    """How the current task was started, DPS 132 (``MowStartTypeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    DEFAULT = ("DEFAULT", 0)
    APP_START = ("APP_START", 1)
    BUTTON_START = ("BUTTON_START", 2)
    SCHEDULE_START = ("SCHEDULE_START", 3)


class MowerEffMode(MowerEnum):
    """Reported efficiency mode, DPS 133 (``MowEffModeDpValue.Type``).

    This is not the same enumeration as the ``effective`` preference setting.
    """

    UNKNOWN = ("UNKNOWN", 0)
    DAILY = ("DAILY", 1)
    PRECISE = ("PRECISE", 2)
    FAST = ("FAST", 3)


class MowerPattern(MowerEnum):
    """Reported mowing pattern, DPS 136 (``MowPattenDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", 0)
    ZIGZAG = ("ZIGZAG", 1)
    WELL = ("WELL", 2)
    DIAMOND = ("DIAMOND", 3)
    TRIANGLE = ("TRIANGLE", 4)
    AUTO_DEFLECT = ("AUTO_DEFLECT", 5)
    RANDOM = ("RANDOM", 6)


class MowerConfMode(MowerEnum):
    """Preference configuration scope, DPS 137 (``MowConfModeDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", 0)
    GLOBAL_CONFIG = ("GLOBAL_CONFIG", 1)
    ZONE_CUSTOM = ("ZONE_CUSTOM", 2)


class MowerOfflineStatus(MowerEnum):
    """Shutdown or reboot reason, DPS 138 (``OfflineStatusDpValue.Type``).

    This is not a reliable live connectivity flag by itself.
    """

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    ONLINE = ("ONLINE", 0)
    MANUAL_SHUTDOWN = ("MANUAL_SHUTDOWN", 1)
    SLEEP_SHUTDOWN = ("SLEEP_SHUTDOWN", 2)
    LOW_BATTERY_SHUTDOWN = ("LOW_BATTERY_SHUTDOWN", 3)
    UPGRADE_REBOOT = ("UPGRADE_REBOOT", 4)


class MowerFcState(MowerEnum):
    """Factory or test mode indicator, DPS 141 (``FcStateDpValue.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    NOT_FC = ("NOT_FC", 0)
    FC = ("FC", 1)


class MowerOffDockNoTaskStatus(MowerEnum):
    """Mower away from the dock without an active task, DPS 143."""

    UNKNOWN = ("UNKNOWN", 0)
    WAITING = ("WAITING", 1)
    SUSPENDING = ("SUSPENDING", 2)
    DOCKING = ("DOCKING", 3)
    REMOTING = ("REMOTING", 4)


class MowerAfsStatus(MowerEnum):
    """Service status, DPS 144 (``AfsStatus.Type``)."""

    UNKNOWN = ("UNKNOWN", -1)
    """Library-side fallback for unrecognized wire values; never sent."""
    IDLE = ("IDLE", 0)
    BIT = ("BIT", 1)
    MMT_OBA = ("MMT_OBA", 2)
    CALIBRATION = ("CALIBRATION", 3)
    ACTIVE = ("ACTIVE", 4)
    INACTIVE = ("INACTIVE", 5)


class MowerNetworkChannel(MowerEnum):
    """Current network route, DPS 145 (``NetworkChannel.Type``)."""

    UNKNOWN = ("UNKNOWN", 0)
    WLAN0 = ("WLAN0", 1)
    WLAN1 = ("WLAN1", 2)
    MOBILE_4G = ("MOBILE_4G", 3)


class MowerDetailState(MowerEnum):
    """Detailed task state (``rock.fsm.RobotDetailState.Type``).

    Reported in ``robot_task.robot_detail_state`` of a ``GET_ROBOT_INFO`` reply
    and, on captured devices, on DPS 123. The numeric domain is separate from
    the compact :class:`MowerMowState`.
    """

    UNKNOWN = ("UNKNOWN", 0)

    MAP_INITIALIZING = ("MAP_INITIALIZING", 1)
    MAP_UNDOCKING = ("MAP_UNDOCKING", 2)
    MAP_UNDOCK_FAULT = ("MAP_UNDOCK_FAULT", 3)
    MAP_LOCATING = ("MAP_LOCATING", 4)
    MAP_PREPARE_BOUNDARY = ("MAP_PREPARE_BOUNDARY", 5)
    MAP_PREPARE_ISLAND = ("MAP_PREPARE_ISLAND", 6)
    MAP_PREPARE_PATH = ("MAP_PREPARE_PATH", 7)
    MAP_BOUNDARY = ("MAP_BOUNDARY", 8)
    MAP_ISLAND = ("MAP_ISLAND", 9)
    MAP_PATH = ("MAP_PATH", 10)
    MAP_BOUNDARY_AUTO = ("MAP_BOUNDARY_AUTO", 11)
    # The protocol spelling "MAP_ERASEING" is intentional.
    MAP_ERASING = ("MAP_ERASEING", 12)
    MAP_SAVE = ("MAP_SAVE", 13)
    MAP_WAIT = ("MAP_WAIT", 14)
    MAP_RECOVERABLE_FAULT = ("MAP_RECOVERABLE_FAULT", 15)
    MAP_FAULT = ("MAP_FAULT", 16)
    MAP_EMERGENCY_STOP = ("MAP_EMERGENCY_STOP", 17)
    MAP_WAITING_FAULT = ("MAP_WAITING_FAULT", 18)
    MAP_NO_AVOID = ("MAP_NO_AVOID", 19)
    MAP_PREPARE_NO_AVOID = ("MAP_PREPARE_NO_AVOID", 20)
    MAP_RESET_PASSAGE = ("MAP_RESET_PASSAGE", 21)
    MAP_PREPARE_RESET_PASSAGE = ("MAP_PREPARE_RESET_PASSAGE", 22)
    MAP_EDIT_BOUNDARY = ("MAP_EDIT_BOUNDARY", 23)
    MAP_PREPARE_EDIT_BOUNDARY = ("MAP_PREPARE_EDIT_BOUNDARY", 24)
    MAP_CONFIRM_EDIT_BOUNDARY = ("MAP_CONFIRM_EDIT_BOUNDARY", 25)

    MOW_INITIALIZING = ("MOW_INITIALIZING", 51)
    MOW_UNDOCKING = ("MOW_UNDOCKING", 52)
    MOW_LOCATING = ("MOW_LOCATING", 53)
    MOW_ADJUST_CUTTER = ("MOW_ADJUST_CUTTER", 54)
    MOW_ZIG_ZAG = ("MOW_ZIG_ZAG", 55)
    MOW_EDGE = ("MOW_EDGE", 56)
    MOW_GOTO = ("MOW_GOTO", 57)
    MOW_SUSPEND = ("MOW_SUSPEND", 58)
    MOW_RECOVERABLE_FAULT = ("MOW_RECOVERABLE_FAULT", 59)
    MOW_FAULT = ("MOW_FAULT", 60)
    MOW_DOCK_RAINFALL = ("MOW_DOCK_RAINFALL", 61)
    MOW_DOCK_NOTDISTURB = ("MOW_DOCK_NOTDISTURB", 62)
    MOW_DOCK_LOW_BATTERY = ("MOW_DOCK_LOW_BATTERY", 63)
    MOW_WAIT = ("MOW_WAIT", 64)
    MOW_PREPARE_REMOTE = ("MOW_PREPARE_REMOTE", 65)
    MOW_REMOTE = ("MOW_REMOTE", 66)
    MOW_EMERGENCY_STOP = ("MOW_EMERGENCY_STOP", 67)
    MOW_DOCK_MANUAL = ("MOW_DOCK_MANUAL", 68)
    MOW_DOCK_FAULT = ("MOW_DOCK_FAULT", 69)
    MOW_REMOTE_UNDOCKING = ("MOW_REMOTE_UNDOCKING", 70)
    MOW_TO_DOCK_INITIALIZING = ("MOW_TO_DOCK_INITIALIZING", 71)
    MOW_TO_DOCK_LOCATING = ("MOW_TO_DOCK_LOCATING", 72)
    MOW_TO_DOCK_RECOVERABLE_FAULT = ("MOW_TO_DOCK_RECOVERABLE_FAULT", 73)
    MOW_TO_DOCK_FAULT = ("MOW_TO_DOCK_FAULT", 74)
    MOW_TO_DOCK_EMERGENCY_STOP = ("MOW_TO_DOCK_EMERGENCY_STOP", 75)
    MOW_TO_DOCK_CHARGING = ("MOW_TO_DOCK_CHARGING", 76)
    MOW_TO_DOCK_CHARGE_COMPLETED = ("MOW_TO_DOCK_CHARGE_COMPLETED", 77)
    MOW_PAUSE = ("MOW_PAUSE", 78)

    FREE = ("FREE", 101)
    FREE_INITIALIZING = ("FREE_INITIALIZING", 102)
    FREE_LOCATING = ("FREE_LOCATING", 103)
    FREE_DOCK_MANUAL = ("FREE_DOCK_MANUAL", 104)
    FREE_DOCK_MOW_END = ("FREE_DOCK_MOW_END", 105)
    FREE_DOCK_PLAN_END = ("FREE_DOCK_PLAN_END", 106)
    FREE_EMERGENCY_STOP = ("FREE_EMERGENCY_STOP", 107)
    FREE_RECOVERABLE_FAULT = ("FREE_RECOVERABLE_FAULT", 108)
    FREE_FAULT = ("FREE_FAULT", 109)
    FREE_BATTERY_HOLD_MODE = ("FREE_BATTERY_HOLD_MODE", 110)

    CHARGING = ("CHARGING", 151)
    CHARGE_COMPLETED = ("CHARGE_COMPLETED", 152)
    CHARGE_WAITING = ("CHARGE_WAITING", 153)
    CHARGE_FAULT = ("CHARGE_FAULT", 154)


class MowerErrorCode(MowerEnum):
    """User-facing error code reported by DPS 120.

    ``UNKNOWN`` (0) is also the value reported when no error is active, so it
    must not be surfaced as a fault by itself.
    """

    UNKNOWN = ("UNKNOWN", 0)
    MAIN_CUTTER_OVER_CURRENT = ("MAIN_CUTTER_OVER_CURRENT", 1)
    MAIN_CUTTER_OVER_TEMPERATURE = ("MAIN_CUTTER_OVER_TEMPERATURE", 2)
    MAIN_CUTTER_DYNAMIC_UNBALANCE = ("MAIN_CUTTER_DYNAMIC_UNBALANCE", 3)
    EDGE_CUTTER_OVER_CURRENT = ("EDGE_CUTTER_OVER_CURRENT", 4)
    EDGE_CUTTER_OVER_TEMPERATURE = ("EDGE_CUTTER_OVER_TEMPERATURE", 5)
    EDGE_CUTTER_DYNAMIC_UNBALANCE = ("EDGE_CUTTER_DYNAMIC_UNBALANCE", 6)
    HEIGHT_MODULE_ADJUSTING_INCOMPLETE = ("HEIGHT_MODULE_ADJUSTING_INCOMPLETE", 7)
    TRAVEL_MOTOR_LEFT_FRONT_OVER_CURRENT = ("TRAVEL_MOTOR_LEFT_FRONT_OVER_CURRENT", 8)
    TRAVEL_MOTOR_RIGHT_FRONT_OVER_CURRENT = ("TRAVEL_MOTOR_RIGHT_FRONT_OVER_CURRENT", 9)
    TRAVEL_MOTOR_LEFT_REAR_OVER_CURRENT = ("TRAVEL_MOTOR_LEFT_REAR_OVER_CURRENT", 10)
    TRAVEL_MOTOR_RIGHT_REAR_OVER_CURRENT = ("TRAVEL_MOTOR_RIGHT_REAR_OVER_CURRENT", 11)
    TRAVEL_MOTOR_OVER_TEMPERATURE = ("TRAVEL_MOTOR_OVER_TEMPERATURE", 12)
    STEERING_MOTOR_LEFT_FRONT_OVER_CURRENT = ("STEERING_MOTOR_LEFT_FRONT_OVER_CURRENT", 13)
    STEERING_MOTOR_RIGHT_FRONT_OVER_CURRENT = ("STEERING_MOTOR_RIGHT_FRONT_OVER_CURRENT", 14)
    STEERING_MOTOR_OVER_TEMPERATURE = ("STEERING_MOTOR_OVER_TEMPERATURE", 15)
    STOP = ("STOP", 16)
    TILT = ("TILT", 17)
    LIFT = ("LIFT", 18)
    FLIP = ("FLIP", 19)
    OUT_OF_BOUND = ("OUT_OF_BOUND", 20)
    BUMPER = ("BUMPER", 21)
    BATTERY_DISCHARGE_OVER_TEMPERATURE = ("BATTERY_DISCHARGE_OVER_TEMPERATURE", 22)
    BATTERY_DISCHARGE_LOW_TEMPERATURE = ("BATTERY_DISCHARGE_LOW_TEMPERATURE", 23)
    BATTERY_UNOFFICIAL = ("BATTERY_UNOFFICIAL", 24)
    DIRTY_CHARGING_CLIPS = ("DIRTY_CHARGING_CLIPS", 25)
    CHARGE_STATION_NO_POWER = ("CHARGE_STATION_NO_POWER", 26)
    CAMERA_DIRTY_OR_OBSTRUCTED = ("CAMERA_DIRTY_OR_OBSTRUCTED", 27)
    CAMERA_OVER_TEMPERATURE = ("CAMERA_OVER_TEMPERATURE", 28)
    CAMERA_LED_OBSTRUCTED = ("CAMERA_LED_OBSTRUCTED", 29)
    LIDAR_DIRTY = ("LIDAR_DIRTY", 30)
    LIDAR_OVER_TEMPERATURE = ("LIDAR_OVER_TEMPERATURE", 31)
    LOCATION_FAILED = ("LOCATION_FAILED", 32)
    LOCATION_AT_ISLAND = ("LOCATION_AT_ISLAND", 33)
    LOCATION_AT_NON_COMPLIANT_SLOPE = ("LOCATION_AT_NON_COMPLIANT_SLOPE", 34)
    BE_TRAPPED = ("BE_TRAPPED", 35)
    CHARGE_STATION_OR_RTK_SLIGHT_MOVEMENT_DOCK = ("CHARGE_STATION_OR_RTK_SLIGHT_MOVEMENT_DOCK", 36)
    N_RTK_SIGNIFICANT_MOVEMENT = ("N_RTK_SIGNIFICANT_MOVEMENT", 37)
    RTK_SIGNIFICANT_MOVEMENT = ("RTK_SIGNIFICANT_MOVEMENT", 38)
    DOCK_CHARGE_STATION_SEARCH_FAIL = ("DOCK_CHARGE_STATION_SEARCH_FAIL", 39)
    DOCK_QRCODE_SCAN_FAIL = ("DOCK_QRCODE_SCAN_FAIL", 40)
    DOCK_ADJUST_ERROR = ("DOCK_ADJUST_ERROR", 41)
    UNDOCK_ERROR = ("UNDOCK_ERROR", 42)
    BATTERY_CHARGE_OVER_TEMPERATURE = ("BATTERY_CHARGE_OVER_TEMPERATURE", 43)
    BATTERY_CHARGE_LOW_TEMPERATURE = ("BATTERY_CHARGE_LOW_TEMPERATURE", 44)
    CAMERA_SEVERELY_DIRTY = ("CAMERA_SEVERELY_DIRTY", 45)
    NO_PLUGIN_KEY = ("NO_PLUGIN_KEY", 46)
    CAMERA_REAR_SIDE_DIRTY = ("CAMERA_REAR_SIDE_DIRTY", 48)
    N_RTK_NETWORK_ERROR = ("N_RTK_NETWORK_ERROR", 55)
    MAIN_CUTTER_FAULT = ("MAIN_CUTTER_FAULT", 101)
    EDGE_CUTTER_FAULT = ("EDGE_CUTTER_FAULT", 102)
    HEIGHT_MODULE_FAULT = ("HEIGHT_MODULE_FAULT", 103)
    BATTERY_FAULT = ("BATTERY_FAULT", 104)
    CAMERA_FAULT = ("CAMERA_FAULT", 105)
    CAMERA_LED_FAULT = ("CAMERA_LED_FAULT", 106)
    MAIN_BOARD_FAULT = ("MAIN_BOARD_FAULT", 107)
    LIDAR_FAULT = ("LIDAR_FAULT", 108)
    TRAVEL_MOTOR_LEFT_FRONT_FAULT = ("TRAVEL_MOTOR_LEFT_FRONT_FAULT", 109)
    TRAVEL_MOTOR_RIGHT_FRONT_FAULT = ("TRAVEL_MOTOR_RIGHT_FRONT_FAULT", 110)
    TRAVEL_MOTOR_LEFT_REAR_FAULT = ("TRAVEL_MOTOR_LEFT_REAR_FAULT", 111)
    TRAVEL_MOTOR_RIGHT_REAR_FAULT = ("TRAVEL_MOTOR_RIGHT_REAR_FAULT", 112)
    STEERING_MOTOR_LEFT_FRONT_FAULT = ("STEERING_MOTOR_LEFT_FRONT_FAULT", 113)
    STEERING_MOTOR_RIGHT_FRONT_FAULT = ("STEERING_MOTOR_RIGHT_FRONT_FAULT", 114)
    LED_SCREEN_FAULT = ("LED_SCREEN_FAULT", 115)
    LEFT_SIDE_CAMERA_FAULT = ("LEFT_SIDE_CAMERA_FAULT", 116)
    RIGHT_SIDE_CAMERA_FAULT = ("RIGHT_SIDE_CAMERA_FAULT", 117)
    REAR_SIDE_CAMERA_FAULT = ("REAR_SIDE_CAMERA_FAULT", 118)

from enum import IntEnum

from ..code_mappings import RoborockModeEnum


class B01_Q10_DP(RoborockModeEnum):
    CLEAN_TIME = ("dpCleanTime", 6)
    CLEAN_AREA = ("dpCleanArea", 7)
    SEEK = ("dpSeek", 11)
    REMOTE = ("dpRemote", 12)
    MAP_RESET = ("dpMapReset", 13)
    REQUEST = ("dpRequest", 16)
    RESET_SIDE_BRUSH = ("dpResetSideBrush", 18)
    RESET_MAIN_BRUSH = ("dpResetMainBrush", 20)
    RESET_FILTER = ("dpResetFilter", 22)
    RAG_LIFE = ("dpRagLife", 23)
    RESET_RAG_LIFE = ("dpResetRagLife", 24)
    NOT_DISTURB = ("dpNotDisturb", 25)
    VOLUME = ("dpVolume", 26)
    BEAK_CLEAN = ("dpBeakClean", 27)
    TOTAL_CLEAN_AREA = ("dpTotalCleanArea", 29)
    TOTAL_CLEAN_COUNT = ("dpTotalCleanCount", 30)
    TOTAL_CLEAN_TIME = ("dpTotalCleanTime", 31)
    TIMER = ("dpTimer", 32)
    NOT_DISTURB_DATA = ("dpNotDisturbData", 33)
    DEVICE_INFO = ("dpDeviceInfo", 34)
    VOICE_PACKAGE = ("dpVoicePackage", 35)
    VOICE_LANGUAGE = ("dpVoiceLanguage", 36)
    DUST_SWITCH = ("dpDustSwitch", 37)
    CUSTOM_MODE = ("dpCustomMode", 39)
    MOP_STATE = ("dpMopState", 40)
    UNIT = ("dpUnit", 42)
    CARPET_CLEAN_PREFER = ("dpCarpetCleanPrefer", 44)
    AUTO_BOOST = ("dpAutoBoost", 45)
    CHILD_LOCK = ("dpChildLock", 47)
    DUST_SETTING = ("dpDustSetting", 50)
    MAP_SAVE_SWITCH = ("dpMapSaveSwitch", 51)
    CLEAN_RECORD = ("dpCleanRecord", 52)
    RECENT_CLEAN_RECORD = ("dpRecentCleanRecord", 53)  # NOTE: typo "dpRecendCleanRecord" in source code
    RESTRICTED_ZONE = ("dpRestrictedZone", 54)
    RESTRICTED_ZONE_UP = ("dpRestrictedZoneUp", 55)
    VIRTUAL_WALL = ("dpVirtualWall", 56)
    VIRTUAL_WALL_UP = ("dpVirtualWallUp", 57)
    ZONED = ("dpZoned", 58)
    ZONED_UP = ("dpZonedUp", 59)
    MULTI_MAP_SWITCH = ("dpMultiMapSwitch", 60)
    MULTI_MAP = ("dpMultiMap", 61)
    CUSTOMER_CLEAN = ("dpCustomerClean", 62)
    CUSTOMER_CLEAN_REQUEST = ("dpCustomerCleanRequest", 63)
    GET_CARPET = ("dpGetCarpet", 64)
    CARPET_UP = ("dpCarpetUp", 65)
    SELF_IDENTIFYING_CARPET = ("dpSelfIdentifyingCarpet", 66)
    SENSOR_LIFE = ("dpSensorLife", 67)
    RESET_SENSOR = ("dpResetSensor", 68)
    REQUEST_TIMER = ("dpRequestTimer", 69)
    REMOVE_ZONED = ("dpRemoveZoned", 70)
    REMOVE_ZONED_UP = ("dpRemoveZonedUp", 71)
    ROOM_MERGE = ("dpRoomMerge", 72)
    ROOM_SPLIT = ("dpRoomSplit", 73)
    RESET_ROOM_NAME = ("dpResetRoomName", 74)
    REQUEST_NOT_DISTURB_DATA = ("dpRequestNotDisturbData", 75)  # NOTE: typo "dpRequsetNotDisturbData" in source code
    CARPET_CLEAN_TYPE = ("dpCarpetCleanType", 76)
    BUTTON_LIGHT_SWITCH = ("dpButtonLightSwitch", 77)
    CLEAN_LINE = ("dpCleanLine", 78)
    TIME_ZONE = ("dpTimeZone", 79)
    AREA_UNIT = ("dpAreaUnit", 80)
    NET_INFO = ("dpNetInfo", 81)
    CLEAN_ORDER = ("dpCleanOrder", 82)
    ROBOT_TYPE = ("dpRobotType", 83)
    LOG_SWITCH = ("dpLogSwitch", 84)
    FLOOR_MATERIAL = ("dpFloorMaterial", 85)
    LINE_LASER_OBSTACLE_AVOIDANCE = ("dpLineLaserObstacleAvoidance", 86)
    CLEAN_PROGRESS = ("dpCleanProgress", 87)  # NOTE: typo "dpCleanProgess" in source code
    GROUND_CLEAN = ("dpGroundClean", 88)
    IGNORE_OBSTACLE = ("dpIgnoreObstacle", 89)
    FAULT = ("dpFault", 90)
    CLEAN_EXPAND = ("dpCleanExpand", 91)
    NOT_DISTURB_EXPAND = ("dpNotDisturbExpand", 92)
    TIMER_TYPE = ("dpTimerType", 93)
    CREATE_MAP_FINISHED = ("dpCreateMapFinished", 94)
    ADD_CLEAN_AREA = ("dpAddCleanArea", 95)
    ADD_CLEAN_STATE = ("dpAddCleanState", 96)
    RESTRICTED_AREA = ("dpRestrictedArea", 97)
    RESTRICTED_AREA_UP = ("dpRestrictedAreaUp", 98)
    SUSPECTED_THRESHOLD = ("dpSuspectedThreshold", 99)
    SUSPECTED_THRESHOLD_UP = ("dpSuspectedThresholdUp", 100)
    COMMON = ("dpCommon", 101)
    REQUEST_DPS = ("dpRequestDps", 102)  # NOTE: typo "dpRequetdps" in source code
    # NOTE: the legacy B01 source also listed dpJumpScan (101) and
    # dpCliffRestrictedArea (102), which collided with the confirmed dpCommon /
    # dpRequestDps codes above (verified against ss07 hardware and the official app
    # plugin) and shadowed them in ``from_code``. Both are unused and their real
    # codes could not be verified, so they were removed rather than left as wrong
    # duplicates. dpCliffRestrictedAreaUp (103) is kept: ss07 hardware does push
    # data point 103 (an empty list when no cliff-restricted areas are set).
    CLIFF_RESTRICTED_AREA_UP = ("dpCliffRestrictedAreaUp", 103)
    BREAKPOINT_CLEAN = ("dpBreakpointClean", 104)
    VALLEY_POINT_CHARGING = ("dpValleyPointCharging", 105)
    VALLEY_POINT_CHARGING_DATA_UP = ("dpValleyPointChargingDataUp", 106)
    VALLEY_POINT_CHARGING_DATA = ("dpValleyPointChargingData", 107)
    VOICE_VERSION = ("dpVoiceVersion", 108)
    ROBOT_COUNTRY_CODE = ("dpRobotCountryCode", 109)
    HEARTBEAT = ("dpHeartbeat", 110)
    # NOTE: ss07 hardware also pushes data points 112 and 113 in its full status
    # dump. They are absent from the official app's vacuum plugin and stayed 0
    # across every observed state (docked/charging, segment cleaning, lifted-off-
    # ground fault, returning to dock, dustbin removed), so their meaning is not
    # yet known. They are intentionally left unmapped; ``decode_rpc_response``
    # silently ignores unknown codes via ``from_code_optional``, so they do not
    # produce "not a valid code" warnings. Map them here once identified.
    STATUS = ("dpStatus", 121)
    BATTERY = ("dpBattery", 122)
    FAN_LEVEL = ("dpFanLevel", 123)  # NOTE: typo "dpfunLevel" in source code
    WATER_LEVEL = ("dpWaterLevel", 124)
    MAIN_BRUSH_LIFE = ("dpMainBrushLife", 125)
    SIDE_BRUSH_LIFE = ("dpSideBrushLife", 126)
    FILTER_LIFE = ("dpFilterLife", 127)
    TASK_CANCEL_IN_MOTION = ("dpTaskCancelInMotion", 132)
    OFFLINE = ("dpOffline", 135)
    CLEAN_COUNT = ("dpCleanCount", 136)
    CLEAN_MODE = ("dpCleanMode", 137)
    CLEAN_TASK_TYPE = ("dpCleanTaskType", 138)
    BACK_TYPE = ("dpBackType", 139)
    CLEANING_PROGRESS = ("dpCleaningProgress", 141)
    FLEEING_GOODS = ("dpFleeingGoods", 142)
    START_CLEAN = ("dpStartClean", 201)
    START_BACK = ("dpStartBack", 202)
    START_DOCK_TASK = ("dpStartDockTask", 203)
    PAUSE = ("dpPause", 204)
    RESUME = ("dpResume", 205)
    STOP = ("dpStop", 206)
    USER_PLAN = ("dpUserPlan", 207)


class YXFanLevel(RoborockModeEnum):
    """The fan or vacuum level of the robot.

    Note: The names used here are the v1 names, though the values
    have different aliases in the app bundles.
    """

    UNKNOWN = "unknown", -1
    OFF = "off", 0  # close
    QUIET = "quiet", 1
    BALANCED = "balanced", 2  # normal
    TURBO = "turbo", 3  # strong
    MAX = "max", 4
    MAX_PLUS = "max_plus", 8  # super


class YXWaterLevel(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    OFF = "off", 0  # close
    LOW = "low", 1
    MEDIUM = "medium", 2  # middle
    HIGH = "high", 3


class YXCleanLine(RoborockModeEnum):
    FAST = "fast", 0
    DAILY = "daily", 1
    FINE = "fine", 2


class YXRoomMaterial(RoborockModeEnum):
    HORIZONTAL_FLOOR_BOARD = "horizontalfloorboard", 0
    VERTICAL_FLOOR_BOARD = "verticalfloorboard", 1
    CERAMIC_TILE = "ceramictile", 2
    OTHER = "other", 255


class YXCleanType(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    VAC_AND_MOP = "vac_and_mop", 1  # bothwork
    VACUUM = "vacuum", 2  # onlysweep
    MOP = "mop", 3  # onlymop
    CUSTOMIZED = "customized", 4  # custom mode


class YXDeviceState(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    SLEEPING = "sleeping", 2  # sleepstate
    IDLE = "idle", 3  # standbystate
    CLEANING = "cleaning", 5  # cleaningstate
    RETURNING_HOME = "returning_home", 6  # tochargestate
    REMOTE_CONTROL_ACTIVE = "remote_control_active", 7  # remoteingstate
    CHARGING = "charging", 8  # chargingstate
    PAUSED = "paused", 10  # pausestate
    ERROR = "error", 12  # faultstate
    UPDATING = "updating", 14  # upgradestate
    EMPTYING_THE_BIN = "emptying_the_bin", 22  # dusting
    MAPPING = "mapping", 29  # creatingmapstate
    SAVING_MAP = "saving_map", 99  # mapsavestate
    RELOCATING = "relocating", 101  # relocationstate
    SWEEPING = "sweeping", 102  # robotsweeping
    MOPPING = "mopping", 103  # robotmoping
    SWEEP_AND_MOP = "sweep_and_mop", 104  # robotsweepandmoping
    TRANSITIONING = "transitioning", 105  # robottransitioning
    WAITING_TO_CHARGE = "waiting_to_charge", 108  # robotwaitcharge


class YXBackType(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    IDLE = "idle", 0
    BACK_DUSTING = "backdusting", 4
    BACK_CHARGING = "backcharging", 5


class YXDeviceWorkMode(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    BOTH_WORK = "bothwork", 1
    ONLY_SWEEP = "onlysweep", 2
    ONLY_MOP = "onlymop", 3
    CUSTOMIZED = "customized", 4
    SAVE_WORRY = "saveworry", 5
    SWEEP_MOP = "sweepmop", 6


class YXDeviceCleanTask(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    IDLE = "idle", 0
    SMART = "smart", 1
    ELECTORAL = "electoral", 2
    DIVIDE_AREAS = "divideareas", 3
    CREATING_MAP = "creatingmap", 4
    PART = "part", 5


class YXCleanScope(RoborockModeEnum):
    """Clean scope/type as stored in a *clean record* (``dpCleanRecord``, field 7).

    This is the same conceptual axis as the live :class:`YXDeviceCleanTask`, but the
    persisted record uses a different integer encoding -- e.g. a full clean records
    ``0`` here vs ``1`` (``smart``) live, and a select-rooms clean records ``1`` here
    vs ``2`` (``electoral``) live. Ground-truthed against the app's History labels;
    code ``2`` was never observed on ss07 and is intentionally unmapped (so it
    resolves to ``None`` rather than a guessed label).
    """

    UNKNOWN = "unknown", -1
    FULL = "full", 0
    SELECTIVE_ROOM = "selective_room", 1
    ZONE = "zone", 3
    SPOT = "spot", 4


class YXCleaningResult(RoborockModeEnum):
    """How a clean ended, as stored in a clean record (``dpCleanRecord``, field 9)."""

    UNKNOWN = "unknown", -1
    INTERRUPTED = "interrupted", 0  # ended on a fault
    COMPLETED = "completed", 1
    STOPPED = "stopped", 2  # ended early without a fault


class YXStartMethod(RoborockModeEnum):
    """What initiated a clean, as stored in a clean record (``dpCleanRecord``, field 10)."""

    UNKNOWN = "unknown", -1
    REMOTE = "remote", 0
    APP = "app", 1
    TIMER = "timer", 2  # schedule / timer
    BUTTON = "button", 3  # device button


class YXDeviceDustCollectionFrequency(RoborockModeEnum):
    # The app exposes "regular" (code 0) vs "frequent", where "frequent" selects
    # one of the every-N-cleans intervals below.
    REGULAR = "regular", 0
    INTERVAL_15 = "interval_15", 15
    INTERVAL_30 = "interval_30", 30
    INTERVAL_45 = "interval_45", 45
    INTERVAL_60 = "interval_60", 60


class YXAreaUnit(RoborockModeEnum):
    """Unit used to report cleaned area (dpAreaUnit)."""

    SQUARE_METER = "square_meter", 0
    SQUARE_FEET = "square_feet", 1


class YXCarpetCleanType(RoborockModeEnum):
    """Carpet handling behavior (dpCarpetCleanType)."""

    RISE = "rise", 0  # lift the mop and boost over carpet
    AVOID = "avoid", 1
    IGNORE = "ignore", 2
    CROSS = "cross", 3


class YXFault(RoborockModeEnum):
    """Q10 (B01/ss07) ``dpFault`` (90) codes, from the ss07 fault spec.

    ``dpFault`` is *overloaded*: several values are lifecycle/status rather than
    errors (e.g. 400 = scheduled clean starting, 501 = returning to dock,
    502 = recharge). A non-zero fault is not necessarily a blocking error.
    The converse also holds: the device can sit in its error state (``dpStatus``
    12) with ``dpFault`` still 0 (observed live with the dust-bin module
    removed), so a ``None``/``NONE`` fault does not imply the absence of an
    error condition.

    These labels differ from the Q7 ``B01Fault`` for several shared numbers
    (500, 501, 503, 569, 570) -- so this is a Q10-specific map, not a reuse of
    ``B01Fault``. Codes marked "hw-confirmed" were observed firing live on a
    physical ss07 in a context matching the label; the rest are from the spec
    only, not yet observed live (single device).
    """

    UNKNOWN = "unknown", -1
    NONE = "none", 0
    LIDAR_BLOCKED = "lidar_blocked", 1
    BUMPER_STUCK = "bumper_stuck", 2  # hw-confirmed (bumper held in during commanded motion)
    ROBOT_SUSPENDED = "robot_suspended", 3  # hw-confirmed (wheels lifted off the floor mid-task)
    CLIFF_SENSOR_ERROR = "cliff_sensor_error", 4  # hw-confirmed (one side lifted mid-task)
    MAIN_BRUSH_STUCK = "main_brush_stuck", 5  # hw-confirmed (two physical brush jams)
    MAIN_WHEELS_STUCK = "main_wheels_stuck", 7
    ROBOT_TRAPPED = "robot_trapped", 8  # hw-confirmed
    CHECK_DUSTBIN_FILTER = "check_dustbin_filter", 9
    LOW_BATTERY = "low_battery", 12  # hw-confirmed (fired at 14% mid clean)
    TEMPERATURE_THRESHOLD = "temperature_threshold", 14
    ROBOT_TILTED = "robot_tilted", 16
    LIDAR_COVER_OBSTRUCTED = "lidar_cover_obstructed", 21
    NO_GO_ZONE_DETECTED = "no_go_zone_detected", 24
    MOPPING_MODULE_STUCK = "mopping_module_stuck", 27
    CARPET_AVOIDANCE = "carpet_avoidance", 28
    CANNOT_CROSS_CARPET = "cannot_cross_carpet", 29
    INSTALL_DUST_BAG = "install_dust_bag", 46  # hw-confirmed (docked with bag removed; fires at dock contact)
    MOP_MOUNT_FELL_OFF = "mop_mount_fell_off", 54
    LIDAR_DIRTY = "lidar_dirty", 58
    FILTER_SERVICE_LIFE = "filter_service_life", 301
    MAIN_BRUSH_SERVICE_LIFE = "main_brush_service_life", 302
    SIDE_BRUSH_SERVICE_LIFE = "side_brush_service_life", 303
    SENSOR_NEEDS_CLEANING = "sensor_needs_cleaning", 304  # hw-confirmed (fired during auto-empty)
    DUST_BAG_FULL = "dust_bag_full", 310  # inferred from auto-empty context; not hw-confirmed
    STARTING_SCHEDULED_CLEAN = "starting_scheduled_clean", 400  # hw-confirmed x3; lifecycle, not an error
    # hw-confirmed (a due scheduled clean fired mid-clean and was ignored); lifecycle, not an error
    CLEANING_IN_PROGRESS = "cleaning_in_progress", 407
    EMPTY_DUSTBIN = "empty_dustbin", 500  # ss07 != Q7 B01Fault (lidar_blocked); spec-only
    # hw-confirmed, fires per completed task; ss07 != Q7 (robot_suspended)
    CLEANING_COMPLETED_RETURNING = "cleaning_completed_returning", 501
    LOW_BATTERY_RESUME = "low_battery_resume", 502  # hw-confirmed; lifecycle
    DOCKING_ERROR = "docking_error", 503  # hw-confirmed; ss07 != Q7 (dustbin_not_installed)
    POSITIONING_FAILED = "positioning_failed", 556  # hw-confirmed; relocalization
    # hw-confirmed (3rd auto-empty in ~15 min: dock refuses to run the cycle); ss07 != Q7 (main_wheels_entangled)
    TOO_FREQUENT_EMPTYING = "too_frequent_emptying", 569
    CANNOT_REACH_TARGET = "cannot_reach_target", 570  # hw-confirmed; ss07 != Q7 (main_brush_entangled)
    OFFLINE_WARNING_ASLEEP = "offline_warning_asleep", 588
    OFFLINE_WARNING_LOW_BATTERY = "offline_warning_low_battery", 589
    DND_AUTO_TOPUP_DISABLED = "dnd_auto_topup_disabled", 591
    CLEAN_CARPET_ULTRASONIC_SENSORS = "clean_carpet_ultrasonic_sensors", 707
    ROBOT_ERROR_RESET = "robot_error_reset", 1002
    VOICE_PACK_UPDATE_AVAILABLE = "voice_pack_update_available", 3001


class RemoteCommand(IntEnum):
    FORWARD = 0
    LEFT = 2
    RIGHT = 3
    STOP = 4
    EXIT = 5

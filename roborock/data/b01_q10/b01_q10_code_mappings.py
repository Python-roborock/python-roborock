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
    JUMP_SCAN = ("dpJumpScan", 101)
    REQUEST_DPS = ("dpRequestDps", 102)  # NOTE: typo "dpRequetdps" in source code
    CLIFF_RESTRICTED_AREA = ("dpCliffRestrictedArea", 102)
    CLIFF_RESTRICTED_AREA_UP = ("dpCliffRestrictedAreaUp", 103)
    BREAKPOINT_CLEAN = ("dpBreakpointClean", 104)
    VALLEY_POINT_CHARGING = ("dpValleyPointCharging", 105)
    VALLEY_POINT_CHARGING_DATA_UP = ("dpValleyPointChargingDataUp", 106)
    VALLEY_POINT_CHARGING_DATA = ("dpValleyPointChargingData", 107)
    VOICE_VERSION = ("dpVoiceVersion", 108)
    ROBOT_COUNTRY_CODE = ("dpRobotCountryCode", 109)
    HEARTBEAT = ("dpHeartbeat", 110)
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
    UNKNOWN = "unknown", -1
    CLOSE = "close", 0
    QUITE = "quite", 1
    NORMAL = "normal", 2
    STRONG = "strong", 3
    MAX = "max", 4
    SUPER = "super", 8


class YXWaterLevel(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    CLOSE = "close", 0
    LOW = "low", 1
    MIDDLE = "middle", 2
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
    BOTH_WORK = "bothwork", 1
    ONLY_SWEEP = "onlysweep", 2
    ONLY_MOP = "onlymop", 3


class YXDeviceState(RoborockModeEnum):
    UNKNOWN = "unknown", -1
    SLEEP_STATE = "sleepstate", 2
    STANDBY_STATE = "standbystate", 3
    CLEANING_STATE = "cleaningstate", 5
    TO_CHARGE_STATE = "tochargestate", 6
    REMOTEING_STATE = "remoteingstate", 7
    CHARGING_STATE = "chargingstate", 8
    PAUSE_STATE = "pausestate", 10
    FAULT_STATE = "faultstate", 12
    UPGRADE_STATE = "upgradestate", 14
    DUSTING = "dusting", 22
    CREATING_MAP_STATE = "creatingmapstate", 29
    MAP_SAVE_STATE = "mapsavestate", 99
    RE_LOCATION_STATE = "relocationstate", 101
    ROBOT_SWEEPING = "robotsweeping", 102
    ROBOT_MOPING = "robotmoping", 103
    ROBOT_SWEEP_AND_MOPING = "robotsweepandmoping", 104
    ROBOT_TRANSITIONING = "robottransitioning", 105
    ROBOT_WAIT_CHARGE = "robotwaitcharge", 108


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


class YXDeviceDustCollectionFrequency(RoborockModeEnum):
    DAILY = "daily", 0
    INTERVAL_15 = "interval_15", 15
    INTERVAL_30 = "interval_30", 30
    INTERVAL_45 = "interval_45", 45
    INTERVAL_60 = "interval_60", 60

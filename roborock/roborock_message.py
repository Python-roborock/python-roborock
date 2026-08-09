from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self

from roborock.data.code_mappings import RoborockEnum
from roborock.util import get_next_int, get_timestamp


class RoborockMessageProtocol(RoborockEnum):
    HELLO_REQUEST = 0
    HELLO_RESPONSE = 1
    PING_REQUEST = 2
    PING_RESPONSE = 3
    GENERAL_REQUEST = 4
    GENERAL_RESPONSE = 5
    RPC_REQUEST = 101
    RPC_RESPONSE = 102
    MAP_RESPONSE = 301


class RoborockDataProtocol(RoborockEnum):
    ERROR_CODE = 120
    STATE = 121
    BATTERY = 122
    FAN_POWER = 123
    WATER_BOX_MODE = 124
    MAIN_BRUSH_WORK_TIME = 125
    SIDE_BRUSH_WORK_TIME = 126
    FILTER_WORK_TIME = 127
    ADDITIONAL_PROPS = 128
    TASK_COMPLETE = 130
    TASK_CANCEL_LOW_POWER = 131
    TASK_CANCEL_IN_MOTION = 132
    CHARGE_STATUS = 133
    DRYING_STATUS = 134
    OFFLINE_STATUS = 135

    @classmethod
    def _missing_(cls: type[Self], key) -> Self:
        raise ValueError(f"{key} not a valid key for Data Protocol")


class RoborockMowerDataProtocol(RoborockEnum):
    UNKNOWN = 0
    ERROR_CODE = 120
    BATTERY = 121
    MOW_TYPE = 122
    MOW_STATE = 123
    MAPPING_TYPE = 124
    MAPPING_STATE = 125
    OTA_STATE = 126
    CHARGE_STATE = 127
    DOCK_STATE = 128
    CHARGE_TYPE = 129
    PEND_TYPE = 130
    REMOTE_STATE = 131
    MOW_START_TYPE = 132
    MOW_EFF_MODE = 133
    MOW_HEIGHT = 134
    MOW_DIRECTION_ANGLE = 135
    MOW_PATTERN = 136
    MOW_CONF_MODE = 137
    OFFLINE_STATUS = 138
    MOW_PROGRESS = 139
    BLADE_LIFESPAN = 140
    FC_STATE = 141
    GPS_COORDINATE = 142
    OFF_DOCK_NO_TASK_STATUS = 143
    AFS_STATUS = 144
    NETWORK_CHANNEL = 145
    START = 201
    DOCK = 202
    PAUSE = 203
    RESUME = 204
    STOP = 205

    @classmethod
    def _missing_(cls: type[Self], key) -> Self:
        raise ValueError(f"{key} not a valid key for Mower Data Protocol")


class RoborockDyadDataProtocol(RoborockEnum):
    DRYING_STATUS = 134
    START = 200
    STATUS = 201
    SELF_CLEAN_MODE = 202
    SELF_CLEAN_LEVEL = 203
    WARM_LEVEL = 204
    CLEAN_MODE = 205
    SUCTION = 206
    WATER_LEVEL = 207
    BRUSH_SPEED = 208
    POWER = 209
    COUNTDOWN_TIME = 210
    AUTO_SELF_CLEAN_SET = 212
    AUTO_DRY = 213
    MESH_LEFT = 214
    BRUSH_LEFT = 215
    ERROR = 216
    MESH_RESET = 218
    BRUSH_RESET = 219
    VOLUME_SET = 221
    STAND_LOCK_AUTO_RUN = 222
    AUTO_SELF_CLEAN_SET_MODE = 223
    AUTO_DRY_MODE = 224
    SILENT_DRY_DURATION = 225
    SILENT_MODE = 226
    SILENT_MODE_START_TIME = 227
    SILENT_MODE_END_TIME = 228
    RECENT_RUN_TIME = 229
    TOTAL_RUN_TIME = 230
    FEATURE_INFO = 235
    RECOVER_SETTINGS = 236
    DRY_COUNTDOWN = 237
    ID_QUERY = 10000
    F_C = 10001
    SCHEDULE_TASK = 10002
    SND_SWITCH = 10003
    SND_STATE = 10004
    PRODUCT_INFO = 10005
    PRIVACY_INFO = 10006
    OTA_NFO = 10007
    RPC_REQUEST = 10101
    RPC_RESPONSE = 10102


class RoborockZeoProtocol(RoborockEnum):
    """Zeo device Data Point protocol IDs (200-266) and meta/RPC commands (10000+).

    Comment tags:
      ro  — read-only
      rw  — read-write
      wo  — write-only
      [startWith]  — must be bundled with START via start()
      [independent] — immediate effect, works via set_value()
    """

    # ── DP 200-266 ─────────────────────────────────────────────────────
    START = 200  # rw  [action → start()]
    PAUSE = 201  # rw
    SHUTDOWN = 202  # rw
    STATE = 203  # ro
    MODE = 204  # rw  [startWith]
    PROGRAM = 205  # rw  [startWith]
    CHILD_LOCK = 206  # rw  [independent]
    TEMP = 207  # rw  [startWith]
    RINSE_TIMES = 208  # rw  [startWith]
    SPIN_LEVEL = 209  # rw  [startWith]
    DRYING_MODE = 210  # rw  [startWith]
    DETERGENT_SET = 211  # rw  [independent]
    SOFTENER_SET = 212  # rw  [independent]
    DETERGENT_TYPE = 213  # rw  [independent]
    SOFTENER_TYPE = 214  # rw  [independent]
    DIRT_DETECTION_SWITCH = 215  # rw  [independent]
    DIRT_DETECTION_STATUS = 216  # ro
    COUNTDOWN = 217  # rw  [independent]  also used in start_with_preset()
    WASHING_LEFT = 218  # ro
    DOORLOCK_STATE = 219  # ro
    ERROR = 220  # ro
    CUSTOM_PARAM_SAVE = 221  # rw  [independent]  see save_cloud_program()
    CUSTOM_PARAM_GET = 222  # rw  [independent]  read via get_custom_mode(), write via load_cloud_program()
    SOUND_SET = 223  # rw  [independent]
    TIMES_AFTER_CLEAN = 224  # ro
    DEFAULT_SETTING = 225  # rw  [independent]
    DETERGENT_EMPTY = 226  # ro
    SOFTENER_EMPTY = 227  # ro
    UV_LIGHT = 228  # rw  [independent]
    LIGHT_SETTING = 229  # rw  [independent]  server schema only, not found in bundle
    DETERGENT_VOLUME = 230  # rw  [independent]  server schema only, not found in bundle
    SOFTENER_VOLUME = 231  # rw  [independent]  server schema only, not found in bundle
    APP_AUTHORIZATION = 232  # ro
    SOAK = 233  # rw  [startWith]
    TOTAL_TIME = 234  # ro  used in dryer startWith payload
    SMART_HOSTING = 235  # rw  [independent]
    SMART_HOSTING_TIME = 236  # ro
    FEATURE_BITS = 237  # ro  decoded by ZeoFeatureBits
    SMART_HOSTING_WAITED_TIME = 238  # ro
    CUSTOM_PROGRAM_CLEANING_TIME = 239  # ro
    SILENT_MODE_ON = 240  # rw  [independent]  use set_silent_mode() for bundled set
    SILENT_MODE_START_TIME = 241  # rw  [independent]  minute-of-day
    SILENT_MODE_END_TIME = 242  # rw  [independent]  minute-of-day
    DRY_CARE_MODE = 244  # rw  [startWith]
    SOFTENER_EXPANSION_TYPE = 245  # rw  [independent]
    SMILE_LIGHT_STATUS = 247  # rw  [independent]
    DETERGENT_EXPANSION_TYPE = 248  # rw  [independent]
    FLUFF_CLEANED = 249  # rw  [independent]
    IS_NEED_FLUFF_CLEAN = 250  # ro
    POWER_LIGHT = 251  # rw  [independent]
    PANEL_PROGRAM_PARAMS_SET = 252  # rw  [independent]
    PANEL_PROGRAM_PARAMS_SET_RESULT = 253  # ro
    SAVE_ADAPTED_CLOUD_PROGRAM = 254  # rw  [independent]
    WASH_DRY_LINKED = 255  # rw  [startWith / feature-gated]
    DRYING_METHOD = 256  # rw  [startWith]
    STEAM_VOLUME = 257  # rw  [startWith]
    ION_DEODORIZATION = 258  # rw  [startWith / feature-gated]
    PANEL_TIMING_PROGRAM_PARAMS = 260  # ro
    STEAM_CARE_TIME = 261  # ro
    DEVICE_BOUND = 262  # ro
    CLOTH_PUT_IN = 263  # ro
    CLOTH_READY_TO_DRY_COUNT_DOWN = 264  # ro
    START_DRYER_ERROR = 265  # ro
    WIFI_LINKAGE_RESET = 266  # rw  [independent]

    # ── Meta / RPC / Voice (10000+) ────────────────────────────────────
    ID_QUERY = 10000  # -- multi-DP query request (not a device DP)
    F_C = 10001  # ro  query via checkFCCState()
    SET_SOUND_PACKAGE = 10003  # wo  setSoundPackage(JSON)
    SND_STATE = 10004  # ro  query via updateSoundPackageInfo()
    PRODUCT_INFO = 10005  # ro  query via loadGeneralInfo() (10s timeout)
    PRIVACY_INFO = 10006  # wo  syncPrivacyToDevice(agreed)
    OTA_NFO = 10007  # ro  forceLoad only
    WASHING_LOG = 10008  # ro  forceLoad only, JSON
    VOICE_VOLUME = 10009  # wo  [independent]  setVoiceVolume(int) → JSON
    RPC_REQUEST = 10101  # wo  rpcRequest(method) → JSON
    RPC_RESPONSE = 10102  # -- MQTT push protocol 102, not a device DP
    VOICE_SWITCH = 10301  # wo  [independent]  setVoiceSwitchStatus(bool) → JSON
    VOICE_RECORD_INFO = 10302  # ro  cache-derived, auto JSON decoded
    VOICE_RECORD = 10303  # ro  query via getVoiceControlRecord(), JSON
    VOICE_RECORD_DELETE = 10304  # wo  [independent]  deleteVoiceControlRecord(id) → JSON


class RoborockB01Protocol(RoborockEnum):
    RPC_REQUEST = 101
    RPC_RESPONSE = 102
    ERROR_CODE = 120
    STATE = 121
    BATTERY = 122
    FAN_POWER = 123
    WATER_BOX_MODE = 124
    MAIN_BRUSH_LIFE = 125
    SIDE_BRUSH_LIFE = 126
    FILTER_LIFE = 127
    OFFLINE_STATUS = 135
    CLEAN_TIMES = 136
    CLEANING_PREFERENCE = 137
    CLEAN_TASK_TYPE = 138
    BACK_TYPE = 139
    DOCK_TASK_TYPE = 140
    CLEANING_PROGRESS = 141
    FC_STATE = 142
    START_CLEAN_TASK = 201
    START_BACK_DOCK_TASK = 202
    START_DOCK_TASK = 203
    PAUSE = 204
    RESUME = 205
    STOP = 206
    CEIP = 207


class RoborockB01Props(StrEnum):
    """Properties requested by the Roborock B01 model."""

    STATUS = "status"
    FAULT = "fault"
    WIND = "wind"
    WATER = "water"
    MODE = "mode"
    QUANTITY = "quantity"
    ALARM = "alarm"
    VOLUME = "volume"
    HYPA = "hypa"
    MAIN_BRUSH = "main_brush"
    SIDE_BRUSH = "side_brush"
    MOP_LIFE = "mop_life"
    MAIN_SENSOR = "main_sensor"
    NET_STATUS = "net_status"
    REPEAT_STATE = "repeat_state"
    TANK_STATE = "tank_state"
    SWEEP_TYPE = "sweep_type"
    CLEAN_PATH_PREFERENCE = "clean_path_preference"
    CLOTH_STATE = "cloth_state"
    TIME_ZONE = "time_zone"
    TIME_ZONE_INFO = "time_zone_info"
    LANGUAGE = "language"
    CLEANING_TIME = "cleaning_time"
    REAL_CLEAN_TIME = "real_clean_time"
    CLEANING_AREA = "cleaning_area"
    CUSTOM_TYPE = "custom_type"
    SOUND = "sound"
    WORK_MODE = "work_mode"
    STATION_ACT = "station_act"
    CHARGE_STATE = "charge_state"
    CURRENT_MAP_ID = "current_map_id"
    MAP_NUM = "map_num"
    DUST_ACTION = "dust_action"
    QUIET_IS_OPEN = "quiet_is_open"
    QUIET_BEGIN_TIME = "quiet_begin_time"
    QUIET_END_TIME = "quiet_end_time"
    CLEAN_FINISH = "clean_finish"
    VOICE_TYPE = "voice_type"
    VOICE_TYPE_VERSION = "voice_type_version"
    ORDER_TOTAL = "order_total"
    BUILD_MAP = "build_map"
    PRIVACY = "privacy"
    DUST_AUTO_STATE = "dust_auto_state"
    DUST_FREQUENCY = "dust_frequency"
    CHILD_LOCK = "child_lock"
    MULTI_FLOOR = "multi_floor"
    MAP_SAVE = "map_save"
    LIGHT_MODE = "light_mode"
    GREEN_LASER = "green_laser"
    DUST_BAG_USED = "dust_bag_used"
    ORDER_SAVE_MODE = "order_save_mode"
    MANUFACTURER = "manufacturer"
    BACK_TO_WASH = "back_to_wash"
    CHARGE_STATION_TYPE = "charge_station_type"
    PV_CUT_CHARGE = "pv_cut_charge"
    PV_CHARGING = "pv_charging"
    SERIAL_NUMBER = "serial_number"
    RECOMMEND = "recommend"
    ADD_SWEEP_STATUS = "add_sweep_status"


ROBOROCK_DATA_STATUS_PROTOCOL = [
    RoborockDataProtocol.ERROR_CODE,
    RoborockDataProtocol.STATE,
    RoborockDataProtocol.BATTERY,
    RoborockDataProtocol.FAN_POWER,
    RoborockDataProtocol.WATER_BOX_MODE,
    RoborockDataProtocol.CHARGE_STATUS,
]

ROBOROCK_DATA_CONSUMABLE_PROTOCOL = [
    RoborockDataProtocol.MAIN_BRUSH_WORK_TIME,
    RoborockDataProtocol.SIDE_BRUSH_WORK_TIME,
    RoborockDataProtocol.FILTER_WORK_TIME,
]


MAX_PAYLOAD_REPR_LEN = 1024


@dataclass
class RoborockMessage:
    protocol: RoborockMessageProtocol
    payload: bytes | None = None
    seq: int = field(default_factory=lambda: get_next_int(100000, 999999))
    version: bytes = b"1.0"
    random: int = field(default_factory=lambda: get_next_int(10000, 99999))
    timestamp: int = field(default_factory=lambda: get_timestamp())

    def __repr__(self) -> str:
        payload_repr = "None"
        if self.payload is not None:
            if isinstance(self.payload, (bytes, bytearray, str)) and len(self.payload) > MAX_PAYLOAD_REPR_LEN:
                r = repr(self.payload[:MAX_PAYLOAD_REPR_LEN])
                quote = r[-1]
                payload_repr = f"{r[:-1]}...{quote} (length: {len(self.payload)})"
            else:
                payload_repr = repr(self.payload)
        return (
            f"RoborockMessage(protocol={self.protocol}, payload={payload_repr}, "
            f"seq={self.seq}, version={self.version!r}, random={self.random}, "
            f"timestamp={self.timestamp})"
        )

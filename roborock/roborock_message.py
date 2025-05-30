from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field

from roborock import RoborockEnum
from roborock.util import get_next_int


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
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        raise ValueError("%s not a valid key for Data Protocol", key)


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
    START = 200  # rw
    PAUSE = 201  # rw
    SHUTDOWN = 202  # rw
    STATE = 203  # ro
    MODE = 204  # rw
    PROGRAM = 205  # rw
    CHILD_LOCK = 206  # rw
    TEMP = 207  # rw
    RINSE_TIMES = 208  # rw
    SPIN_LEVEL = 209  # rw
    DRYING_MODE = 210  # rw
    DETERGENT_SET = 211  # rw
    SOFTENER_SET = 212  # rw
    DETERGENT_TYPE = 213  # rw
    SOFTENER_TYPE = 214  # rw
    COUNTDOWN = 217  # rw
    WASHING_LEFT = 218  # ro
    DOORLOCK_STATE = 219  # ro
    ERROR = 220  # ro
    CUSTOM_PARAM_SAVE = 221  # rw
    CUSTOM_PARAM_GET = 222  # ro
    SOUND_SET = 223  # rw
    TIMES_AFTER_CLEAN = 224  # ro
    DEFAULT_SETTING = 225  # rw
    DETERGENT_EMPTY = 226  # ro
    SOFTENER_EMPTY = 227  # ro
    LIGHT_SETTING = 229  # rw
    DETERGENT_VOLUME = 230  # rw
    SOFTENER_VOLUME = 231  # rw
    APP_AUTHORIZATION = 232  # rw
    ID_QUERY = 10000
    F_C = 10001
    SND_STATE = 10004
    PRODUCT_INFO = 10005
    PRIVACY_INFO = 10006
    OTA_NFO = 10007
    WASHING_LOG = 10008
    RPC_REQ = 10101
    RPC_RESp = 10102


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


@dataclass
class MessageRetry:
    method: str
    retry_id: int


@dataclass
class RoborockMessage:
    protocol: RoborockMessageProtocol
    payload: bytes | None = None
    seq: int = field(default_factory=lambda: get_next_int(100000, 999999))
    version: bytes = b"1.0"
    random: int = field(default_factory=lambda: get_next_int(10000, 99999))
    timestamp: int = field(default_factory=lambda: math.floor(time.time()))
    message_retry: MessageRetry | None = None
    _parsed_payload: dict | None = None

    def get_payload(self) -> dict | None:
        if self.payload and not self._parsed_payload:
            self._parsed_payload = json.loads(self.payload.decode())
        return self._parsed_payload

    def get_request_id(self) -> int | None:
        payload = self.get_payload()
        if payload:
            for data_point_number, data_point in self._parsed_payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("id")
        return None

    def get_retry_id(self) -> int | None:
        if self.message_retry:
            return self.message_retry.retry_id
        return self.get_request_id()

    def get_method(self) -> str | None:
        if self.message_retry:
            return self.message_retry.method
        protocol = self.protocol
        payload = self.get_payload()
        if payload and protocol in [4, 5, 101, 102]:
            for data_point_number, data_point in self._parsed_payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("method")
        return None

    def get_params(self) -> list | dict | None:
        protocol = self.protocol
        payload = self.get_payload()
        if payload and protocol in [4, 101, 102]:
            for data_point_number, data_point in self._parsed_payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("params")
        return None

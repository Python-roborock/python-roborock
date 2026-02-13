"""Mock data for Roborock tests."""

import hashlib
import json
import pathlib
from typing import Any

# All data is based on a U.S. customer with a Roborock S7 MaxV Ultra
USER_EMAIL = "user@domain.com"

BASE_URL = "https://usiot.roborock.com"

USER_ID = "user123"
K_VALUE = "qiCNieZa"
USER_DATA = {
    "uid": 123456,
    "tokentype": "token_type",
    "token": "abc123",
    "rruid": "abc123",
    "region": "us",
    "countrycode": "1",
    "country": "US",
    "nickname": "user_nickname",
    "rriot": {
        "u": USER_ID,
        "s": "pass123",
        "h": "unknown123",
        "k": K_VALUE,
        "r": {
            "r": "US",
            "a": "https://api-us.roborock.com",
            "m": "tcp://mqtt-us.roborock.com:8883",  # Skip SSL code in MQTT client library
            "l": "https://wood-us.roborock.com",
        },
    },
    "tuyaDeviceState": 2,
    "avatarurl": "https://files.roborock.com/iottest/default_avatar.png",
}
LOCAL_KEY = "key123key123key1"  # 16 bytes / 128 bits
PRODUCT_ID = "product-id-123"
HOME_DATA_SCENES_RAW = [
    {
        "id": 1234567,
        "name": "My plan",
        "param": json.dumps(
            {
                "triggers": [],
                "action": {
                    "type": "S",
                    "items": [
                        {
                            "id": 5,
                            "type": "CMD",
                            "name": "",
                            "entityId": "EEEEEEEEEEEEEE",
                            "param": json.dumps(
                                {
                                    "id": 5,
                                    "method": "do_scenes_app_start",
                                    "params": [
                                        {
                                            "fan_power": 104,
                                            "water_box_mode": 200,
                                            "mop_mode": 300,
                                            "mop_template_id": 300,
                                            "repeat": 1,
                                            "auto_dustCollection": 1,
                                            "source": 101,
                                        }
                                    ],
                                }
                            ),
                            "finishDpIds": [130],
                        },
                        {
                            "id": 4,
                            "type": "CMD",
                            "name": "",
                            "entityId": "EEEEEEEEEEEEEE",
                            "param": json.dumps(
                                {
                                    "id": 4,
                                    "method": "do_scenes_segments",
                                    "params": {
                                        "data": [
                                            {
                                                "tid": "111111111111111111",
                                                "segs": [
                                                    {"sid": 19},
                                                    {"sid": 18},
                                                    {"sid": 22},
                                                    {"sid": 21},
                                                    {"sid": 16},
                                                ],
                                                "map_flag": 0,
                                                "fan_power": 105,
                                                "water_box_mode": 201,
                                                "mop_mode": 300,
                                                "mop_template_id": 300,
                                                "repeat": 1,
                                                "clean_order_mode": 1,
                                                "auto_dry": 1,
                                                "auto_dustCollection": 1,
                                                "region_num": 0,
                                            }
                                        ],
                                        "source": 101,
                                    },
                                }
                            ),
                            "finishDpIds": [130],
                        },
                    ],
                },
                "matchType": "NONE",
                "tagId": "4444",
            }
        ),
        "enabled": True,
        "extra": None,
        "type": "WORKFLOW",
    }
]

TESTDATA = pathlib.Path("tests/testdata")

PRODUCTS = {file.name: json.load(file.open(encoding="utf-8")) for file in TESTDATA.glob("home_data_product_*.json")}
DEVICES = {file.name: json.load(file.open(encoding="utf-8")) for file in TESTDATA.glob("home_data_device_*.json")}

# Products
A27_PRODUCT_DATA = PRODUCTS["home_data_product_a27.json"]
SC01_PRODUCT_DATA = PRODUCTS["home_data_product_sc01.json"]
SS07_PRODUCT_DATA = PRODUCTS["home_data_product_ss07.json"]
A102_PRODUCT_DATA = PRODUCTS["home_data_product_a102.json"]
A114_PRODUCT_DATA = PRODUCTS["home_data_product_a114.json"]

# Devices
S7_DEVICE_DATA = DEVICES["home_data_device_s7_maxv.json"]
Q7_DEVICE_DATA = DEVICES["home_data_device_q7.json"]
Q10_DEVICE_DATA = DEVICES["home_data_device_q10.json"]
ZEO_ONE_DEVICE_DATA = DEVICES["home_data_device_zeo_one.json"]
SAROS_10R_DEVICE_DATA = DEVICES["home_data_device_saros_10r.json"]


HOME_DATA_RAW: dict[str, Any] = {
    "id": 123456,
    "name": "My Home",
    "lon": None,
    "lat": None,
    "geoName": None,
    "products": [
        A27_PRODUCT_DATA,
    ],
    "devices": [
        S7_DEVICE_DATA,
    ],
    "receivedDevices": [],
    "rooms": [
        {"id": 2362048, "name": "Example room 1"},
        {"id": 2362044, "name": "Example room 2"},
        {"id": 2362041, "name": "Example room 3"},
    ],
}

CLEAN_RECORD = {
    "begin": 1672543330,
    "end": 1672544638,
    "duration": 1176,
    "area": 20965000,
    "error": 0,
    "complete": 1,
    "start_type": 2,
    "clean_type": 3,
    "finish_reason": 56,
    "dust_collection_status": 1,
    "avoid_count": 19,
    "wash_count": 2,
    "map_flag": 0,
}

CLEAN_SUMMARY = {
    "clean_time": 74382,
    "clean_area": 1159182500,
    "clean_count": 31,
    "dust_collection_count": 25,
    "records": [
        1672543330,
        1672458041,
    ],
}

CONSUMABLE = {
    "main_brush_work_time": 74382,
    "side_brush_work_time": 74383,
    "filter_work_time": 74384,
    "filter_element_work_time": 0,
    "sensor_dirty_time": 74385,
    "strainer_work_times": 65,
    "dust_collection_work_times": 25,
    "cleaning_brush_work_times": 66,
}

DND_TIMER = {
    "start_hour": 22,
    "start_minute": 0,
    "end_hour": 7,
    "end_minute": 0,
    "enabled": 1,
}

STATUS = {
    "msg_ver": 2,
    "msg_seq": 458,
    "state": 8,
    "battery": 100,
    "clean_time": 1176,
    "clean_area": 20965000,
    "error_code": 0,
    "map_present": 1,
    "in_cleaning": 0,
    "in_returning": 0,
    "in_fresh_state": 1,
    "lab_status": 1,
    "water_box_status": 1,
    "back_type": -1,
    "wash_phase": 0,
    "wash_ready": 0,
    "fan_power": 102,
    "dnd_enabled": 0,
    "map_status": 3,
    "is_locating": 0,
    "lock_status": 0,
    "water_box_mode": 203,
    "water_box_carriage_status": 1,
    "mop_forbidden_enable": 1,
    "camera_status": 3457,
    "is_exploring": 0,
    "home_sec_status": 0,
    "home_sec_enable_password": 0,
    "adbumper_status": [0, 0, 0],
    "water_shortage_status": 0,
    "dock_type": 3,
    "dust_collection_status": 0,
    "auto_dust_collection": 1,
    "avoid_count": 19,
    "mop_mode": 300,
    "debug_mode": 0,
    "collision_avoid_status": 1,
    "switch_map_mode": 0,
    "dock_error_status": 0,
    "charge_status": 1,
    "unsave_map_reason": 0,
    "unsave_map_flag": 0,
}

BASE_URL_REQUEST = {
    "code": 200,
    "msg": "success",
    "data": {"url": "https://sample.com", "countrycode": 1, "country": "US"},
}

GET_CODE_RESPONSE = {"code": 200, "msg": "success", "data": None}
HASHED_USER = hashlib.md5((USER_ID + ":" + K_VALUE).encode()).hexdigest()[2:10]
MQTT_PUBLISH_TOPIC = f"rr/m/o/{USER_ID}/{HASHED_USER}/{PRODUCT_ID}"
TEST_LOCAL_API_HOST = "1.1.1.1"

NETWORK_INFO = {
    "ip": TEST_LOCAL_API_HOST,
    "ssid": "test_wifi",
    "mac": "aa:bb:cc:dd:ee:ff",
    "bssid": "aa:bb:cc:dd:ee:ff",
    "rssi": -50,
}

APP_GET_INIT_STATUS = {
    "local_info": {
        "name": "custom_A.03.0069_FCC",
        "bom": "A.03.0069",
        "location": "us",
        "language": "en",
        "wifiplan": "0x39",
        "timezone": "US/Pacific",
        "logserver": "awsusor0.fds.api.xiaomi.com",
        "featureset": 1,
    },
    "feature_info": [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125],
    "new_feature_info": 633887780925447,
    "new_feature_info2": 8192,
    "new_feature_info_str": "0000000000002000",
    "status_info": {
        "state": 8,
        "battery": 100,
        "clean_time": 5610,
        "clean_area": 96490000,
        "error_code": 0,
        "in_cleaning": 0,
        "in_returning": 0,
        "in_fresh_state": 1,
        "lab_status": 1,
        "water_box_status": 0,
        "map_status": 3,
        "is_locating": 0,
        "lock_status": 0,
        "water_box_mode": 204,
        "distance_off": 0,
        "water_box_carriage_status": 0,
        "mop_forbidden_enable": 0,
    },
}

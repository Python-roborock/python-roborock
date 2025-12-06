"""Test cases for the containers module."""

import dataclasses
from dataclasses import dataclass
from typing import Any

import pytest
from syrupy import SnapshotAssertion

from roborock import CleanRecord, CleanSummary, Consumable, DnDTimer, HomeData, S7MaxVStatus, UserData
from roborock.data import RoborockBase, RoborockCategory
from roborock.data.b01_q7 import (
    B01Fault,
    B01Props,
    SCWindMapping,
    WorkStatusMapping,
)
from roborock.data.containers import _camelize, _decamelize
from roborock.data.v1 import (
    MultiMapsList,
    RoborockDockErrorCode,
    RoborockDockTypeCode,
    RoborockErrorCode,
    RoborockFanSpeedS7MaxV,
    RoborockMopIntensityS7,
    RoborockMopModeS7,
    RoborockStateCode,
)

from .mock_data import (
    CLEAN_RECORD,
    CLEAN_SUMMARY,
    CONSUMABLE,
    DND_TIMER,
    HOME_DATA_RAW,
    K_VALUE,
    LOCAL_KEY,
    PRODUCT_ID,
    STATUS,
    USER_DATA,
)


@dataclass
class SimpleObject(RoborockBase):
    """Simple object for testing serialization."""

    name: str | None = None
    value: int | None = None


@dataclass
class ComplexObject(RoborockBase):
    """Complex object for testing serialization."""

    simple: SimpleObject | None = None
    items: list[str] | None = None
    value: int | None = None
    nested_dict: dict[str, SimpleObject] | None = None
    nested_list: list[SimpleObject] | None = None
    any: Any | None = None
    nested_int_dict: dict[int, SimpleObject] | None = None


@dataclass
class BoolFeatures(RoborockBase):
    """Complex object for testing serialization."""

    my_flag_supported: bool | None = None
    my_flag_2_supported: bool | None = None
    is_ces_2022_supported: bool | None = None


def test_simple_object() -> None:
    """Test serialization and deserialization of a simple object."""

    obj = SimpleObject(name="Test", value=42)
    serialized = obj.as_dict()
    assert serialized == {"name": "Test", "value": 42}
    deserialized = SimpleObject.from_dict(serialized)
    assert deserialized.name == "Test"
    assert deserialized.value == 42


def test_complex_object() -> None:
    """Test serialization and deserialization of a complex object."""
    simple = SimpleObject(name="Nested", value=100)
    obj = ComplexObject(
        simple=simple,
        items=["item1", "item2"],
        value=200,
        nested_dict={
            "nested1": SimpleObject(name="Nested1", value=1),
            "nested2": SimpleObject(name="Nested2", value=2),
        },
        nested_int_dict={
            10: SimpleObject(name="IntKey1", value=10),
        },
        nested_list=[SimpleObject(name="Nested3", value=3), SimpleObject(name="Nested4", value=4)],
        any="This can be anything",
    )
    serialized = obj.as_dict()
    assert serialized == {
        "simple": {"name": "Nested", "value": 100},
        "items": ["item1", "item2"],
        "value": 200,
        "nestedDict": {
            "nested1": {"name": "Nested1", "value": 1},
            "nested2": {"name": "Nested2", "value": 2},
        },
        "nestedIntDict": {
            10: {"name": "IntKey1", "value": 10},
        },
        "nestedList": [
            {"name": "Nested3", "value": 3},
            {"name": "Nested4", "value": 4},
        ],
        "any": "This can be anything",
    }
    deserialized = ComplexObject.from_dict(serialized)
    assert deserialized.simple.name == "Nested"
    assert deserialized.simple.value == 100
    assert deserialized.items == ["item1", "item2"]
    assert deserialized.value == 200
    assert deserialized.nested_dict == {
        "nested1": SimpleObject(name="Nested1", value=1),
        "nested2": SimpleObject(name="Nested2", value=2),
    }
    assert deserialized.nested_int_dict == {
        10: SimpleObject(name="IntKey1", value=10),
    }
    assert deserialized.nested_list == [
        SimpleObject(name="Nested3", value=3),
        SimpleObject(name="Nested4", value=4),
    ]
    assert deserialized.any == "This can be anything"


@pytest.mark.parametrize(
    ("data"),
    [
        {
            "nested_int_dict": {10: {"name": "IntKey1", "value": 10}},
        },
        {
            "nested_int_dict": {"10": {"name": "IntKey1", "value": 10}},
        },
    ],
)
def test_from_dict_key_types(data: dict) -> None:
    """Test serialization and deserialization of a complex object."""
    obj = ComplexObject.from_dict(data)
    assert obj.nested_int_dict == {
        10: SimpleObject(name="IntKey1", value=10),
    }


def test_ignore_unknown_keys() -> None:
    """Test that we don't fail on unknown keys."""
    data = {
        "ignored_key": "This key should be ignored",
        "name": "named_object",
        "value": 42,
    }
    deserialized = SimpleObject.from_dict(data)
    assert deserialized.name == "named_object"
    assert deserialized.value == 42


def test_user_data():
    ud = UserData.from_dict(USER_DATA)
    assert ud.uid == 123456
    assert ud.tokentype == "token_type"
    assert ud.token == "abc123"
    assert ud.rruid == "abc123"
    assert ud.region == "us"
    assert ud.country == "US"
    assert ud.countrycode == "1"
    assert ud.nickname == "user_nickname"
    assert ud.rriot.u == "user123"
    assert ud.rriot.s == "pass123"
    assert ud.rriot.h == "unknown123"
    assert ud.rriot.k == K_VALUE
    assert ud.rriot.r.r == "US"
    assert ud.rriot.r.a == "https://api-us.roborock.com"
    assert ud.rriot.r.m == "tcp://mqtt-us.roborock.com:8883"
    assert ud.rriot.r.l == "https://wood-us.roborock.com"
    assert ud.tuya_device_state == 2
    assert ud.avatarurl == "https://files.roborock.com/iottest/default_avatar.png"


def test_home_data():
    hd = HomeData.from_dict(HOME_DATA_RAW)
    assert hd.id == 123456
    assert hd.name == "My Home"
    assert hd.lon is None
    assert hd.lat is None
    assert hd.geo_name is None
    product = hd.products[0]
    assert product.id == PRODUCT_ID
    assert product.name == "Roborock S7 MaxV"
    assert product.code == "a27"
    assert product.model == "roborock.vacuum.a27"
    assert product.icon_url is None
    assert product.attribute is None
    assert product.capability == 0
    assert product.category == RoborockCategory.VACUUM
    schema = product.schema
    assert schema[0].id == "101"
    assert schema[0].name == "rpc_request"
    assert schema[0].code == "rpc_request_code"
    assert schema[0].mode == "rw"
    assert schema[0].type == "RAW"
    assert schema[0].product_property is None
    assert schema[0].desc is None
    device = hd.devices[0]
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.attribute is None
    assert device.active_time == 1672364449
    assert device.local_key == LOCAL_KEY
    assert device.runtime_env is None
    assert device.time_zone_id == "America/Los_Angeles"
    assert device.icon_url == "no_url"
    assert device.product_id == "product-id-123"
    assert device.lon is None
    assert device.lat is None
    assert not device.share
    assert device.share_time is None
    assert device.online
    assert device.fv == "02.56.02"
    assert device.pv == "1.0"
    assert device.room_id == 2362003
    assert device.tuya_uuid is None
    assert not device.tuya_migrated
    assert device.extra == '{"RRPhotoPrivacyVersion": "1"}'
    assert device.sn == "abc123"
    assert device.feature_set == "2234201184108543"
    assert device.new_feature_set == "0000000000002041"
    # status = device.device_status
    # assert status.name ==
    assert device.silent_ota_switch
    assert hd.rooms[0].id == 2362048
    assert hd.rooms[0].name == "Example room 1"


def test_serialize_and_unserialize():
    ud = UserData.from_dict(USER_DATA)
    ud_dict = ud.as_dict()
    assert ud_dict == USER_DATA


def test_consumable():
    c = Consumable.from_dict(CONSUMABLE)
    assert c.main_brush_work_time == 74382
    assert c.side_brush_work_time == 74383
    assert c.filter_work_time == 74384
    assert c.filter_element_work_time == 0
    assert c.sensor_dirty_time == 74385
    assert c.strainer_work_times == 65
    assert c.dust_collection_work_times == 25
    assert c.cleaning_brush_work_times == 66


def test_status():
    s = S7MaxVStatus.from_dict(STATUS)
    assert s.msg_ver == 2
    assert s.msg_seq == 458
    assert s.state == RoborockStateCode.charging
    assert s.battery == 100
    assert s.clean_time == 1176
    assert s.clean_area == 20965000
    assert s.square_meter_clean_area == 21.0
    assert s.error_code == RoborockErrorCode.none
    assert s.map_present == 1
    assert s.in_cleaning == 0
    assert s.in_returning == 0
    assert s.in_fresh_state == 1
    assert s.lab_status == 1
    assert s.water_box_status == 1
    assert s.back_type == -1
    assert s.wash_phase == 0
    assert s.wash_ready == 0
    assert s.fan_power == 102
    assert s.dnd_enabled == 0
    assert s.map_status == 3
    assert s.current_map == 0
    assert s.is_locating == 0
    assert s.lock_status == 0
    assert s.water_box_mode == 203
    assert s.water_box_carriage_status == 1
    assert s.mop_forbidden_enable == 1
    assert s.camera_status == 3457
    assert s.is_exploring == 0
    assert s.home_sec_status == 0
    assert s.home_sec_enable_password == 0
    assert s.adbumper_status == [0, 0, 0]
    assert s.water_shortage_status == 0
    assert s.dock_type == RoborockDockTypeCode.empty_wash_fill_dock
    assert s.dust_collection_status == 0
    assert s.auto_dust_collection == 1
    assert s.avoid_count == 19
    assert s.mop_mode == 300
    assert s.debug_mode == 0
    assert s.collision_avoid_status == 1
    assert s.switch_map_mode == 0
    assert s.dock_error_status == RoborockDockErrorCode.ok
    assert s.charge_status == 1
    assert s.unsave_map_reason == 0
    assert s.unsave_map_flag == 0
    assert s.fan_power == RoborockFanSpeedS7MaxV.balanced
    assert s.mop_mode == RoborockMopModeS7.standard
    assert s.water_box_mode == RoborockMopIntensityS7.intense


def test_current_map() -> None:
    """Test the current map logic based on map status."""
    s = S7MaxVStatus.from_dict(STATUS)
    assert s.map_status == 3
    assert s.current_map == 0

    s.map_status = 7
    assert s.current_map == 1

    s.map_status = 11
    assert s.current_map == 2

    s.map_status = None
    assert not s.current_map


def test_dnd_timer():
    dnd = DnDTimer.from_dict(DND_TIMER)
    assert dnd.start_hour == 22
    assert dnd.start_minute == 0
    assert dnd.end_hour == 7
    assert dnd.end_minute == 0
    assert dnd.enabled == 1


def test_clean_summary():
    cs = CleanSummary.from_dict(CLEAN_SUMMARY)
    assert cs.clean_time == 74382
    assert cs.clean_area == 1159182500
    assert cs.square_meter_clean_area == 1159.2
    assert cs.clean_count == 31
    assert cs.dust_collection_count == 25
    assert cs.records
    assert len(cs.records) == 2
    assert cs.records[1] == 1672458041


def test_clean_record():
    cr = CleanRecord.from_dict(CLEAN_RECORD)
    assert cr.begin == 1672543330
    assert cr.end == 1672544638
    assert cr.duration == 1176
    assert cr.area == 20965000
    assert cr.square_meter_area == 21.0
    assert cr.error == 0
    assert cr.complete == 1
    assert cr.start_type == 2
    assert cr.clean_type == 3
    assert cr.finish_reason == 56
    assert cr.dust_collection_status == 1
    assert cr.avoid_count == 19
    assert cr.wash_count == 2
    assert cr.map_flag == 0


def test_no_value():
    modified_status = STATUS.copy()
    modified_status["dock_type"] = 9999
    s = S7MaxVStatus.from_dict(modified_status)
    assert s.dock_type == RoborockDockTypeCode.unknown
    assert -9999 not in RoborockDockTypeCode.keys()
    assert "missing" not in RoborockDockTypeCode.values()


def test_b01props_deserialization():
    """Test that B01Props can be deserialized after its module is dynamically imported."""

    B01_PROPS_MOCK_DATA = {
        "status": 6,
        "fault": 510,
        "wind": 3,
        "water": 2,
        "mode": 1,
        "quantity": 1,
        "alarm": 0,
        "volume": 60,
        "hypa": 90,
        "mainBrush": 80,
        "sideBrush": 70,
        "mopLife": 60,
        "mainSensor": 50,
        "netStatus": {
            "rssi": "-60",
            "loss": 1,
            "ping": 20,
            "ip": "192.168.1.102",
            "mac": "BB:CC:DD:EE:FF:00",
            "ssid": "MyOtherWiFi",
            "frequency": 2.4,
            "bssid": "00:FF:EE:DD:CC:BB",
        },
        "repeatState": 1,
        "tankState": 0,
        "sweepType": 0,
        "cleanPathPreference": 1,
        "clothState": 1,
        "timeZone": -5,
        "timeZoneInfo": "America/New_York",
        "language": 2,
        "cleaningTime": 1500,
        "realCleanTime": 1400,
        "cleaningArea": 600000,
        "customType": 1,
        "sound": 0,
        "workMode": 3,
        "stationAct": 1,
        "chargeState": 0,
        "currentMapId": 2,
        "mapNum": 3,
        "dustAction": 0,
        "quietIsOpen": 1,
        "quietBeginTime": 23,
        "quietEndTime": 7,
        "cleanFinish": 0,
        "voiceType": 2,
        "voiceTypeVersion": 1,
        "orderTotal": {"total": 12, "enable": 0},
        "buildMap": 0,
        "privacy": {
            "aiRecognize": 1,
            "dirtRecognize": 1,
            "petRecognize": 1,
            "carpetTurbo": 1,
            "carpetAvoid": 1,
            "carpetShow": 1,
            "mapUploads": 1,
            "aiAgent": 1,
            "aiAvoidance": 1,
            "recordUploads": 1,
            "alongFloor": 1,
            "autoUpgrade": 1,
        },
        "dustAutoState": 0,
        "dustFrequency": 1,
        "childLock": 1,
        "multiFloor": 0,
        "mapSave": 0,
        "lightMode": 0,
        "greenLaser": 0,
        "dustBagUsed": 1,
        "orderSaveMode": 0,
        "manufacturer": "Roborock-Test",
        "backToWash": 0,
        "chargeStationType": 2,
        "pvCutCharge": 1,
        "pvCharging": {"status": 1, "beginTime": 10, "endTime": 18},
        "serialNumber": "987654321",
        "recommend": {"sill": 0, "wall": 0, "roomId": [4, 5, 6]},
        "addSweepStatus": 1,
    }

    deserialized = B01Props.from_dict(B01_PROPS_MOCK_DATA)
    assert isinstance(deserialized, B01Props)
    assert deserialized.fault == B01Fault.F_510
    assert deserialized.status == WorkStatusMapping.SWEEP_MOPING_2
    assert deserialized.wind == SCWindMapping.SUPER_STRONG
    assert deserialized.net_status.ip == "192.168.1.102"


def test_multi_maps_list_info(snapshot: SnapshotAssertion) -> None:
    """Test that MultiMapsListInfo can be deserialized correctly."""
    data = {
        "max_multi_map": 4,
        "max_bak_map": 1,
        "multi_map_count": 2,
        "map_info": [
            {
                "mapFlag": 0,
                "add_time": 1757636125,
                "length": 10,
                "name": "Downstairs",
                "bak_maps": [{"mapFlag": 4, "add_time": 1739205442}],
                "rooms": [
                    {"id": 16, "tag": 12, "iot_name_id": "6990322", "iot_name": "Room"},
                    {"id": 17, "tag": 15, "iot_name_id": "7140977", "iot_name": "Room"},
                    {"id": 18, "tag": 12, "iot_name_id": "6985623", "iot_name": "Room"},
                    {"id": 19, "tag": 14, "iot_name_id": "6990378", "iot_name": "Room"},
                    {"id": 20, "tag": 10, "iot_name_id": "7063728", "iot_name": "Room"},
                    {"id": 22, "tag": 12, "iot_name_id": "6995506", "iot_name": "Room"},
                    {"id": 23, "tag": 15, "iot_name_id": "7140979", "iot_name": "Room"},
                    {"id": 25, "tag": 13, "iot_name_id": "6990383", "iot_name": "Room"},
                    {"id": 24, "tag": -1, "iot_name_id": "-1", "iot_name": "Room"},
                ],
                "furnitures": [
                    {"id": 1, "type": 46, "subtype": 2},
                    {"id": 2, "type": 47, "subtype": 0},
                    {"id": 3, "type": 56, "subtype": 0},
                    {"id": 4, "type": 43, "subtype": 0},
                    {"id": 5, "type": 44, "subtype": 0},
                    {"id": 6, "type": 44, "subtype": 0},
                    {"id": 7, "type": 44, "subtype": 0},
                    {"id": 8, "type": 46, "subtype": 0},
                    {"id": 9, "type": 46, "subtype": 0},
                ],
            },
            {
                "mapFlag": 1,
                "add_time": 1734283706,
                "length": 5,
                "name": "Foyer",
                "bak_maps": [{"mapFlag": 5, "add_time": 1728184107}],
                "rooms": [],
                "furnitures": [],
            },
        ],
    }
    deserialized = MultiMapsList.from_dict(data)
    assert isinstance(deserialized, MultiMapsList)
    assert deserialized == snapshot


def test_accurate_map_flag() -> None:
    """Test that we parse the map flag accurately."""
    s = S7MaxVStatus.from_dict(STATUS)
    assert s.current_map == 0
    s = S7MaxVStatus.from_dict(
        {
            **STATUS,
            "map_status": 252,  # Code for no map
        }
    )
    assert s.current_map is None


def test_boolean_features() -> None:
    """Test serialization and deserialization of BoolFeatures."""
    obj = BoolFeatures(my_flag_supported=True, my_flag_2_supported=False, is_ces_2022_supported=True)
    serialized = obj.as_dict()
    assert serialized == {
        "myFlagSupported": True,
        "myFlag2Supported": False,
        "isCes2022Supported": True,
    }
    deserialized = BoolFeatures.from_dict(serialized)
    assert dataclasses.asdict(deserialized) == {
        "my_flag_supported": True,
        "my_flag_2_supported": False,
        "is_ces_2022_supported": True,
    }


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("simpleTest", "simple_test"),
        ("testValue", "test_value"),
        ("anotherExampleHere", "another_example_here"),
        ("isCes2022Supported", "is_ces_2022_supported"),
        ("isThreeDMappingInnerTestSupported", "is_three_d_mapping_inner_test_supported"),
    ],
)
def test_decamelize_function(input_str: str, expected: str) -> None:
    """Test the _decamelize function."""

    assert _decamelize(input_str) == expected
    assert _camelize(expected) == input_str

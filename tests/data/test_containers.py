"""Test cases for the containers module."""

import dataclasses
from dataclasses import dataclass
from typing import Any

import pytest

from roborock.data.containers import (
    HomeData,
    HomeDataDevice,
    RoborockBase,
    RoborockCategory,
    UserData,
    _camelize,
    _decamelize,
)
from tests.mock_data import (
    HOME_DATA_RAW,
    K_VALUE,
    LOCAL_KEY,
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
    assert product.id == "product-id-s7-maxv"
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
    assert product.supported_schema_codes == {
        "additional_props",
        "battery",
        "charge_status",
        "drying_status",
        "error_code",
        "fan_power",
        "filter_life",
        "main_brush_life",
        "rpc_request_code",
        "rpc_response",
        "side_brush_life",
        "state",
        "task_cancel_in_motion",
        "task_cancel_low_power",
        "task_complete",
        "water_box_mode",
    }

    device = hd.devices[0]
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.attribute is None
    assert device.active_time == 1672364449
    assert device.local_key == LOCAL_KEY
    assert device.runtime_env is None
    assert device.time_zone_id == "America/Los_Angeles"
    assert device.icon_url == "no_url"
    assert device.product_id == "product-id-s7-maxv"
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


def test_offline_device() -> None:
    """Test that a HomeDataDevice response from an offline device is handled correctly."""
    data = {
        "duid": "xxxxxx",
        "name": "S6 Pure",
        "localKey": "yyyyy",
        "productId": "zzzzz",
        "activeTime": 1765277892,
        "timeZoneId": "Europe/Moscow",
        "iconUrl": "",
        "share": False,
        "online": False,
        "pv": "1.0",
        "tuyaMigrated": False,
        "extra": "{}",
        "deviceStatus": {},
        "silentOtaSwitch": False,
        "f": False,
    }
    device = HomeDataDevice.from_dict(data)
    assert device.duid == "xxxxxx"
    assert device.name == "S6 Pure"
    assert device.local_key == "yyyyy"
    assert device.product_id == "zzzzz"
    assert device.active_time == 1765277892
    assert device.time_zone_id == "Europe/Moscow"
    assert not device.online
    assert device.fv is None

from roborock import CleanRecord, CleanSummary, Consumable, DnDTimer, HomeData, S7MaxVStatus, UserData
from roborock.code_mappings import (
    RoborockCategory,
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
    LOCAL_KEY,
    PRODUCT_ID,
    STATUS,
    USER_DATA,
)


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
    assert ud.rriot.k == "domain123"
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

"""Test cases for the containers module."""

from syrupy import SnapshotAssertion

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
from roborock.data.v1.v1_code_mappings import ClearWaterBoxStatus, DirtyWaterBoxStatus, DustBagStatus
from roborock.data.v1.v1_containers import (
    AppInitStatus,
    CleanRecord,
    CleanSummary,
    Consumable,
    DnDTimer,
    S7MaxVStatus,
    StatusV2,
)
from tests.mock_data import (
    CLEAN_RECORD,
    CLEAN_SUMMARY,
    CONSUMABLE,
    DND_TIMER,
    STATUS,
)


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
    assert s.dss == 169
    assert s.clear_water_box_status == ClearWaterBoxStatus.okay
    assert s.dirty_water_box_status == DirtyWaterBoxStatus.okay
    assert s.dust_bag_status == DustBagStatus.okay
    assert s.water_box_filter_status == 0
    assert s.clean_fluid_status is None
    assert s.hatch_door_status == 0
    assert s.dock_cool_fan_status == 0


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


def test_status_v2() -> None:
    """Test that StatusV2 can be created from a dictionary."""
    s = StatusV2.from_dict(STATUS)
    assert s.msg_ver == 2
    assert s.msg_seq == 458
    assert s.state == RoborockStateCode.charging
    assert s.battery == 100
    assert s.clean_time == 1176
    assert s.clean_area == 20965000
    assert s.square_meter_clean_area == 21.0
    assert s.error_code == RoborockErrorCode.none
    assert s.error_code_name == "none"
    assert s.state_name == "charging"
    assert s.map_present == 1
    assert s.in_cleaning == 0
    assert s.fan_power == 102
    assert s.water_box_mode == 203
    assert s.mop_mode == 300
    assert s.dock_type == RoborockDockTypeCode.empty_wash_fill_dock
    assert s.dock_error_status == RoborockDockErrorCode.ok
    assert s.current_map == 0


def test_status_v2_current_map() -> None:
    """Test the current map logic based on map status for StatusV2."""
    s = StatusV2.from_dict(STATUS)
    assert s.map_status == 3
    assert s.current_map == 0

    s.map_status = 7
    assert s.current_map == 1

    s.map_status = 11
    assert s.current_map == 2

    s.map_status = None
    assert s.current_map is None


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


def test_partial_app_init_status() -> None:
    """Test that a partial AppInitStatus response is handled correctly."""
    app_init_status = AppInitStatus.from_dict(
        {
            "local_info": {
                "name": "custom_A.03.0096_FCC",
                "bom": "A.03.0096",
                "location": "us",
                "language": "en",
                "wifiplan": "US",
                "timezone": "US/Pacific",
                "logserver": "awsusor0.fds.api.xiaomi.com",
                "featureset": 1,
            },
            "feature_info": [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125],
            "new_feature_info": 10738169343,
            "status_info": {
                "state": 8,
                "battery": 100,
                "clean_time": 251,
                "clean_area": 3847500,
                "error_code": 0,
                "in_cleaning": 0,
                "in_returning": 0,
                "in_fresh_state": 1,
                "lab_status": 3,
                "water_box_status": 0,
                "map_status": 7,
                "is_locating": 0,
                "lock_status": 0,
                "water_box_mode": 203,
                "distance_off": 0,
                "water_box_carriage_status": 0,
                "mop_forbidden_enable": 0,
                "camera_status": 3495,
                "is_exploring": 0,
                "home_sec_status": 0,
                "home_sec_enable_password": 1,
                "adbumper_status": [0, 0, 0],
            },
        }
    )
    assert app_init_status.local_info.name == "custom_A.03.0096_FCC"
    assert app_init_status.feature_info == [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125]
    assert app_init_status.new_feature_info_str == ""

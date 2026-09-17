"""Test cases for the containers module."""

import json
import logging

import pytest

from roborock.data.b01_q7 import (
    B01Fault,
    B01Props,
    CleanPathPreferenceMapping,
    CleanRecordDetail,
    CleanRecordList,
    CleanRepeatMapping,
    DustCollectionStateMapping,
    SCWindMapping,
    StationStateMapping,
    WorkStatusMapping,
)
from roborock.data.code_mappings import completed_warnings


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (0, WorkStatusMapping.SLEEPING),
        (1, WorkStatusMapping.WAITING_FOR_ORDERS),
        (2, WorkStatusMapping.PAUSED),
        (3, WorkStatusMapping.DOCKING),
        (4, WorkStatusMapping.CHARGING),
        (5, WorkStatusMapping.SWEEP_MOPING),
        (6, WorkStatusMapping.SWEEP_MOPING_2),
        (7, WorkStatusMapping.MOPING),
        (8, WorkStatusMapping.UPDATING),
        (9, WorkStatusMapping.MOP_CLEANING),
        (10, WorkStatusMapping.MOP_AIRDRYING),
        (11, WorkStatusMapping.WORKING_SLEEP),
    ],
)
def test_work_status_mapping(code: int, expected: WorkStatusMapping) -> None:
    """Test every Q7 work status handled by the official app bundle."""
    assert WorkStatusMapping.from_code(code) is expected


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
    assert deserialized.wind == SCWindMapping.STRONG
    assert deserialized.net_status is not None
    assert deserialized.net_status.ip == "192.168.1.102"
    assert deserialized.repeat_state == CleanRepeatMapping.TWO
    assert deserialized.clean_path_preference == CleanPathPreferenceMapping.DEEP
    assert deserialized.repeat_state_name == "two"
    assert deserialized.clean_path_preference_name == "deep"


def test_b01props_deserialization_working_sleep_status():
    """Test the working-sleep status reported by Q7 devices."""
    deserialized = B01Props.from_dict(
        {
            "status": 11,
            "quantity": 87,
            "wind": 2,
        }
    )

    assert isinstance(deserialized, B01Props)
    assert deserialized.status == WorkStatusMapping.WORKING_SLEEP
    assert deserialized.status_name == "working_sleep"
    assert deserialized.quantity == 87
    assert deserialized.wind == SCWindMapping.STANDARD


def test_b01props_deserialization_unknown_work_status(caplog: pytest.LogCaptureFixture):
    """Test that an unrecognized future work status does not break the response."""
    warning = "999 is not a valid code for WorkStatusMapping"
    completed_warnings.discard(warning)
    with caplog.at_level(logging.WARNING):
        deserialized = B01Props.from_dict(
            {
                "status": 999,
                "quantity": 87,
                "wind": 2,
            }
        )

    assert isinstance(deserialized, B01Props)
    assert deserialized.status == WorkStatusMapping.UNKNOWN
    assert deserialized.status_name == "unknown"
    assert deserialized.quantity == 87
    assert deserialized.wind == SCWindMapping.STANDARD
    assert warning in caplog.text
    assert "Failed to convert status" not in caplog.text


@pytest.mark.parametrize("station_key,dust_key", [("station_act", "dust_action"), ("stationAct", "dustAction")])
@pytest.mark.parametrize(
    ("station_code", "dust_code", "expected_station", "expected_dust"),
    [
        (0, 0, StationStateMapping.idle, DustCollectionStateMapping.idle),
        (3, 1, StationStateMapping.collecting_dust, DustCollectionStateMapping.collecting_dust),
    ],
)
def test_b01props_dock_states(
    station_key: str,
    dust_key: str,
    station_code: int,
    dust_code: int,
    expected_station: StationStateMapping,
    expected_dust: DustCollectionStateMapping,
) -> None:
    """Decode dock states and preserve integer values when serializing them."""
    props = B01Props.from_dict({station_key: station_code, dust_key: dust_code})

    assert props.station_act is expected_station
    assert props.dust_action is expected_dust
    serialized = json.loads(json.dumps(props.as_dict()))
    assert serialized == {"stationAct": station_code, "dustAction": dust_code}
    restored = B01Props.from_dict(serialized)
    assert restored.station_act is expected_station
    assert restored.dust_action is expected_dust


@pytest.mark.parametrize("station_code,dust_code", [(-1, -1), (1, 2), (999, 999)])
def test_b01props_unknown_dock_states(station_code: int, dust_code: int, caplog: pytest.LogCaptureFixture) -> None:
    """Unknown dock states must not appear idle or discard other properties."""
    props = B01Props.from_dict({"station_act": station_code, "dust_action": dust_code, "quantity": 87})

    assert props.station_act is StationStateMapping.unknown
    assert props.dust_action is DustCollectionStateMapping.unknown
    assert props.quantity == 87
    assert "Failed to convert" not in caplog.text


@pytest.mark.parametrize("payload", [{}, {"station_act": None, "dust_action": None}])
def test_b01props_missing_dock_states(payload: dict[str, None]) -> None:
    """Missing dock states stay absent rather than becoming idle or unknown."""
    props = B01Props.from_dict(payload)

    assert props.station_act is None
    assert props.dust_action is None
    assert props.as_dict() == {}


def test_b01_q7_clean_record_list_parses_detail_fields():
    payload = {
        "total_time": 34980,
        "total_area": 28540,
        "total_count": 1,
        "record_list": [
            {
                "url": "/userdata/record_map/1766368207_1766368283_0_clean_map.bin",
                "detail": json.dumps(
                    {
                        "record_start_time": 1766368207,
                        "method": 0,
                        "record_use_time": 60,
                        "clean_count": 1,
                        "record_clean_area": 85,
                        "record_clean_mode": 0,
                        "record_clean_way": 0,
                        "record_task_status": 20,
                        "record_faultcode": 0,
                        "record_dust_num": 0,
                        "clean_current_map": 0,
                        "record_map_url": "/userdata/record_map/1766368207_1766368283_0_clean_map.bin",
                    }
                ),
            }
        ],
    }

    parsed = CleanRecordList.from_dict(payload)
    assert isinstance(parsed, CleanRecordList)
    assert parsed.record_list[0].url == "/userdata/record_map/1766368207_1766368283_0_clean_map.bin"

    detail_dict = json.loads(parsed.record_list[0].detail or "{}")
    detail = CleanRecordDetail.from_dict(detail_dict)
    assert isinstance(detail, CleanRecordDetail)
    assert detail.record_start_time == 1766368207
    assert detail.record_use_time == 60
    assert detail.record_clean_area == 85
    assert detail.record_clean_mode == 0
    assert detail.record_task_status == 20
    assert detail.record_map_url == "/userdata/record_map/1766368207_1766368283_0_clean_map.bin"
    assert detail.method == 0
    assert detail.clean_count == 1
    assert detail.record_clean_way == 0
    assert detail.record_faultcode == 0
    assert detail.record_dust_num == 0
    assert detail.clean_current_map == 0

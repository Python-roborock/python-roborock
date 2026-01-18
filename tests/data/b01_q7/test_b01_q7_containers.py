"""Test cases for the containers module."""

from roborock.data.b01_q7 import (
    B01Fault,
    B01Props,
    SCWindMapping,
    WorkStatusMapping,
)


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

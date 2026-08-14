"""Test mower data containers."""

import dataclasses

from roborock.data import MowerStatus, RoborockMowerStateCode
from roborock.roborock_message import RoborockMowerDataProtocol


def test_mower_status_from_dict() -> None:
    status = MowerStatus.from_dict(
        {
            "error_code": 0,
            "battery": 82,
            "mow_state": 3,
            "mowHeight": 70,
            "gpsCoordinate": {"latitude": 1, "longitude": 2},
            "unknown": "ignored",
        }
    )

    assert status.error_code == 0
    assert status.battery == 82
    assert status.mow_state is RoborockMowerStateCode.map_undock_fault
    assert status.mow_height == 70
    assert status.gps_coordinate == {"latitude": 1, "longitude": 2}


def test_mower_status_from_dps() -> None:
    status = MowerStatus.from_dps(
        {
            "121": 78,
            122: 1,
            "123": 58,
            "133": 1,
            "139": 55,
            "142": "<redacted-gps>",
            "145": 1,
            "unknown": "ignored",
            "999": "ignored",
        }
    )

    assert status.battery == 78
    assert status.mow_type == 1
    assert status.mow_state is RoborockMowerStateCode.mow_suspend
    assert status.mow_eff_mode == 1
    assert status.mow_progress == 55
    assert status.gps_coordinate == "<redacted-gps>"
    assert status.network_channel == 1
    assert status.error_code is None
    assert status.mow_height is None


def test_mower_status_from_empty_dps() -> None:
    assert MowerStatus.from_dps(None) == MowerStatus()


def test_mower_status_unknown_state_uses_unknown() -> None:
    status = MowerStatus.from_dps({"123": 9999})

    assert status.mow_state is RoborockMowerStateCode.unknown


def test_mower_state_code_mappings() -> None:
    assert RoborockMowerStateCode(0) is RoborockMowerStateCode.idle
    assert RoborockMowerStateCode(55) is RoborockMowerStateCode.mow_zig_zag
    assert RoborockMowerStateCode(56) is RoborockMowerStateCode.mow_edge
    assert RoborockMowerStateCode(71) is RoborockMowerStateCode.mow_to_dock_initializing
    assert RoborockMowerStateCode(151) is RoborockMowerStateCode.charge_charging
    assert RoborockMowerStateCode(154) is RoborockMowerStateCode.charge_fault


def test_mower_status_dps_metadata() -> None:
    dps_by_field = {
        field.name: field.metadata["dps"]
        for field in dataclasses.fields(MowerStatus)
        if field.metadata and "dps" in field.metadata
    }

    assert dps_by_field == {
        "error_code": RoborockMowerDataProtocol.ERROR_CODE,
        "battery": RoborockMowerDataProtocol.BATTERY,
        "mow_type": RoborockMowerDataProtocol.MOW_TYPE,
        "mow_state": RoborockMowerDataProtocol.MOW_STATE,
        "mapping_type": RoborockMowerDataProtocol.MAPPING_TYPE,
        "mapping_state": RoborockMowerDataProtocol.MAPPING_STATE,
        "ota_state": RoborockMowerDataProtocol.OTA_STATE,
        "charge_state": RoborockMowerDataProtocol.CHARGE_STATE,
        "dock_state": RoborockMowerDataProtocol.DOCK_STATE,
        "charge_type": RoborockMowerDataProtocol.CHARGE_TYPE,
        "pend_type": RoborockMowerDataProtocol.PEND_TYPE,
        "remote_state": RoborockMowerDataProtocol.REMOTE_STATE,
        "mow_start_type": RoborockMowerDataProtocol.MOW_START_TYPE,
        "mow_eff_mode": RoborockMowerDataProtocol.MOW_EFF_MODE,
        "mow_height": RoborockMowerDataProtocol.MOW_HEIGHT,
        "mow_direction_angle": RoborockMowerDataProtocol.MOW_DIRECTION_ANGLE,
        "mow_pattern": RoborockMowerDataProtocol.MOW_PATTERN,
        "mow_conf_mode": RoborockMowerDataProtocol.MOW_CONF_MODE,
        "offline_status": RoborockMowerDataProtocol.OFFLINE_STATUS,
        "mow_progress": RoborockMowerDataProtocol.MOW_PROGRESS,
        "blade_lifespan": RoborockMowerDataProtocol.BLADE_LIFESPAN,
        "fc_state": RoborockMowerDataProtocol.FC_STATE,
        "gps_coordinate": RoborockMowerDataProtocol.GPS_COORDINATE,
        "off_dock_no_task_status": RoborockMowerDataProtocol.OFF_DOCK_NO_TASK_STATUS,
        "afs_status": RoborockMowerDataProtocol.AFS_STATUS,
        "network_channel": RoborockMowerDataProtocol.NETWORK_CHANNEL,
    }


def test_mower_command_dps_are_not_status_fields() -> None:
    status_dps = {
        field.metadata["dps"] for field in dataclasses.fields(MowerStatus) if field.metadata and "dps" in field.metadata
    }

    assert RoborockMowerDataProtocol.START not in status_dps
    assert RoborockMowerDataProtocol.DOCK not in status_dps
    assert RoborockMowerDataProtocol.PAUSE not in status_dps
    assert RoborockMowerDataProtocol.RESUME not in status_dps
    assert RoborockMowerDataProtocol.STOP not in status_dps

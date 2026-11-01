"""Tests for mower data containers."""

import dataclasses

import pytest

from roborock.data import (
    MowerDetailState,
    MowerEffMode,
    MowerErrorCode,
    MowerGpsCoordinate,
    MowerMowType,
    MowerNetworkChannel,
    MowerStatus,
)
from roborock.roborock_message import RoborockMowerDataProtocol


def test_mower_status_from_captured_values() -> None:
    """The values from the captured snapshot parse to their typed fields."""
    status = MowerStatus.from_dict(
        {"battery": 78, "mow_type": 1, "mow_state": 58, "mow_eff_mode": 1, "mow_progress": 55, "network_channel": 1}
    )

    assert status.battery == 78
    assert status.mow_type is MowerMowType.GLOBAL
    assert status.mow_state is MowerDetailState.MOW_SUSPEND
    assert status.mow_eff_mode is MowerEffMode.DAILY
    assert status.mow_progress == 55
    assert status.network_channel is MowerNetworkChannel.WLAN0
    # Fields absent from a report are unknown, not zero.
    assert status.error_code is None
    assert status.mow_height is None


def test_mower_status_from_dict_accepts_camel_case_and_nested_gps() -> None:
    status = MowerStatus.from_dict(
        {
            "errorCode": 18,
            "battery": 82,
            "mowState": 55,
            "mowHeight": 70,
            "gpsCoordinate": {"latitude": 1.5, "longitude": -2.25},
            "unknown": "ignored",
        }
    )

    assert status.error_code is MowerErrorCode.LIFT
    assert status.battery == 82
    assert status.mow_state is MowerDetailState.MOW_ZIG_ZAG
    assert status.mow_height == 70
    assert status.gps_coordinate == MowerGpsCoordinate(latitude=1.5, longitude=-2.25)


def test_mower_status_round_trips_through_as_dict() -> None:
    status = MowerStatus.from_dict({"battery": 78, "mow_state": 58, "mow_type": 1})

    serialized = status.as_dict()

    assert serialized["mowState"] == "mow_suspend"
    assert serialized["mowType"] == "global"
    assert MowerStatus.from_dict(serialized) == status


def test_mower_status_resolves_unknown_firmware_codes_to_unknown() -> None:
    """An unmapped code resolves to the explicit UNKNOWN member instead of raising."""
    status = MowerStatus.from_dict({"mow_state": 9999, "battery": 50, "mow_type": 9999})

    assert status.mow_state is MowerDetailState.UNKNOWN
    assert status.mow_type is MowerMowType.UNKNOWN
    assert status.battery == 50


def test_mower_status_dps_metadata_matches_protocol() -> None:
    dps_by_field = {
        field.name: field.metadata["dps"] for field in dataclasses.fields(MowerStatus) if "dps" in field.metadata
    }
    status_protocols = {protocol for protocol in RoborockMowerDataProtocol if 120 <= protocol.value <= 145}

    assert set(dps_by_field.values()) == status_protocols
    assert len(dps_by_field) == len(status_protocols)


def test_mower_status_from_dps() -> None:
    """The existing factory accepts mixed keys and returns typed status fields."""
    status = MowerStatus.from_dps(
        {
            "121": 78,
            122: 1,
            "123": 58,
            "133": 1,
            "142": {"latitude": 1.5, "longitude": -2.25},
            "145": 1,
            "battery": 0,
            "123.0": 55,
            "999": "ignored",
        }
    )

    assert status.battery == 78
    assert status.mow_type is MowerMowType.GLOBAL
    assert status.mow_state is MowerDetailState.MOW_SUSPEND
    assert status.mow_eff_mode is MowerEffMode.DAILY
    assert status.gps_coordinate == MowerGpsCoordinate(latitude=1.5, longitude=-2.25)
    assert status.network_channel is MowerNetworkChannel.WLAN0
    assert status.error_code is None


@pytest.mark.parametrize("dps", [None, {}])
def test_mower_status_from_empty_dps(dps: dict[int | str, object] | None) -> None:
    assert MowerStatus.from_dps(dps) == MowerStatus()


def test_mower_status_from_dps_unknown_state() -> None:
    assert MowerStatus.from_dps({"123": 9999}).mow_state is MowerDetailState.UNKNOWN

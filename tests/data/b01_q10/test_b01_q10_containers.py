"""Test cases for B01 Q10 containers."""

from roborock.data.b01_q10 import YXDeviceState


def test_q10_status_values_are_canonical() -> None:
    """Q10 status enum values should expose canonical names."""
    assert YXDeviceState.CLEANING_STATE.value == "cleaning"
    assert YXDeviceState.CHARGING_STATE.value == "charging"
    assert YXDeviceState.UPGRADE_STATE.value == "updating"


def test_q10_status_codes_map_to_canonical_values() -> None:
    """Code-based mapping should return canonical status values."""
    assert YXDeviceState.from_code(5) is YXDeviceState.CLEANING_STATE
    assert YXDeviceState.from_code(8) is YXDeviceState.CHARGING_STATE
    assert YXDeviceState.from_code(14) is YXDeviceState.UPGRADE_STATE

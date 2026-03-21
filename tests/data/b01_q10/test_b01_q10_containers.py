"""Test cases for B01 Q10 containers."""

from roborock.data.b01_q10 import YXDeviceState


def test_q10_status_values_are_canonical() -> None:
    """Q10 status enum values should expose canonical names."""
    assert YXDeviceState.SLEEP_STATE.value == "sleeping"
    assert YXDeviceState.STANDBY_STATE.value == "standby"
    assert YXDeviceState.CLEANING_STATE.value == "cleaning"
    assert YXDeviceState.TO_CHARGE_STATE.value == "going_to_charge"
    assert YXDeviceState.REMOTEING_STATE.value == "remote_control"
    assert YXDeviceState.CHARGING_STATE.value == "charging"
    assert YXDeviceState.PAUSE_STATE.value == "paused"
    assert YXDeviceState.FAULT_STATE.value == "fault"
    assert YXDeviceState.UPGRADE_STATE.value == "updating"
    assert YXDeviceState.CREATING_MAP_STATE.value == "creating_map"
    assert YXDeviceState.MAP_SAVE_STATE.value == "saving_map"
    assert YXDeviceState.RE_LOCATION_STATE.value == "relocating"
    assert YXDeviceState.ROBOT_SWEEPING.value == "sweeping"
    assert YXDeviceState.ROBOT_MOPING.value == "mopping"
    assert YXDeviceState.ROBOT_SWEEP_AND_MOPING.value == "sweep_and_mop"
    assert YXDeviceState.ROBOT_TRANSITIONING.value == "transitioning"
    assert YXDeviceState.ROBOT_WAIT_CHARGE.value == "waiting_to_charge"


def test_q10_status_codes_map_to_canonical_values() -> None:
    """Code-based mapping should return canonical status values."""
    assert YXDeviceState.from_code(5) is YXDeviceState.CLEANING_STATE
    assert YXDeviceState.from_code(8) is YXDeviceState.CHARGING_STATE
    assert YXDeviceState.from_code(14) is YXDeviceState.UPGRADE_STATE

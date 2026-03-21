"""Test cases for B01 Q10 code mappings."""

from roborock.data.b01_q10 import YXDeviceState


def test_q10_status_values_are_canonical() -> None:
    """Q10 status enum values should expose canonical names."""
    expected_values = {
        YXDeviceState.UNKNOWN: "unknown",
        YXDeviceState.SLEEP_STATE: "sleeping",
        YXDeviceState.STANDBY_STATE: "standby",
        YXDeviceState.CLEANING_STATE: "cleaning",
        YXDeviceState.TO_CHARGE_STATE: "going_to_charge",
        YXDeviceState.REMOTEING_STATE: "remote_control",
        YXDeviceState.CHARGING_STATE: "charging",
        YXDeviceState.PAUSE_STATE: "paused",
        YXDeviceState.FAULT_STATE: "fault",
        YXDeviceState.UPGRADE_STATE: "updating",
        YXDeviceState.DUSTING: "dusting",
        YXDeviceState.CREATING_MAP_STATE: "creating_map",
        YXDeviceState.MAP_SAVE_STATE: "saving_map",
        YXDeviceState.RE_LOCATION_STATE: "relocating",
        YXDeviceState.ROBOT_SWEEPING: "sweeping",
        YXDeviceState.ROBOT_MOPING: "mopping",
        YXDeviceState.ROBOT_SWEEP_AND_MOPING: "sweep_and_mop",
        YXDeviceState.ROBOT_TRANSITIONING: "transitioning",
        YXDeviceState.ROBOT_WAIT_CHARGE: "waiting_to_charge",
    }

    assert {state: state.value for state in expected_values} == expected_values
    assert all(not value.endswith("state") for value in expected_values.values())


def test_q10_status_codes_map_to_canonical_values() -> None:
    """Code-based mapping should return canonical status values."""
    assert YXDeviceState.from_code(5) is YXDeviceState.CLEANING_STATE
    assert YXDeviceState.from_code(8) is YXDeviceState.CHARGING_STATE
    assert YXDeviceState.from_code(14) is YXDeviceState.UPGRADE_STATE

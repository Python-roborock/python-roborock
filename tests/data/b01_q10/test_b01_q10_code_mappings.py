"""Test cases for B01 Q10 code mappings."""

import pytest

from roborock.data.b01_q10 import YXDeviceState


@pytest.mark.parametrize(
    "state, string",
    [
        (YXDeviceState.UNKNOWN, "unknown"),
        (YXDeviceState.IDLE, "idle"),
        (YXDeviceState.CHARGING, "charging"),
        (YXDeviceState.CLEANING, "cleaning"),
        (YXDeviceState.SLEEPING, "sleeping"),
        (YXDeviceState.UPDATING, "updating"),
        (YXDeviceState.RETURNING_HOME, "returning_home"),
    ],
)
def test_q10_status_values_are_canonical(state: YXDeviceState, string: str) -> None:
    """Q10 status enum values should expose canonical names."""
    assert state.value == string


@pytest.mark.parametrize(
    "code, expected_state",
    [
        (5, YXDeviceState.CLEANING),
        (8, YXDeviceState.CHARGING),
        (14, YXDeviceState.UPDATING),
    ],
)
def test_q10_status_codes_map_to_canonical_values(code: int, expected_state: YXDeviceState) -> None:
    """Code-based mapping should return canonical status values."""
    assert YXDeviceState.from_code(code) is expected_state

"""Test cases for B01 Q10 code mappings."""

import pytest

from roborock.data.b01_q10 import Q10Status, YXDeviceState, YXFault


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


@pytest.mark.parametrize(
    "code, expected",
    [
        (0, YXFault.NONE),
        (503, YXFault.DOCKING_ERROR),  # ss07 docking error, not the Q7 "dustbin_not_installed"
        (570, YXFault.CANNOT_REACH_TARGET),  # ss07 cannot-reach, not the Q7 "main_brush_entangled"
        (556, YXFault.POSITIONING_FAILED),
    ],
)
def test_q10_fault_codes_map_to_ss07_labels(code: int, expected: YXFault) -> None:
    """dpFault codes should decode to the ss07-correct labels."""
    assert YXFault.from_code(code) is expected


def test_q10_status_fault_field_and_name() -> None:
    """``fault`` is a typed ``YXFault`` field; ``fault_name`` mirrors the Q7 accessor."""
    status = Q10Status(fault=YXFault.CANNOT_REACH_TARGET)
    assert status.fault is YXFault.CANNOT_REACH_TARGET
    assert status.fault_name == "cannot_reach_target"

    assert Q10Status(fault=None).fault_name is None


def test_q10_status_fault_decodes_from_dict() -> None:
    """A raw dpFault int decodes to the enum through the standard conversion path."""
    status = Q10Status.from_dict({"fault": 503})
    assert status is not None
    assert status.fault is YXFault.DOCKING_ERROR

    # An unmapped code follows the library-wide enum-field behavior:
    # the failed conversion is logged and the field is left None.
    unmapped = Q10Status.from_dict({"fault": 99999})
    assert unmapped is not None
    assert unmapped.fault is None
    assert unmapped.fault_name is None

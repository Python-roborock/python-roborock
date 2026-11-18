"""Tests for the V1 clean mode enums and wire-code helpers."""

from roborock.data.v1.v1_clean_modes import VacuumModes, vacuum_mode_wire_code


def test_vacuum_modes_have_distinct_codes() -> None:
    """Every VacuumModes member must keep a distinct code."""
    codes = [mode.code for mode in VacuumModes]
    assert len(codes) == len(set(codes))


def test_vacuum_modes_gentle_and_off_have_distinct_codes() -> None:
    """GENTLE and OFF must not share a code."""
    assert VacuumModes.GENTLE.code != VacuumModes.OFF.code


def test_vacuum_modes_code_lookup_is_unambiguous() -> None:
    """Each code must resolve to exactly one member."""
    assert VacuumModes.from_code(105) is VacuumModes.GENTLE
    assert VacuumModes.from_code(VacuumModes.OFF.code) is VacuumModes.OFF
    assert VacuumModes.from_code_optional(105) is VacuumModes.GENTLE
    assert VacuumModes.from_code_optional(VacuumModes.OFF.code) is VacuumModes.OFF


def test_vacuum_modes_int_equality_is_unambiguous() -> None:
    """Only GENTLE equals the shared wire code 105."""
    assert VacuumModes.GENTLE == 105
    assert VacuumModes.OFF != 105
    assert VacuumModes.OFF == VacuumModes.OFF.code


def test_vacuum_mode_wire_code() -> None:
    """OFF sends the shared wire code 105; every other mode sends its own code."""
    assert vacuum_mode_wire_code(VacuumModes.OFF) == 105
    assert vacuum_mode_wire_code(VacuumModes.GENTLE) == 105
    for mode in VacuumModes:
        if mode is VacuumModes.OFF:
            continue
        assert vacuum_mode_wire_code(mode) == mode.code

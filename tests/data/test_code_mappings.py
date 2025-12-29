"""Tests for code mappings.

These tests exercise the custom enum methods using arbitrary enum values.
"""

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP


def test_from_code():
    """Test from_code method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_code(201)
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_code(204)
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_code(206)


def test_from_name():
    """Test from_name method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_name("START_CLEAN")
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_name("pause")
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_name("Stop")


def test_from_value():
    """Test from_value method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_value("dpStartClean")
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_value("dpPause")
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_value("dpStop")

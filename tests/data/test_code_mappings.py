"""Tests for code mappings.
These tests exercise the custom enum methods using arbitrary enum values.
"""

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP


def test_from_code() -> None:
    """Test from_code method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_code(201)
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_code(204)
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_code(206)


def test_invalid_from_code() -> None:
    """Test invalid from_code method."""
    with pytest.raises(ValueError, match="999999 is not a valid code for B01_Q10_DP"):
        B01_Q10_DP.from_code(999999)


def test_invalid_from_code_optional() -> None:
    """Test invalid from_code_optional method."""
    assert B01_Q10_DP.from_code_optional(999999) is None


def test_from_name() -> None:
    """Test from_name method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_name("START_CLEAN")
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_name("pause")
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_name("Stop")


def test_invalid_from_name() -> None:
    """Test invalid from_name method."""
    with pytest.raises(ValueError, match="INVALID_NAME is not a valid name for B01_Q10_DP"):
        B01_Q10_DP.from_name("INVALID_NAME")


def test_from_value() -> None:
    """Test from_value method."""
    assert B01_Q10_DP.START_CLEAN == B01_Q10_DP.from_value("dpStartClean")
    assert B01_Q10_DP.PAUSE == B01_Q10_DP.from_value("dpPause")
    assert B01_Q10_DP.STOP == B01_Q10_DP.from_value("dpStop")


def test_invalid_from_value() -> None:
    """Test invalid from_value method."""
    with pytest.raises(ValueError, match="invalid_value is not a valid value for B01_Q10_DP"):
        B01_Q10_DP.from_value("invalid_value")

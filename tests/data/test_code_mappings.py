"""Tests for code mappings.
These tests exercise the custom enum methods using arbitrary enum values.
"""

import logging

import pytest

from roborock import HomeDataProduct, RoborockCategory
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXCleanType
from roborock.data.code_mappings import completed_warnings


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


def test_from_code_optional_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    """from_code_optional must silently return None for unknown codes.

    Regression test: ss07 hardware pushes data points this library does not model
    (e.g. DPs 112 and 113); resolving them via the optional lookup must not emit
    the "not a valid code" warning that the strict ``from_code`` logs.
    """
    completed_warnings.discard("112 is not a valid code for B01_Q10_DP")
    completed_warnings.discard("113 is not a valid code for B01_Q10_DP")
    with caplog.at_level(logging.WARNING):
        assert B01_Q10_DP.from_code_optional(112) is None
        assert B01_Q10_DP.from_code_optional(113) is None
    assert "not a valid code" not in caplog.text


def test_from_code_still_warns(caplog: pytest.LogCaptureFixture) -> None:
    """The strict from_code keeps logging and raising on unknown codes."""
    completed_warnings.discard("87654 is not a valid code for B01_Q10_DP")
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="not a valid code"):
        B01_Q10_DP.from_code(87654)
    assert "87654 is not a valid code for B01_Q10_DP" in caplog.text


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


@pytest.mark.parametrize(
    "input, expected",
    [
        ("START_CLEAN", B01_Q10_DP.START_CLEAN),
        ("start_clean", B01_Q10_DP.START_CLEAN),
        ("dpStartClean", B01_Q10_DP.START_CLEAN),
        (201, B01_Q10_DP.START_CLEAN),
        ("PAUSE", B01_Q10_DP.PAUSE),
        ("pause", B01_Q10_DP.PAUSE),
        ("dpPause", B01_Q10_DP.PAUSE),
        (204, B01_Q10_DP.PAUSE),
        ("STOP", B01_Q10_DP.STOP),
        ("stop", B01_Q10_DP.STOP),
        ("dpStop", B01_Q10_DP.STOP),
        (206, B01_Q10_DP.STOP),
        ("invalid_value", None),
        (999999, None),
    ],
)
def test_from_any_optional(input: str | int, expected: B01_Q10_DP | None) -> None:
    """Test from_any_optional method."""
    assert B01_Q10_DP.from_any_optional(input) == expected


def test_homedata_product_unknown_category():
    """Test that HomeDataProduct can handle unknown categories."""
    data = {
        "id": "unknown_cat_id",
        "name": "Unknown Device",
        "model": "roborock.vacuum.a87",
        "category": "roborock.random.category",
        "schema": [],
    }

    product = HomeDataProduct.from_dict(data)
    assert product.id == "unknown_cat_id"
    assert product.category == RoborockCategory.UNKNOWN


@pytest.mark.parametrize(
    ("readable_value", "expected_clean_type"),
    [
        ("vac_and_mop", YXCleanType.VAC_AND_MOP),
        ("vacuum", YXCleanType.VACUUM),
        ("mop", YXCleanType.MOP),
        ("customized", YXCleanType.CUSTOMIZED),
    ],
)
def test_yx_clean_type_from_value_readable_values(readable_value: str, expected_clean_type: YXCleanType) -> None:
    """Test YXCleanType accepts canonical readable values."""
    assert YXCleanType.from_value(readable_value) is expected_clean_type
    assert expected_clean_type.value == readable_value


def test_yx_clean_type_from_code_customized() -> None:
    """Test YXCleanType accepts custom mode code used by Q10 status updates."""
    assert YXCleanType.from_code(4) is YXCleanType.CUSTOMIZED

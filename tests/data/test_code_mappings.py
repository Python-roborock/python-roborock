"""Tests for code mappings.
These tests exercise the custom enum methods using arbitrary enum values.
"""

import pytest

from roborock import HomeDataProduct, RoborockCategory
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXCleanType


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
    ("input_value", "expected"),
    [
        ("vac_and_mop", YXCleanType.VAC_AND_MOP),
        ("vacuum", YXCleanType.VACUUM),
        ("mop", YXCleanType.MOP),
    ],
)
def test_yx_clean_type_from_value_compat_aliases(input_value: str, expected: YXCleanType) -> None:
    """Test YXCleanType accepts readable values."""
    assert YXCleanType.from_value(input_value) is expected
    assert expected.value == input_value

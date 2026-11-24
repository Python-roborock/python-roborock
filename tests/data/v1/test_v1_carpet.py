"""Tests for the V1 carpet adaption gates."""

import pytest

from roborock.data.code_mappings import RoborockProductNickname as Product
from roborock.data.v1.v1_carpet import carpet_adaption_support, carpet_clean_mode_support


@pytest.mark.parametrize(
    ("location", "product", "deep_clean_supported", "expected"),
    [
        ("us", Product.PEARL, False, (False, True)),
        ("us", Product.TANOSS, False, (True, False)),
        ("de", Product.TANOSS, False, (True, False)),
        ("de", Product.CORALPRO, True, (False, True)),
        ("de", Product.CORALPRO, False, (False, False)),
        ("cn", Product.PEARL, True, (True, False)),
        (None, Product.PEARL, True, (True, False)),
    ],
)
def test_carpet_adaption_support(
    location: str | None, product: Product, deep_clean_supported: bool, expected: tuple[bool, bool]
) -> None:
    """Self and dynamic carpet adaption depend on the region, model and carpet deep clean."""
    assert carpet_adaption_support(location, product, deep_clean_supported) == expected


@pytest.mark.parametrize(
    ("location", "product", "carpet_supported", "expected"),
    [
        ("us", Product.TANOSSLITE, True, False),
        ("de", Product.TANOSSLITE, True, True),
        (None, Product.TANOSSLITE, True, True),
        ("us", Product.TANOSS, True, True),
        ("us", None, True, True),
        ("de", Product.TANOSS, False, False),
    ],
)
def test_carpet_clean_mode_support(
    location: str | None, product: Product | None, carpet_supported: bool, expected: bool
) -> None:
    """Carpet settings need carpet support and are hidden on the TanosSLite in the US."""
    assert carpet_clean_mode_support(location, product, carpet_supported) is expected

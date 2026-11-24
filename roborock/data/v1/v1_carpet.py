"""Carpet adaption gates for V1 vacuums."""

from roborock.data.code_mappings import RoborockProductNickname as Product

__all__ = ["carpet_adaption_support", "carpet_clean_mode_support"]

# "us" is FCC, "de" is CE.
_FCC_DYNAMIC_PRODUCTS = {Product.TOPAZSV, Product.TOPAZSC, Product.ULTRON, Product.ULTRONSPLUS, Product.PEARL}
_CE_SELF_PRODUCTS = {
    Product.TANOSS,
    Product.TANOSSPLUS,
    Product.TOPAZS,
    Product.TOPAZSPLUS,
    Product.TOPAZSPOWER,
    Product.TOPAZSV,
}


def carpet_adaption_support(
    location: str | None, product: Product | None, deep_clean_supported: bool
) -> tuple[bool, bool]:
    """Return (self_adaption, dynamic_adaption) carpet support for a region and model."""
    if location == "us":
        dynamic = product in _FCC_DYNAMIC_PRODUCTS
        return not dynamic, dynamic
    if location == "de":
        self_adaption = product in _CE_SELF_PRODUCTS
        return self_adaption, not self_adaption and deep_clean_supported
    return True, False


def carpet_clean_mode_support(location: str | None, product: Product | None, carpet_supported: bool) -> bool:
    """Return whether carpet settings are offered; they are hidden on the TanosSLite in the US."""
    return carpet_supported and not (location == "us" and product == Product.TANOSSLITE)

"""Carpet models and adaption gates for V1 vacuums."""

from dataclasses import dataclass
from enum import StrEnum

from roborock.data.code_mappings import RoborockEnum
from roborock.data.code_mappings import RoborockProductNickname as Product
from roborock.data.containers import RoborockBase

__all__ = ["CarpetCleanMode", "CarpetMode", "SwitchStatus", "carpet_adaption_support", "carpet_clean_mode_support"]

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


class CarpetCleanMode(RoborockEnum):
    """Carpet clean mode codes of the robot."""

    unknown = -1
    avoid = 0
    self_adaption = 1
    vac_and_mop = 2
    dynamic_adaption = 3


class CarpetMode(StrEnum):
    """Carpet behaviour options exposed to users."""

    AVOID = "avoid"
    VAC_AND_MOP = "vac_and_mop"
    VACUUM_ONLY = "vacuum_only"
    CROSS = "cross"


@dataclass
class SwitchStatus(RoborockBase):
    """Bit flags from the `switch_status` of `get_prop ["get_status"]`."""

    switch_status: int | None = None

    @property
    def carpet_first(self) -> bool:
        """Whether carpets are cleaned first."""
        return bool((self.switch_status or 0) & 0x08)

    @property
    def cross_carpet(self) -> bool:
        """Whether the robot may cross carpets."""
        return bool((self.switch_status or 0) & 0x20)

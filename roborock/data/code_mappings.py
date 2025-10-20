from __future__ import annotations

import logging
from collections import namedtuple
from enum import Enum, IntEnum, StrEnum

_LOGGER = logging.getLogger(__name__)
completed_warnings = set()


class RoborockEnum(IntEnum):
    """Roborock Enum for codes with int values"""

    @property
    def name(self) -> str:
        return super().name.lower()

    @classmethod
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        if hasattr(cls, "unknown"):
            warning = f"Missing {cls.__name__} code: {key} - defaulting to 'unknown'"
            if warning not in completed_warnings:
                completed_warnings.add(warning)
                _LOGGER.warning(warning)
            return cls.unknown  # type: ignore
        default_value = next(item for item in cls)
        warning = f"Missing {cls.__name__} code: {key} - defaulting to {default_value}"
        if warning not in completed_warnings:
            completed_warnings.add(warning)
            _LOGGER.warning(warning)
        return default_value

    @classmethod
    def as_dict(cls: type[RoborockEnum]):
        return {i.name: i.value for i in cls if i.name != "missing"}

    @classmethod
    def as_enum_dict(cls: type[RoborockEnum]):
        return {i.value: i for i in cls if i.name != "missing"}

    @classmethod
    def values(cls: type[RoborockEnum]) -> list[int]:
        return list(cls.as_dict().values())

    @classmethod
    def keys(cls: type[RoborockEnum]) -> list[str]:
        return list(cls.as_dict().keys())

    @classmethod
    def items(cls: type[RoborockEnum]):
        return cls.as_dict().items()


class RoborockModeEnum(StrEnum):
    """A custom StrEnum that also stores an integer code for each member."""

    code: int

    def __new__(cls, value: str, code: int) -> RoborockModeEnum:
        """Creates a new enum member."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.code = code
        return member

    @classmethod
    def from_code(cls, code: int):
        for member in cls:
            if member.code == code:
                return member
        raise ValueError(f"{code} is not a valid code for {cls.__name__}")


ProductInfo = namedtuple("ProductInfo", ["nickname", "short_models"])


class RoborockProductNickname(Enum):
    # Coral Series
    CORAL = ProductInfo(nickname="Coral", short_models=("a20", "a21"))
    CORALPRO = ProductInfo(nickname="CoralPro", short_models=("a143", "a144"))

    # Pearl Series
    PEARL = ProductInfo(nickname="Pearl", short_models=("a74", "a75"))
    PEARLC = ProductInfo(nickname="PearlC", short_models=("a103", "a104"))
    PEARLE = ProductInfo(nickname="PearlE", short_models=("a167", "a168"))
    PEARLELITE = ProductInfo(nickname="PearlELite", short_models=("a169", "a170"))
    PEARLPLUS = ProductInfo(nickname="PearlPlus", short_models=("a86", "a87"))
    PEARLPLUSS = ProductInfo(nickname="PearlPlusS", short_models=("a116", "a117", "a136"))
    PEARLS = ProductInfo(nickname="PearlS", short_models=("a100", "a101"))
    PEARLSLITE = ProductInfo(nickname="PearlSLite", short_models=("a122", "a123"))

    # Ruby Series
    RUBYPLUS = ProductInfo(nickname="RubyPlus", short_models=("t4", "s4"))
    RUBYSC = ProductInfo(nickname="RubySC", short_models=("p5", "a08"))
    RUBYSE = ProductInfo(nickname="RubySE", short_models=("a19",))
    RUBYSLITE = ProductInfo(nickname="RubySLite", short_models=("p6", "s5e", "a05"))

    # Tanos Series
    TANOS = ProductInfo(nickname="Tanos", short_models=("t6", "s6"))
    TANOSE = ProductInfo(nickname="TanosE", short_models=("t7", "a11"))
    TANOSS = ProductInfo(nickname="TanosS", short_models=("a14", "a15"))
    TANOSSC = ProductInfo(nickname="TanosSC", short_models=("a39", "a40"))
    TANOSSE = ProductInfo(nickname="TanosSE", short_models=("a33", "a34"))
    TANOSSMAX = ProductInfo(nickname="TanosSMax", short_models=("a52",))
    TANOSSLITE = ProductInfo(nickname="TanosSLite", short_models=("a37", "a38"))
    TANOSSPLUS = ProductInfo(nickname="TanosSPlus", short_models=("a23", "a24"))
    TANOSV = ProductInfo(nickname="TanosV", short_models=("t7p", "a09", "a10"))

    # Topaz Series
    TOPAZS = ProductInfo(nickname="TopazS", short_models=("a29", "a30", "a76"))
    TOPAZSC = ProductInfo(nickname="TopazSC", short_models=("a64", "a65"))
    TOPAZSPLUS = ProductInfo(nickname="TopazSPlus", short_models=("a46", "a47", "a66"))
    TOPAZSPOWER = ProductInfo(nickname="TopazSPower", short_models=("a62",))
    TOPAZSV = ProductInfo(nickname="TopazSV", short_models=("a26", "a27"))

    # Ultron Series
    ULTRON = ProductInfo(nickname="Ultron", short_models=("a50", "a51"))
    ULTRONE = ProductInfo(nickname="UltronE", short_models=("a72", "a84"))
    ULTRONLITE = ProductInfo(nickname="UltronLite", short_models=("a73", "a85"))
    ULTRONSC = ProductInfo(nickname="UltronSC", short_models=("a94", "a95"))
    ULTRONSE = ProductInfo(nickname="UltronSE", short_models=("a124", "a125", "a139", "a140"))
    ULTRONSPLUS = ProductInfo(nickname="UltronSPlus", short_models=("a68", "a69", "a70"))
    ULTRONSV = ProductInfo(nickname="UltronSV", short_models=("a96", "a97"))

    # Verdelite Series
    VERDELITE = ProductInfo(nickname="Verdelite", short_models=("a146", "a147"))

    # Vivian Series
    VIVIAN = ProductInfo(nickname="Vivian", short_models=("a134", "a135", "a155", "a156"))
    VIVIANC = ProductInfo(nickname="VivianC", short_models=("a158", "a159"))


SHORT_MODEL_TO_ENUM = {model: product for product in RoborockProductNickname for model in product.value.short_models}


class RoborockCategory(Enum):
    """Describes the category of the device."""

    WET_DRY_VAC = "roborock.wetdryvac"
    VACUUM = "robot.vacuum.cleaner"
    WASHING_MACHINE = "roborock.wm"
    UNKNOWN = "UNKNOWN"

    def __missing__(self, key):
        _LOGGER.warning("Missing key %s from category", key)
        return RoborockCategory.UNKNOWN

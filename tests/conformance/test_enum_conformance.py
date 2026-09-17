"""Conformance tests for Roborock enum fallback resilience.

As defined in AGENTS.md, all wire/firmware enums representing device status,
error codes, and protocol integer codes MUST inherit from RoborockEnum
(defining a lowercase unknown member) or RoborockModeEnum (using from_code_optional)
so unknown codes from firmware updates never crash consumers.
"""

from __future__ import annotations

import enum
import inspect

import pytest

import roborock
from roborock.data.code_mappings import RoborockEnum, RoborockModeEnum
from tests.conformance.discovery import discover_subclasses, to_pytest_params, walk_modules

# Baseline inventory of legacy RoborockEnum classes that do not yet define an
# explicit `unknown` member. When newer firmware emits an undocumented code,
# RoborockEnum._missing_ currently falls back to `next(item for item in cls)`,
# which arbitrarily defaults to the first member.
# As these enums are remediated, remove them from this baseline.
KNOWN_ENUMS_MISSING_UNKNOWN = {
    "roborock.data.dyad.dyad_code_mappings.DyadBrushSpeed",
    "roborock.data.dyad.dyad_code_mappings.DyadCleanMode",
    "roborock.data.dyad.dyad_code_mappings.DyadCleanser",
    "roborock.data.dyad.dyad_code_mappings.DyadError",
    "roborock.data.dyad.dyad_code_mappings.DyadMode",
    "roborock.data.dyad.dyad_code_mappings.DyadSelfCleanLevel",
    "roborock.data.dyad.dyad_code_mappings.DyadSelfCleanMode",
    "roborock.data.dyad.dyad_code_mappings.DyadSuction",
    "roborock.data.dyad.dyad_code_mappings.DyadWarmLevel",
    "roborock.data.dyad.dyad_code_mappings.DyadWaterLevel",
    "roborock.data.v1.v1_code_mappings.CleanFluidStatus",
    "roborock.data.v1.v1_code_mappings.ClearWaterBoxStatus",
    "roborock.data.v1.v1_code_mappings.DirtyWaterBoxStatus",
    "roborock.data.v1.v1_code_mappings.DustBagStatus",
    "roborock.data.v1.v1_code_mappings.RoborockCleanType",
    "roborock.data.v1.v1_code_mappings.RoborockDockErrorCode",
    "roborock.data.v1.v1_code_mappings.RoborockDssCodes",
    "roborock.data.v1.v1_code_mappings.RoborockErrorCode",
    "roborock.data.v1.v1_code_mappings.RoborockFanPowerCode",
    "roborock.data.v1.v1_code_mappings.RoborockFanSpeedE2",
    "roborock.data.v1.v1_code_mappings.RoborockFanSpeedV1",
    "roborock.data.v1.v1_code_mappings.RoborockFanSpeedV2",
    "roborock.data.v1.v1_code_mappings.RoborockFanSpeedV3",
    "roborock.data.v1.v1_code_mappings.RoborockFinishReason",
    "roborock.data.v1.v1_code_mappings.RoborockInCleaning",
    "roborock.data.v1.v1_code_mappings.RoborockMopIntensityCode",
    "roborock.data.v1.v1_code_mappings.RoborockMopIntensityV2",
    "roborock.data.v1.v1_code_mappings.RoborockStartType",
    "roborock.data.zeo.zeo_code_mappings.ZeoDetergentExpansionType",
    "roborock.data.zeo.zeo_code_mappings.ZeoDetergentType",
    "roborock.data.zeo.zeo_code_mappings.ZeoDirtDetectionStatus",
    "roborock.data.zeo.zeo_code_mappings.ZeoDryAndCare",
    "roborock.data.zeo.zeo_code_mappings.ZeoDryerStartError",
    "roborock.data.zeo.zeo_code_mappings.ZeoDryingMethod",
    "roborock.data.zeo.zeo_code_mappings.ZeoDryingMode",
    "roborock.data.zeo.zeo_code_mappings.ZeoError",
    "roborock.data.zeo.zeo_code_mappings.ZeoFeatureBits",
    "roborock.data.zeo.zeo_code_mappings.ZeoMode",
    "roborock.data.zeo.zeo_code_mappings.ZeoProgram",
    "roborock.data.zeo.zeo_code_mappings.ZeoRinse",
    "roborock.data.zeo.zeo_code_mappings.ZeoSoak",
    "roborock.data.zeo.zeo_code_mappings.ZeoSoftenerExpansionType",
    "roborock.data.zeo.zeo_code_mappings.ZeoSoftenerType",
    "roborock.data.zeo.zeo_code_mappings.ZeoSpin",
    "roborock.data.zeo.zeo_code_mappings.ZeoState",
    "roborock.data.zeo.zeo_code_mappings.ZeoSteamVolume",
    "roborock.data.zeo.zeo_code_mappings.ZeoTemperature",
    "roborock.roborock_message.RoborockB01Protocol",
    "roborock.roborock_message.RoborockDataProtocol",
    "roborock.roborock_message.RoborockDyadDataProtocol",
    "roborock.roborock_message.RoborockMessageProtocol",
    "roborock.roborock_message.RoborockMowerDataProtocol",
    "roborock.roborock_message.RoborockZeoProtocol",
}

_XFAIL_MARKS = {
    fqn: pytest.mark.xfail(
        reason=f"{fqn} lacks an explicit 'unknown' member; defaults to first item on unknown codes",
        strict=True,
    )
    for fqn in KNOWN_ENUMS_MISSING_UNKNOWN
}

_ALL_ROBOROCK_ENUMS = discover_subclasses(roborock, RoborockEnum, exclude=(RoborockEnum,))
_ALL_MODE_ENUMS = discover_subclasses(roborock, RoborockModeEnum, exclude=(RoborockModeEnum,))


# Enums in wire code mapping modules that intentionally remain standard Enum/StrEnum/IntEnum
# (e.g., domain categories, product nicknames, or outgoing command identifiers).
ALLOWED_NON_RESILIENT_CODE_MAPPING_ENUMS = {
    "roborock.data.b01_q10.b01_q10_code_mappings.RemoteCommand",
    "roborock.data.code_mappings.RoborockCategory",
    "roborock.data.code_mappings.RoborockProductNickname",
    "roborock.data.v1.v1_code_mappings.RoborockDockState",
}


def _discover_code_mapping_enums() -> list[type[enum.Enum]]:
    enums: list[type[enum.Enum]] = []
    for mod in walk_modules(roborock):
        if "code_mapping" in mod.__name__:
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    obj.__module__ == mod.__name__
                    and issubclass(obj, enum.Enum)
                    and obj not in (enum.Enum, enum.IntEnum, enum.StrEnum, RoborockEnum, RoborockModeEnum)
                ):
                    enums.append(obj)
    return sorted(enums, key=lambda c: f"{c.__module__}.{c.__name__}")


_ALL_CODE_MAPPING_ENUMS = _discover_code_mapping_enums()


@pytest.mark.parametrize("enum_cls", to_pytest_params(_ALL_ROBOROCK_ENUMS, marks_by_fqn=_XFAIL_MARKS))
def test_roborock_enum_has_unknown_fallback(enum_cls: type[RoborockEnum]) -> None:
    """All RoborockEnum subclasses must define an explicit 'unknown' member."""
    assert hasattr(enum_cls, "unknown"), (
        f"{enum_cls.__module__}.{enum_cls.__name__} must define an 'unknown' member to prevent "
        "crashing or defaulting to arbitrary states on new firmware."
    )
    # Derive an integer sentinel guaranteed to not exist in the enum
    sentinel = max(item.value for item in enum_cls) + 1 if list(enum_cls) else 99999
    assert enum_cls(sentinel) == enum_cls.unknown


@pytest.mark.parametrize("mode_enum_cls", to_pytest_params(_ALL_MODE_ENUMS))
def test_roborock_mode_enum_handles_unknown_code(mode_enum_cls: type[RoborockModeEnum]) -> None:
    """RoborockModeEnum subclasses must return None when an unknown code is provided."""
    sentinel = max(member.code for member in mode_enum_cls) + 1 if list(mode_enum_cls) else 99999
    assert mode_enum_cls.from_code_optional(sentinel) is None


@pytest.mark.parametrize("enum_cls", to_pytest_params(_ALL_CODE_MAPPING_ENUMS))
def test_code_mapping_enums_inherit_resilient_bases(enum_cls: type[enum.Enum]) -> None:
    """Enums in wire code mapping modules must inherit from RoborockEnum or RoborockModeEnum."""
    fqn = f"{enum_cls.__module__}.{enum_cls.__name__}"
    if fqn in ALLOWED_NON_RESILIENT_CODE_MAPPING_ENUMS:
        return
    assert issubclass(enum_cls, (RoborockEnum, RoborockModeEnum)), (
        f"{fqn} in a code mapping module does not inherit from RoborockEnum or RoborockModeEnum. "
        "Wire status and error code enums must use resilient enum bases to handle unknown firmware codes."
    )


def test_known_missing_unknown_baseline_inventory() -> None:
    """Ensure the inventory of legacy unresilient enums remains strictly synchronized."""
    current_missing = {f"{cls.__module__}.{cls.__name__}" for cls in _ALL_ROBOROCK_ENUMS if not hasattr(cls, "unknown")}
    new_untracked = current_missing - KNOWN_ENUMS_MISSING_UNKNOWN
    assert not new_untracked, (
        f"New RoborockEnum classes without 'unknown' member detected: {new_untracked}. "
        "All new wire enums must define an 'unknown' member (e.g. unknown = -1 or 0)."
    )
    stale_in_baseline = KNOWN_ENUMS_MISSING_UNKNOWN - current_missing
    assert not stale_in_baseline, (
        f"Enums in KNOWN_ENUMS_MISSING_UNKNOWN are no longer missing 'unknown': {stale_in_baseline}. "
        "Please remove them from KNOWN_ENUMS_MISSING_UNKNOWN."
    )

"""Tests for mower code mappings."""

import pytest

from roborock.data import mower
from roborock.data.code_mappings import RoborockModeEnum
from roborock.data.mower import (
    MowerChargeState,
    MowerDetailState,
    MowerEffMode,
    MowerEnum,
    MowerErrorCode,
    MowerFcState,
    MowerMowState,
    MowerMowType,
    MowerNetworkChannel,
    MowerOfflineStatus,
    MowerPendType,
    RoborockMowerStateCode,
)

ALL_MOWER_ENUMS: list[type[RoborockModeEnum]] = sorted(
    (
        obj
        for obj in vars(mower).values()
        if isinstance(obj, type) and issubclass(obj, MowerEnum) and obj is not MowerEnum
    ),
    key=lambda cls: cls.__name__,
)


def test_all_mower_enums_are_exported() -> None:
    """Every mower enum is exported from its module."""
    assert ALL_MOWER_ENUMS
    assert all(cls.__name__ in mower.mower_code_mappings.__all__ for cls in ALL_MOWER_ENUMS)


@pytest.mark.parametrize("enum_cls", ALL_MOWER_ENUMS, ids=lambda cls: cls.__name__)
def test_mower_enum_values_are_protobuf_names(enum_cls: type[RoborockModeEnum]) -> None:
    """The string value is the protobuf enum name, so it can round-trip through the JSON route."""
    for member in enum_cls:
        assert enum_cls.from_value(member.value) is member
        assert enum_cls.from_code(member.code) is member


@pytest.mark.parametrize("enum_cls", ALL_MOWER_ENUMS, ids=lambda cls: cls.__name__)
def test_mower_enum_codes_are_unique(enum_cls: type[RoborockModeEnum]) -> None:
    """Each wire code maps to exactly one member."""
    codes = [member.code for member in enum_cls]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize(
    ("enum_cls", "code", "expected"),
    [
        # Values from the live RockNeo Q105 status capture.
        (MowerMowType, 1, MowerMowType.GLOBAL),
        (MowerDetailState, 58, MowerDetailState.MOW_SUSPEND),
        (MowerEffMode, 1, MowerEffMode.DAILY),
        (MowerNetworkChannel, 1, MowerNetworkChannel.WLAN0),
        # Zero has a named meaning in every compact enum.
        (MowerMowState, 0, MowerMowState.IDLE),
        (MowerChargeState, 0, MowerChargeState.NOT_CHARGING),
        (MowerPendType, 0, MowerPendType.NOT_SUSPENDED),
        (MowerOfflineStatus, 0, MowerOfflineStatus.ONLINE),
        (MowerFcState, 0, MowerFcState.NOT_FC),
        # Boundaries of the detailed state domain.
        (MowerDetailState, 25, MowerDetailState.MAP_CONFIRM_EDIT_BOUNDARY),
        (MowerDetailState, 78, MowerDetailState.MOW_PAUSE),
        (MowerDetailState, 110, MowerDetailState.FREE_BATTERY_HOLD_MODE),
        (MowerDetailState, 154, MowerDetailState.CHARGE_FAULT),
        # Error codes have gaps in their numbering.
        (MowerErrorCode, 48, MowerErrorCode.CAMERA_REAR_SIDE_DIRTY),
        (MowerErrorCode, 55, MowerErrorCode.N_RTK_NETWORK_ERROR),
        (MowerErrorCode, 118, MowerErrorCode.REAR_SIDE_CAMERA_FAULT),
    ],
)
def test_mower_enum_code_lookup(enum_cls: type[RoborockModeEnum], code: int, expected: RoborockModeEnum) -> None:
    assert enum_cls.from_code(code) is expected


@pytest.mark.parametrize(
    ("enum_cls", "code"),
    [
        # Gaps inside the detailed-state and error-code domains.
        (MowerDetailState, 26),
        (MowerDetailState, 50),
        (MowerDetailState, 79),
        (MowerErrorCode, 47),
        (MowerErrorCode, 56),
        # The detailed value seen on DPS 123 is not part of the compact domain.
        (MowerMowState, 58),
    ],
)
def test_mower_enum_unknown_codes_resolve_to_none(enum_cls: type[RoborockModeEnum], code: int) -> None:
    assert enum_cls.from_code_optional(code) is None


@pytest.mark.parametrize(
    ("member", "wire_name"),
    [
        (MowerDetailState.MAP_ERASING, "MAP_ERASEING"),
    ],
)
def test_misspelled_wire_names_are_preserved(member: RoborockModeEnum, wire_name: str) -> None:
    """Protocol misspellings are kept as the value so the JSON route still matches."""
    assert member.value == wire_name
    assert type(member).from_value(wire_name) is member


@pytest.mark.parametrize(
    ("enum_cls", "raw", "expected"),
    [
        (MowerEffMode, "DAILY", MowerEffMode.DAILY),
        (MowerEffMode, 1, MowerEffMode.DAILY),
        (MowerEffMode, "1", MowerEffMode.DAILY),
        (MowerDetailState, "MAP_ERASEING", MowerDetailState.MAP_ERASING),
        # Unknown values resolve to the explicit unknown member, synthetic or protocol-defined.
        (MowerMowType, 9999, MowerMowType.UNKNOWN),
        (MowerMowType, "FUTURE_TYPE", MowerMowType.UNKNOWN),
        (MowerDetailState, 9999, MowerDetailState.UNKNOWN),
    ],
)
def test_from_code_accepts_wire_forms_and_falls_back(
    enum_cls: type[MowerEnum], raw: int | str, expected: MowerEnum
) -> None:
    assert enum_cls.from_code(raw) is expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (0, RoborockMowerStateCode.idle),
        (12, RoborockMowerStateCode.map_erasing),
        (58, RoborockMowerStateCode.mow_suspend),
        (61, RoborockMowerStateCode.mow_docked_rainfall),
        (151, RoborockMowerStateCode.charge_charging),
        (154, RoborockMowerStateCode.charge_fault),
        (9999, RoborockMowerStateCode.unknown),
    ],
)
def test_legacy_state_enum_remains_available(code: int, expected: RoborockMowerStateCode) -> None:
    """Existing imports, lower-case member names and integer lookups still work."""
    from roborock.data import RoborockMowerStateCode as exported_enum

    assert exported_enum is RoborockMowerStateCode
    assert exported_enum(code) is expected
    assert exported_enum.unknown.value == -999

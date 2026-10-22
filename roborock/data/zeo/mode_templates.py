"""Mode-template resolution for Zeo (washing machine / dryer) devices.

Resolves which mode templates a device supports:

1. ``deviceModel`` string → series name (45 prefixes, longest-first match).
2. series + region + feature bits → data-module id (41 branches).
3. data-module id → list of mode templates (4212 modes across 70 modules).

Each mode template maps a program to its parameter capabilities, including the
protocol-level (DP) enum values the device expects — e.g. soak sends
``ZeoSoak`` (0..5), temperature sends ``ZeoTemperature`` (1..7) — built from the
flat ``*_levelN`` fields of the mode data.

A mode entry may additionally carry *special-combination* variants of the same
``(mode, program)`` pair (marked ``priority: "sp"`` and ``is_in_app: false``);
they are exposed as :attr:`ZeoModeTemplate.special_rules` and carry a fixed
``special_program_total_time`` (a display-only duration, not the DP 234 value).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..containers import RoborockBase
from .zeo_code_mappings import (
    ZeoDryAndCare,
    ZeoDryingMethod,
    ZeoDryingMode,
    ZeoFeatureBits,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoak,
    ZeoSpin,
    ZeoSteamVolume,
    ZeoTemperature,
)

__all__ = [
    "ZeoModeConfig",
    "ZeoModeLists",
    "ZeoModeTemplate",
    "ZeoParamConfig",
    "ZeoTimeOptions",
    "build_mode_templates",
    "resolve_data_module",
    "resolve_mode_templates",
    "split_mode_templates",
]

_DATA_DIR = Path(__file__).parent / "mode_data"


_SOAK_FIELDS = {
    1: ZeoSoak.normal,  # 0, 0min
    2: ZeoSoak.low,  # 1, 5min
    3: ZeoSoak.medium,  # 2, 10min
    4: ZeoSoak.high,  # 3, 15min
    5: ZeoSoak.max,  # 4, 20min
    6: ZeoSoak.very_max,  # 5, 30min
}


def _soak_level_range(feature_bits: int) -> range:
    """soak_level6 (30 min) only exists when ``ThirtyMinSoak`` is enabled.

    Without ``ZeoFeatureBits.thirty_min_soak`` (bit 8) the 30-minute level is
    never offered, even when the mode data carries a value for it.
    """
    if feature_bits & (1 << int(ZeoFeatureBits.thirty_min_soak)):
        return range(1, 7)
    return range(1, 6)


# The order the temperature levels are read in: ``temperature_level1,
# temperature_level6, temperature_level2, temperature_level3, temperature_level4,
# temperature_level5, temperature_level7``.  The 20 °C slot sits second in that
# field list, so ``support`` follows this order rather than ascending level
# numbers.
_TEMPERATURE_LEVEL_ORDER = (1, 6, 2, 3, 4, 5, 7)

_TEMPERATURE_FIELDS = {
    1: ZeoTemperature.normal,  # L1, 0C
    6: ZeoTemperature.twenty_c,  # L6, 20C (special slot, second in the field order)
    2: ZeoTemperature.low,  # L2, 30C
    3: ZeoTemperature.medium,  # L3, 40C
    4: ZeoTemperature.high,  # L4, 60C
    5: ZeoTemperature.max,  # L5, 90C
    7: ZeoTemperature.ninety_c,  # L7, 95C
}

_RINSE_FIELDS = {
    0: ZeoRinse.none,
    1: ZeoRinse.min,
    2: ZeoRinse.low,
    3: ZeoRinse.mid,
    4: ZeoRinse.high,
    5: ZeoRinse.max,
}

_SPIN_FIELDS = {
    1: ZeoSpin.none,  # 0 RPM
    2: ZeoSpin.very_low,  # 400 RPM
    3: ZeoSpin.low,  # 600 RPM
    4: ZeoSpin.mid,  # 800 RPM
    5: ZeoSpin.high,  # 1000 RPM
    6: ZeoSpin.very_high,  # 1200 RPM
    7: ZeoSpin.max,  # 1400 RPM
}

_DRY_FIELDS = {
    1: ZeoDryingMode.iron,  # Low → Iron(2)
    2: ZeoDryingMode.quick,  # Mid → Quick(1)
    3: ZeoDryingMode.store,  # High → Store(3)
}

_DRY_AND_CARE_FIELDS = {
    1: ZeoDryAndCare.soft,
    2: ZeoDryAndCare.normal,
}

_DRY_METHOD_FIELDS = {
    1: ZeoDryingMethod.l1,  # Saving
    2: ZeoDryingMethod.l2,  # Standard
    3: ZeoDryingMethod.l3,  # SuperFast
}

_STEAM_FIELDS = {
    1: ZeoSteamVolume.none,  # L0, None
    2: ZeoSteamVolume.low,  # L1, Min
    3: ZeoSteamVolume.medium,  # L2, Low
    4: ZeoSteamVolume.high,  # L3, Mid
    5: ZeoSteamVolume.max,  # L4, High
}


@dataclass
class ZeoParamConfig(RoborockBase):
    """One parameter's available levels.

    ``default`` and ``support`` hold protocol-level enum members (what the
    device actually expects).  ``raw_values`` holds the physical display values
    from the mode data (minutes, °C, RPM, ...), in the same order as
    ``support``.
    """

    default: Any | None = None
    """Default protocol-level level (a ``ZeoXxx`` enum member), or ``None``."""

    support: list[Any] = field(default_factory=list)
    """All available protocol-level levels, in the order the mode data lists them."""

    raw_values: list[Any] = field(default_factory=list)
    """Physical display values for each supported level, same order as ``support``."""


@dataclass
class ZeoTimeOptions(RoborockBase):
    """Selectable durations, in minutes, for a timed programme (DP 234).

    Unlike :class:`ZeoParamConfig` the values *are* the protocol values: the
    mode data lists the minutes to send, with no enum encoding in between.
    """

    default: int | None = None
    """Default duration in minutes, or ``None``."""

    support: list[int] = field(default_factory=list)
    """All selectable durations, in the order the mode data lists them."""


@dataclass
class ZeoModeConfig(RoborockBase):
    """A program's parameter capabilities."""

    soak: ZeoParamConfig | None = None
    temperature: ZeoParamConfig | None = None
    rinse: ZeoParamConfig | None = None
    spin: ZeoParamConfig | None = None
    drying_mode: ZeoParamConfig | None = None
    dry_and_care: ZeoParamConfig | None = None
    dry_method: ZeoParamConfig | None = None
    steam_volume: ZeoParamConfig | None = None

    # Timed-programme durations.  An entry carries at most one of the three
    # option groups (see `_build_time_options`).
    smart_time: ZeoTimeOptions | None = None
    timed_program_time: ZeoTimeOptions | None = None
    timed_drying: ZeoTimeOptions | None = None

    is_support_auto_detergent: bool = False
    is_support_auto_softener: bool = False
    is_support_uvc: bool = False
    is_support_reservation: bool = False
    is_support_dirt_detection: bool = False
    is_ion_on: bool = False
    default_ion_status: bool = False

    total_time: int | None = None
    """Fixed running duration in minutes for this programme (DP 234).

    Resolved from the timed option groups' defaults (``smart_time`` →
    ``timed_drying`` → ``timed_program_time``).  The special-combination
    ``special_program_total_time`` is deliberately *not* folded in: it is a
    display-only duration, not a protocol value.
    """


@dataclass
class ZeoModeTemplate(RoborockBase):
    """One program template (a single mode object from the data module)."""

    id: int
    dp: ZeoProgram
    program_type: ZeoMode
    program_name: str
    """The programme's name as recorded in the mode data.

    The mode data stores this in Chinese and it is not a display string.  Use
    :attr:`dp` (a :class:`ZeoProgram` member) as the stable identifier and
    translate it in the caller's own layer.
    """
    is_in_app: bool
    config: ZeoModeConfig

    # Ordering for this program within its mode (lower comes first).
    priority: int = 0

    # Special-combination variants of the same (mode, program) pair, built from
    # the nested ``special_rules`` of the mode data, each exactly like a
    # top-level mode.  They carry ``is_in_app=False`` and their ``priority`` is
    # the marker ``"sp"`` rather than an ordering — it normalises to 0, with
    # the marker still visible in ``raw["priority"]``.
    special_rules: list[ZeoModeTemplate] = field(default_factory=list)

    special_program_total_time: int | None = None
    """Fixed duration of a special-combination variant, in minutes.

    Display-only: it is *not* the DP 234 duration (``total_time``).  Regular
    programmes leave it ``None``.
    """

    # Raw flat fields, kept verbatim for advanced consumers.
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class ZeoModeLists(RoborockBase):
    """A device's programmes, split into the per-mode groups a picker needs."""

    all_modes: list[ZeoModeTemplate] = field(default_factory=list)
    """Every entry of the device's data module."""

    wash: list[ZeoModeTemplate] = field(default_factory=list)
    wash_and_dry: list[ZeoModeTemplate] = field(default_factory=list)
    dry: list[ZeoModeTemplate] = field(default_factory=list)
    treatment: list[ZeoModeTemplate] = field(default_factory=list)

    other: list[ZeoModeTemplate] = field(default_factory=list)
    """The cloud/custom programme plus the drum self-clean programme.

    ``down_clean`` also keeps its per-mode bucket membership, so the buckets
    overlap.
    """


def _build_param(
    raw: dict[str, Any],
    field_prefix: str,
    level_order: Sequence[int],
    field_map: dict[int, Any],
    default_field: str,
) -> ZeoParamConfig | None:
    """Build a :class:`ZeoParamConfig` from flat ``*_levelN`` fields.

    ``level_order`` is the order the ``*_levelN`` fields are read in, which is
    not always ascending (see ``_TEMPERATURE_LEVEL_ORDER``).  The mode data
    expresses both the available levels and the default as the same ``N`` that
    appears in the ``*_levelN`` field names, so no shifting between level
    numbering schemes is needed.
    """
    support: list[Any] = []
    raw_values: list[Any] = []
    for n in level_order:
        v = raw.get(f"{field_prefix}{n}")
        if v is not None and n in field_map:
            support.append(field_map[n])
            raw_values.append(v)

    if not support:
        return None

    default: Any | None = None
    level_n = raw.get(default_field)
    if level_n is not None:
        # Only trust the default when its level is actually part of the
        # support set (e.g. default_soak_level=6 is meaningless when the
        # 30-minute level is filtered out by the ThirtyMinSoak feature bit).
        if level_n in field_map and level_n in level_order:
            default = field_map[level_n]

    return ZeoParamConfig(default=default, support=support, raw_values=raw_values)


def _build_time_options(raw: dict[str, Any], list_field: str, default_field: str) -> ZeoTimeOptions | None:
    """Build a :class:`ZeoTimeOptions` from a ``*_time_list`` + default pair."""
    values = raw.get(list_field)
    if not values:
        return None
    default = raw.get(default_field)
    return ZeoTimeOptions(
        default=int(default) if default is not None else None,
        support=[int(value) for value in values],
    )


def _resolve_total_time(*option_groups: ZeoTimeOptions | None) -> int | None:
    """Resolve a programme's fixed duration (DP 234), if it has one.

    The duration is the first option group's default, in the order::

        smart_time → timed_drying → timed_program_time

    The special-combination ``special_program_total_time`` is deliberately
    excluded: it is display-only, not a DP 234 duration.  The caller passes the
    option groups in the order above.
    """
    for group in option_groups:
        if group is not None and group.default is not None:
            return group.default
    return None


def _build_config(raw: dict[str, Any], feature_bits: int = 0) -> ZeoModeConfig:
    """Turn a flat mode object into a structured :class:`ZeoModeConfig`."""
    smart_time = _build_time_options(raw, "smart_time_list", "default_smart_time")
    timed_drying = _build_time_options(raw, "timed_drying_list", "default_timed_drying_time")
    timed_program_time = _build_time_options(raw, "timed_program_time_list", "default_timed_program_time")
    return ZeoModeConfig(
        soak=_build_param(raw, "soak_level", _soak_level_range(feature_bits), _SOAK_FIELDS, "default_soak_level"),
        temperature=_build_param(
            raw, "temperature_level", _TEMPERATURE_LEVEL_ORDER, _TEMPERATURE_FIELDS, "default_temperature_level"
        ),
        rinse=_build_param(raw, "rinse_level", range(6), _RINSE_FIELDS, "default_rinse_level"),
        spin=_build_param(raw, "spin_speed_level", range(1, 8), _SPIN_FIELDS, "default_spin_speed_level"),
        drying_mode=_build_param(raw, "dry_level", range(1, 4), _DRY_FIELDS, "default_dry_level"),
        dry_and_care=_build_param(
            raw, "dry_and_care_level", range(1, 3), _DRY_AND_CARE_FIELDS, "default_dry_and_care_level"
        ),
        dry_method=_build_param(raw, "dry_method_level", range(1, 4), _DRY_METHOD_FIELDS, "default_dry_method_level"),
        steam_volume=_build_param(
            raw, "steam_treatment_level", range(1, 6), _STEAM_FIELDS, "default_steam_treatment_level"
        ),
        smart_time=smart_time,
        timed_program_time=timed_program_time,
        timed_drying=timed_drying,
        is_support_auto_detergent=bool(raw.get("is_support_auto_detergent")),
        is_support_auto_softener=bool(raw.get("is_support_auto_softener")),
        is_support_uvc=bool(raw.get("is_support_uvc")),
        is_support_reservation=bool(raw.get("is_support_reservation")),
        is_support_dirt_detection=bool(raw.get("is_support_dirt_detection")),
        is_ion_on=bool(raw.get("is_ion_on")),
        default_ion_status=bool(raw.get("default_ion_status")),
        total_time=_resolve_total_time(smart_time, timed_drying, timed_program_time),
    )


def _as_priority(value: Any) -> int:
    """Coerce a data ``priority`` to an int.

    Regular programmes carry a numeric app ordering.  Special-combination
    entries carry the marker ``"sp"`` instead; that is not an ordering, so it
    becomes ``0`` (the original marker remains available in ``raw``).
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _mode_from_raw(raw: dict[str, Any], feature_bits: int = 0) -> ZeoModeTemplate:
    """Turn a flat mode object into a :class:`ZeoModeTemplate`."""
    return ZeoModeTemplate(
        id=int(raw["id"]),
        dp=ZeoProgram(int(raw["dp"])),
        program_type=ZeoMode(int(raw["program_type"])),
        program_name=str(raw.get("program_name") or ""),
        is_in_app=bool(raw.get("is_in_app")),
        config=_build_config(raw, feature_bits),
        priority=_as_priority(raw.get("priority")),
        special_rules=[_mode_from_raw(entry, feature_bits) for entry in raw.get("special_rules") or []],
        special_program_total_time=raw.get("special_program_total_time"),
        raw=raw,
    )


class _ModeDataStore:
    """Lazily loads the three data files."""

    def __init__(self) -> None:
        self._prefixes: dict[str, str] | None = None
        self._selector: list[dict] | None = None
        self._modules: dict[str, list[dict]] | None = None

    @property
    def prefixes(self) -> dict[str, str]:
        if self._prefixes is None:
            with (_DATA_DIR / "device_model_prefixes.json").open(encoding="utf-8") as f:
                self._prefixes = json.load(f)
        return self._prefixes

    @property
    def selector(self) -> list[dict]:
        if self._selector is None:
            with (_DATA_DIR / "mode_selector_map.json").open(encoding="utf-8") as f:
                self._selector = json.load(f)
        return self._selector

    @property
    def modules(self) -> dict[str, list[dict]]:
        if self._modules is None:
            with (_DATA_DIR / "mode_data_all_normalized.json").open(encoding="utf-8") as f:
                self._modules = json.load(f)
        return self._modules


_store = _ModeDataStore()


def _match_prefix(device_model: str) -> str | None:
    """Longest-prefix match of ``device_model`` against the 45 known prefixes."""
    matched: list[tuple[int, str]] = []
    for prefix, series in _store.prefixes.items():
        if device_model.startswith(prefix):
            matched.append((len(prefix), series))
    if not matched:
        return None
    matched.sort(reverse=True)
    return matched[0][1]


def _series_matches(branch_series: str, series: str) -> bool:
    """Return True if ``branch_series`` (e.g. ``"isM1|isM1Overseas"``) covers ``series``."""
    return series in branch_series.split("|")


def _resolve_module(series: str | None, location: str | None, feature_bits: int = 0) -> int:
    """Resolve the data-module id for a series + region + feature bits.

    Branches are tried in order and the first match wins.  ``location=None``
    (or an unknown region) falls through to each branch's default module.

    One branch (``isPoseidonPro``) has a ``feature`` condition — it requires
    the ``deep_self_clean`` feature bit (``ZeoFeatureBits.deep_self_clean``,
    bit 19); without it the plain ``isPoseidonPro`` branch is used instead.
    """
    for branch in _store.selector:
        branch_series = branch["series"]
        if series is not None and _series_matches(branch_series, series):
            feature = branch.get("feature")
            if feature == "deep_self_clean":
                if not (feature_bits & (1 << int(ZeoFeatureBits.deep_self_clean))):
                    continue  # condition not met → try the next branch
            regions = branch.get("regions", {})
            if location is not None and location in regions:
                return int(regions[location])
            return int(branch["default"])
    # fallback branch
    return int(_store.selector[-1]["default"])


def resolve_mode_templates(
    device_model: str,
    location: str | None = None,
    feature_bits: int = 0,
    *,
    in_app_only: bool = False,
) -> list[ZeoModeTemplate]:
    """Resolve the mode templates for a device.

    Args:
        device_model: The device model string, e.g. ``"roborock.wm.a92"`` (M1S).
        location: Optional two-letter region code (``jp``, ``tw``, ``kr``,
            ``de``, ``au``, ``ru``, ``ch``, ``no``, ``my``, ``th``).  ``None``
            selects each branch's default (mainland China) module.
        feature_bits: The device's ``FEATURE_BITS`` (DP 237) value, used for
            the ``isPoseidonPro`` + ``deep_self_clean`` branch selection and
            for gating the 30-minute soak level
            (``ZeoFeatureBits.thirty_min_soak``, bit 8).  ``0`` is a safe
            default (no deep self-clean, no 30-minute soak).
        in_app_only: Drop entries with ``is_in_app`` ``False``.  The mode data
            contains every entry the device accepts, including internal ones
            flagged as hidden, so callers building a picker usually want this
            set.

    Returns:
        A list of :class:`ZeoModeTemplate`, in data order.
    """
    module_id = resolve_data_module(device_model, location, feature_bits)
    return build_mode_templates(module_id, feature_bits, in_app_only=in_app_only)


def resolve_data_module(
    device_model: str,
    location: str | None = None,
    feature_bits: int = 0,
) -> int:
    """The data-module id for a device.

    Every device resolves to exactly one data module, and that module is the
    single source of its programme table.  Callers that need a device's
    :mod:`~roborock.data.zeo.zeo_program_configs` entries start here.

    Args:
        device_model: The device model string, e.g. ``"roborock.wm.a92"`` (M1S).
        location: Optional two-letter region code; ``None`` selects each
            branch's default (mainland China) module.
        feature_bits: The device's ``FEATURE_BITS`` (DP 237) value — only the
            ``isPoseidonPro`` + ``deep_self_clean`` branch depends on it.

    Returns:
        A data-module id present in ``mode_data_all_normalized.json``.  A model
        matching no known series falls back to the final branch.
    """
    return _resolve_module(_match_prefix(device_model), location, feature_bits)


def build_mode_templates(
    module_id: int,
    feature_bits: int = 0,
    *,
    in_app_only: bool = False,
) -> list[ZeoModeTemplate]:
    """Build the mode templates for a data-module id.

    Args:
        module_id: A data-module id from ``mode_selector_map.json``.
        feature_bits: The device's ``FEATURE_BITS`` (DP 237) value, used to
            gate the 30-minute soak level (``ZeoFeatureBits.thirty_min_soak``).
        in_app_only: Drop entries with ``is_in_app`` ``False``.

    Returns:
        One :class:`ZeoModeTemplate` per mode in the module, in data order.
        An unknown module id yields an empty list.
    """
    raw_modes = _store.modules.get(str(module_id), [])
    templates = [_mode_from_raw(raw, feature_bits) for raw in raw_modes]
    if in_app_only:
        return [template for template in templates if template.is_in_app]
    return templates


#: The bucket name for each ``ZeoMode``.
_BUCKETS: dict[ZeoMode, str] = {
    ZeoMode.wash: "wash",
    ZeoMode.wash_and_dry: "wash_and_dry",
    ZeoMode.dry: "dry",
    ZeoMode.treatment: "treatment",
}

# The cloud programme is hidden from the per-mode buckets: it appears only in
# ``other``.
_MODE_BUCKET_EXCLUDED = (ZeoProgram.custom,)

# Programmes gathered into ``other``: the cloud programme and the drum
# self-clean programme.  ``down_clean`` keeps its per-mode bucket membership.
_OTHER_PROGRAMS = (ZeoProgram.custom, ZeoProgram.down_clean)


def split_mode_templates(templates: Sequence[ZeoModeTemplate]) -> ZeoModeLists:
    """Split templates into the per-mode groups a picker needs.

    The cloud programme is excluded from the per-mode buckets and gathered into
    ``other`` together with the drum self-clean programme.  ``down_clean`` keeps
    its per-mode bucket membership, so the buckets are *not* a partition:
    ``down_clean`` entries appear in two buckets.  ``all_modes`` keeps every
    entry exactly once.
    """
    lists = ZeoModeLists(all_modes=list(templates))
    for template in templates:
        if template.dp in _OTHER_PROGRAMS:
            lists.other.append(template)
        if template.dp in _MODE_BUCKET_EXCLUDED:
            continue
        bucket = _BUCKETS.get(template.program_type)
        if bucket is not None:
            getattr(lists, bucket).append(template)
    return lists

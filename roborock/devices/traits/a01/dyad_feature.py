"""Dyad model capabilities.

The Roborock app decides what a Dyad supports from its model series and variant.
These sets follow the model table and capability checks in the app plugin. Only the
F25 Ultra (`a194`) has been checked against a real device.

Model IDs are the last part of the model name, for example `a194` in `roborock.wdv.a194`.
"""

from __future__ import annotations

from roborock.data.dyad.dyad_code_mappings import DyadCleanMode

_HALBERD = frozenset({"a55", "a56", "a61", "a107"})  # Dyad Pro, Dyad Air
_COMBO = frozenset({"a82", "a83", "a99", "a108"})  # Dyad Pro Combo
_SABER_BASE = frozenset({"a80", "a81"})
_SABER_PLUS = frozenset({"a137", "a138"})
_DAGGER = frozenset({"a109", "a110", "a111", "a112", "a113", "a132", "a145"})  # Flexi, Flexi Pro
_MARVIS = frozenset({"a365", "a366", "a367", "a368", "a369"})
_MORPH_WITH_INTENSITY = frozenset(
    {
        "a150",
        "a151",  # F25 ACE
        "a173",
        "a174",  # F25 ACE Combo
        "a259",
        "a260",  # F25 ACE Pro
        "a319",
        "a320",  # F25 Pro Turbo
        "a341",
        "a342",  # F25 Pro Turbo Combo
    }
)
_MORPH = _MORPH_WITH_INTENSITY | frozenset(
    {
        "a152",
        "a163",
        "a165",
        "a171",
        "a175",
        "a177",
        "a200",
        "a238",  # F25 XT
        "a251",
        "a252",
        "a253",
        "a280",
        "a283",
        "a309",
        "a310",
        "a313",
        "a314",
        "a315",
        "a316",
        "a317",
        "a318",
        "a323",
        "a343",
        "a344",
    }
)
_YAOGUANG = frozenset(
    {
        "a193",
        "a194",  # F25 Ultra
        "a202",
        "a256",
        "a257",
        "a263",
        "a264",
        "a285",
        "a286",
        "a289",
        "a299",
        "a300",  # F25 Ultra Steam Gen 2
        "a301",
        "a321",
        "a322",
        "a356",
        "a357",
        "a362",
        "a363",
        "a364",
    }
)

_ALL_MODELS = _HALBERD | _COMBO | _SABER_BASE | _SABER_PLUS | _DAGGER | _MARVIS | _MORPH | _YAOGUANG
_SMART_SELF_CLEAN = _DAGGER | _SABER_PLUS | _MORPH | _YAOGUANG | _MARVIS
_DRYING_MODE = _MORPH | _YAOGUANG
_CLEAN_INTENSITY = _MORPH_WITH_INTENSITY | _YAOGUANG
_SELF_CLEAN_PAUSE = _ALL_MODELS - _DAGGER - _SABER_PLUS

_CLEAN_MODES_WITHOUT_SPONGE = frozenset({DyadCleanMode.auto, DyadCleanMode.max, DyadCleanMode.power_saving})
_CLEAN_MODES_WITH_SPONGE = _CLEAN_MODES_WITHOUT_SPONGE | {DyadCleanMode.dehydration}
_CLEAN_MODES_HEATED = frozenset(
    {DyadCleanMode.auto, DyadCleanMode.steam, DyadCleanMode.hot_water, DyadCleanMode.dehydration}
)


def _model_id(model: str | None) -> str | None:
    """Return the model ID from a full model name."""
    return model.rsplit(".", 1)[-1] if model else None


def is_known_model(model: str | None) -> bool:
    """Return whether the model is in the app's Dyad model table."""
    return _model_id(model) in _ALL_MODELS


def supports_drying_mode(model: str | None) -> bool:
    """Return whether the silent drying data point holds a drying mode instead of a duration."""
    return _model_id(model) in _DRYING_MODE


def supports_smart_self_clean(model: str | None) -> bool:
    """Return whether the model has the smart self-clean intensity."""
    return _model_id(model) in _SMART_SELF_CLEAN


def supports_clean_intensity(model: str | None) -> bool:
    """Return whether the app offers suction levels paired with a brush speed, and water levels."""
    return _model_id(model) in _CLEAN_INTENSITY


def clean_modes(model: str | None) -> frozenset[DyadCleanMode]:
    """Return the clean modes the app offers for the model, empty for an unknown model."""
    model_id = _model_id(model)
    if model_id not in _ALL_MODELS:
        return frozenset()
    if model_id in _YAOGUANG:
        return _CLEAN_MODES_HEATED
    if model_id in _DAGGER | _SABER_PLUS:
        return _CLEAN_MODES_WITHOUT_SPONGE
    return _CLEAN_MODES_WITH_SPONGE


def supports_self_clean_pause(model: str | None) -> bool:
    """Return whether self-clean can be paused."""
    return _model_id(model) in _SELF_CLEAN_PAUSE

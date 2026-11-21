"""Tests for the Dyad model capabilities."""

import pytest

from roborock.data.dyad.dyad_code_mappings import DyadCleanMode
from roborock.devices.traits.a01 import dyad_feature

AUTO_MAX_SAVING = {DyadCleanMode.auto, DyadCleanMode.max, DyadCleanMode.power_saving}
WITH_SPONGE = AUTO_MAX_SAVING | {DyadCleanMode.dehydration}
HEATED = {DyadCleanMode.auto, DyadCleanMode.steam, DyadCleanMode.hot_water, DyadCleanMode.dehydration}


@pytest.mark.parametrize(
    ("model", "drying_mode", "smart_self_clean", "clean_intensity", "self_clean_pause", "clean_modes"),
    [
        # Halberd
        ("roborock.wetdryvac.a56", False, False, False, True, WITH_SPONGE),
        # Combo
        ("roborock.wetdryvac.a83", False, False, False, True, WITH_SPONGE),
        # Saber
        ("roborock.wetdryvac.a81", False, False, False, True, WITH_SPONGE),
        # Saber Plus
        ("roborock.wetdryvac.a138", False, True, False, False, AUTO_MAX_SAVING),
        # Dagger
        ("roborock.wetdryvac.a132", False, True, False, False, AUTO_MAX_SAVING),
        # Morph with suction and water levels
        ("roborock.wetdryvac.a151", True, True, True, True, WITH_SPONGE),
        # Morph without them
        ("roborock.wetdryvac.a238", True, True, False, True, WITH_SPONGE),
        # YaoGuang
        ("roborock.wdv.a194", True, True, True, True, HEATED),
        # Marvis, CN and INT models
        ("roborock.wdv.a365", False, True, False, True, WITH_SPONGE),
        ("roborock.wdv.a366", False, True, False, True, WITH_SPONGE),
        ("roborock.wdv.a367", False, True, False, True, WITH_SPONGE),
        ("roborock.wdv.a368", False, True, False, True, WITH_SPONGE),
        ("roborock.wdv.a369", False, True, False, True, WITH_SPONGE),
        ("roborock.wdv.a370", False, True, False, True, WITH_SPONGE),
    ],
)
def test_model_capabilities(
    model: str,
    drying_mode: bool,
    smart_self_clean: bool,
    clean_intensity: bool,
    self_clean_pause: bool,
    clean_modes: set[DyadCleanMode],
):
    """Each series has the capabilities the app gives it."""
    assert dyad_feature.is_known_model(model)
    assert dyad_feature.supports_drying_mode(model) is drying_mode
    assert dyad_feature.supports_smart_self_clean(model) is smart_self_clean
    assert dyad_feature.supports_clean_intensity(model) is clean_intensity
    assert dyad_feature.supports_self_clean_pause(model) is self_clean_pause
    assert dyad_feature.clean_modes(model) == clean_modes


@pytest.mark.parametrize("model", [None, "", "roborock.wdv.a999", "roborock.wm.a102"])
def test_unknown_model_has_no_capabilities(model: str | None):
    """A model outside the app's table gets nothing."""
    assert not dyad_feature.is_known_model(model)
    assert not dyad_feature.supports_drying_mode(model)
    assert not dyad_feature.supports_smart_self_clean(model)
    assert not dyad_feature.supports_clean_intensity(model)
    assert not dyad_feature.supports_self_clean_pause(model)
    assert dyad_feature.clean_modes(model) == frozenset()

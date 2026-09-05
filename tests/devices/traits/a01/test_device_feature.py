"""Tests for A01 (Zeo) per-model feature gating."""

import pytest

from roborock.devices.traits.a01.device_feature import build_force_load_dp_list, supports_default_setting
from roborock.roborock_message import RoborockZeoProtocol


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("roborock.wm.a63", False),  # H1
        ("roborock.wm.a102", True),  # H1 Overseas
        ("roborock.wm.a90", True),  # H1 Lite
        (None, True),  # unknown model: assume supported
    ],
)
def test_supports_default_setting(model: str | None, expected: bool) -> None:
    """DP 225 is unsupported on H1 (a63) only."""
    assert supports_default_setting(model) is expected


def test_force_load_omits_default_setting_for_h1() -> None:
    """H1 (a63) has a softener compartment but must not be queried for DP 225."""
    dp_list = build_force_load_dp_list("roborock.wm.a63")

    assert RoborockZeoProtocol.DEFAULT_SETTING not in dp_list
    # The remaining softener DPs are still queried.
    assert RoborockZeoProtocol.SOFTENER_SET in dp_list
    assert RoborockZeoProtocol.SOFTENER_TYPE in dp_list
    assert RoborockZeoProtocol.SOFTENER_EMPTY in dp_list


def test_force_load_keeps_default_setting_for_other_softener_models() -> None:
    """Other softener-equipped models still query DP 225."""
    assert RoborockZeoProtocol.DEFAULT_SETTING in build_force_load_dp_list("roborock.wm.a102")


def test_force_load_omits_default_setting_without_softener() -> None:
    """Models without a softener compartment never query DP 225."""
    assert RoborockZeoProtocol.DEFAULT_SETTING not in build_force_load_dp_list("roborock.wm.a92")

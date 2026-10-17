"""Tests for the CustomizeCleanModeTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.devices.traits.v1.customize_clean_mode import (
    CustomizeCleanModeTrait,
    SegmentCleanMode,
)
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand

CUSTOMIZE_CLEAN_MODE_DATA = [
    {"segment": 4, "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
    {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
]


@pytest.fixture(name="customize_clean_mode_trait")
def customize_clean_mode_trait_fixture(mock_rpc_channel: AsyncMock) -> CustomizeCleanModeTrait:
    """Create a CustomizeCleanModeTrait with mocked dependencies.

    This is constructed directly rather than via the `device` fixture: unlike
    the dock-gated optional traits, there is no existing test helper for
    parametrizing the `new_feature_info` bit this trait is gated on, and the
    other `requires_feature`-gated optional traits (child_lock, led_status,
    valley_electricity_timer) do not have discovery-level tests either.
    """
    trait = CustomizeCleanModeTrait()
    trait._rpc_channel = mock_rpc_channel  # type: ignore[assignment]
    return trait


async def test_refresh(customize_clean_mode_trait: CustomizeCleanModeTrait, mock_rpc_channel: AsyncMock) -> None:
    """Rooms with an override are parsed into SegmentCleanMode entries."""
    mock_rpc_channel.send_command.side_effect = [CUSTOMIZE_CLEAN_MODE_DATA]

    await customize_clean_mode_trait.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE)
    assert customize_clean_mode_trait.modes == [
        SegmentCleanMode(segment=4, fan_power=102, water_box_mode=203, mop_mode=300, repeat=1, seq_type=0),
        SegmentCleanMode(segment=7, fan_power=101, water_box_mode=203, mop_mode=300, repeat=1, seq_type=1),
    ]
    assert customize_clean_mode_trait.by_segment[7].clean_then_mop is True
    assert customize_clean_mode_trait.by_segment[4].clean_then_mop is False


async def test_refresh_no_overrides(
    customize_clean_mode_trait: CustomizeCleanModeTrait, mock_rpc_channel: AsyncMock
) -> None:
    """An empty response means no room currently has a custom clean mode."""
    mock_rpc_channel.send_command.side_effect = [[]]

    await customize_clean_mode_trait.refresh()

    assert customize_clean_mode_trait.modes == []
    assert customize_clean_mode_trait.by_segment == {}


async def test_refresh_bad_format(
    customize_clean_mode_trait: CustomizeCleanModeTrait, mock_rpc_channel: AsyncMock
) -> None:
    """A non-list response is a parsing error, not a silent empty result."""
    mock_rpc_channel.send_command.side_effect = [{"unexpected": "shape"}]

    with pytest.raises(RoborockParsingException):
        await customize_clean_mode_trait.refresh()


@pytest.mark.parametrize(("seq_type", "expected"), [(1, True), (0, False), (None, None)])
def test_clean_then_mop(seq_type: int | None, expected: bool | None) -> None:
    """seq_type reports whether a room is vacuumed before it is mopped."""
    mode = SegmentCleanMode(segment=1, seq_type=seq_type)

    assert mode.clean_then_mop is expected


@pytest.mark.parametrize(
    ("enabled", "mop_mode", "repeat", "expected_params"),
    [
        (
            True,
            300,
            1,
            {"segment": 7, "fan_power": 101, "water_box_mode": 203, "seq_type": 1, "mop_mode": 300, "repeat": 1},
        ),
        (True, None, None, {"segment": 7, "fan_power": 101, "water_box_mode": 203, "seq_type": 1}),
        (False, 300, None, {"segment": 7, "fan_power": 101, "water_box_mode": 203, "seq_type": 0, "mop_mode": 300}),
    ],
)
async def test_set_clean_then_mop(
    customize_clean_mode_trait: CustomizeCleanModeTrait,
    mock_rpc_channel: AsyncMock,
    enabled: bool,
    mop_mode: int | None,
    repeat: int | None,
    expected_params: dict[str, int],
) -> None:
    """The setter sends the room's full clean mode alongside the sequence type, then refreshes."""
    mock_rpc_channel.send_command.side_effect = ["ok", CUSTOMIZE_CLEAN_MODE_DATA]

    await customize_clean_mode_trait.set_clean_then_mop(
        7, enabled, fan_power=101, water_box_mode=203, mop_mode=mop_mode, repeat=repeat
    )

    assert mock_rpc_channel.send_command.mock_calls == [
        call(RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE, params=[expected_params]),
        call(RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE),
    ]
    assert customize_clean_mode_trait.by_segment[7].clean_then_mop is True

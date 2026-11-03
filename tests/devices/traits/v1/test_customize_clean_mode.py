"""Tests for the CustomizeCleanModeTrait class."""

import asyncio
from unittest.mock import AsyncMock, call

import pytest

from roborock.data import HomeDataDevice, SegmentCleanMode
from roborock.data.v1.v1_clean_modes import CleanRoutes, VacuumModes, WaterModes
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.customize_clean_mode import CustomizeCleanModeTrait
from roborock.exceptions import RoborockParsingException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

CUSTOMIZE_CLEAN_MODE_DATA = [
    {"segment": 4, "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
    {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
]

# S7 MaxV / a27 (the suite's default device) supports per-room custom modes
# but not clean-then-mop specifically - real devices, used below for
# test_set_clean_then_mop_unsupported without needing to fake it.
# Saros 10R is the only fixture device with BOTH features True - used for
# every test that actually exercises set_clean_then_mop's happy path.
SAROS_10R = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"][0]
S5E = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s5e.json"][0]


@pytest.fixture(name="customize_clean_mode_trait")
def customize_clean_mode_trait_fixture(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CustomizeCleanModeTrait | None:
    """Return the discovered CustomizeCleanModeTrait from the device."""
    assert device.v1_properties
    return device.v1_properties.customize_clean_mode


@pytest.mark.parametrize("device_info", [S5E])
async def test_unsupported_customize_clean_mode(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    device_info: HomeDataDevice,
) -> None:
    """Trait is not initialized when is_customized_clean_supported is False."""
    assert customize_clean_mode_trait is None


async def test_refresh(customize_clean_mode_trait: CustomizeCleanModeTrait | None, mock_rpc_channel: AsyncMock) -> None:
    """Rooms with an override are parsed into SegmentCleanMode entries."""
    assert customize_clean_mode_trait is not None
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
    customize_clean_mode_trait: CustomizeCleanModeTrait | None, mock_rpc_channel: AsyncMock
) -> None:
    """An empty response means no room currently has a custom clean mode."""
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [[]]

    await customize_clean_mode_trait.refresh()

    assert customize_clean_mode_trait.modes == []
    assert customize_clean_mode_trait.by_segment == {}


async def test_refresh_bad_format(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None, mock_rpc_channel: AsyncMock
) -> None:
    """A non-list response is a parsing error, not a silent empty result."""
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [{"unexpected": "shape"}]

    with pytest.raises(RoborockParsingException):
        await customize_clean_mode_trait.refresh()


async def test_refresh_bad_list_entry(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None, mock_rpc_channel: AsyncMock
) -> None:
    """A malformed entry inside the list is a parsing error, not silently dropped."""
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [["ok"]]

    with pytest.raises(RoborockParsingException):
        await customize_clean_mode_trait.refresh()


async def test_refresh_duplicate_segment_raises(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None, mock_rpc_channel: AsyncMock
) -> None:
    """Two entries resolving to the same segment id is an ambiguous table, not silently collapsed.

    Regression test for a real gap found in review: the raw-preservation
    cache used to be built by a plain dict comprehension, which would
    silently keep only the LAST entry for a duplicated segment id and lose
    the other - an ambiguous table should be treated as unsafe to write
    from, not quietly resolved.
    """
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [
        [
            {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
            {"segment": 7, "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
        ]
    ]

    with pytest.raises(RoborockParsingException):
        await customize_clean_mode_trait.refresh()


@pytest.mark.parametrize(("seq_type", "expected"), [(1, True), (0, False), (None, None)])
def test_clean_then_mop(seq_type: int | None, expected: bool | None) -> None:
    """seq_type reports whether a room is vacuumed before it is mopped."""
    mode = SegmentCleanMode(segment=1, seq_type=seq_type)

    assert mode.clean_then_mop is expected


@pytest.mark.parametrize("device_info", [SAROS_10R])
@pytest.mark.parametrize(
    ("enabled", "repeat", "expected_entry"),
    [
        (True, 2, {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 2, "seq_type": 1}),
        (
            True,
            None,
            {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
        ),
        (
            False,
            None,
            {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
        ),
    ],
)
async def test_set_clean_then_mop(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
    enabled: bool,
    repeat: int | None,
    expected_entry: dict[str, int],
) -> None:
    """The setter always sends mop_mode and repeat (the device rejects a request missing
    mop_mode, and silently resets repeat to 1 rather than preserving it if left out) alongside
    the room's other settings and the sequence type, then refreshes."""
    assert customize_clean_mode_trait is not None
    # Refresh is called internally to fetch the existing table before writing,
    # then again after the write - two GET responses are consumed. The second
    # (post-write) response reflects what was actually written for segment 7,
    # not a static fixture - otherwise this test can't catch a setter that
    # sends the wrong seq_type (see the enabled=False case, which caught a
    # real bug: the original test's post-write mock was the same static
    # all-enabled fixture regardless of `enabled`, so clean_then_mop was
    # always asserted True even when enabled=False was never actually
    # exercised).
    refreshed_segment_4 = {
        "segment": 4,
        "fan_power": 102,
        "water_box_mode": 203,
        "mop_mode": 300,
        "repeat": 1,
        "seq_type": 0,
    }
    mock_rpc_channel.send_command.side_effect = [
        CUSTOMIZE_CLEAN_MODE_DATA,
        "ok",
        [refreshed_segment_4, expected_entry],
    ]
    kwargs = {"fan_power": 101, "water_box_mode": 203, "mop_mode": 300}
    if repeat is not None:
        kwargs["repeat"] = repeat

    await customize_clean_mode_trait.set_clean_then_mop(7, enabled, **kwargs)

    assert mock_rpc_channel.send_command.mock_calls == [
        call(RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE),
        call(
            RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE,
            params=[
                {"segment": 4, "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
                expected_entry,
            ],
        ),
        call(RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE),
    ]
    assert customize_clean_mode_trait.by_segment[7].clean_then_mop is enabled


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_accepts_typed_modes(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """fan_power/water_box_mode/mop_mode accept the typed mode enums, not just raw ints."""
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [CUSTOMIZE_CLEAN_MODE_DATA, "ok", CUSTOMIZE_CLEAN_MODE_DATA]

    await customize_clean_mode_trait.set_clean_then_mop(
        7,
        True,
        fan_power=VacuumModes.BALANCED,
        water_box_mode=WaterModes.HIGH,
        mop_mode=CleanRoutes.DEEP,
    )

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    segment_7 = next(entry for entry in sent_params if entry["segment"] == 7)
    assert segment_7 == {
        "segment": 7,
        "fan_power": VacuumModes.BALANCED.code,
        "water_box_mode": WaterModes.HIGH.code,
        "mop_mode": CleanRoutes.DEEP.code,
        "repeat": 1,
        "seq_type": 1,
    }


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_preserves_other_rooms(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """Updating one room's override must not drop another room's existing override.

    Some V1 firmware replaces the whole customized-segment table rather than
    patching a single entry, so sending only the changed room would silently
    wipe other rooms. The full known table (segment 4 untouched, segment 7
    updated) must be sent on every write.
    """
    assert customize_clean_mode_trait is not None
    mock_rpc_channel.send_command.side_effect = [CUSTOMIZE_CLEAN_MODE_DATA, "ok", CUSTOMIZE_CLEAN_MODE_DATA]

    await customize_clean_mode_trait.set_clean_then_mop(7, False, fan_power=101, water_box_mode=203, mop_mode=300)

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    assert {entry["segment"] for entry in sent_params} == {4, 7}
    segment_4 = next(entry for entry in sent_params if entry["segment"] == 4)
    assert segment_4 == {
        "segment": 4,
        "fan_power": 102,
        "water_box_mode": 203,
        "mop_mode": 300,
        "repeat": 1,
        "seq_type": 0,
    }


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_preserves_model_specific_fields(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """Model-specific fields (e.g. mop_power) on the room being updated must not be stripped."""
    assert customize_clean_mode_trait is not None
    data_with_mop_power = [
        {
            "segment": 7,
            "fan_power": 101,
            "water_box_mode": 203,
            "mop_mode": 300,
            "repeat": 1,
            "seq_type": 0,
            "mop_power": 50,
        },
    ]
    mock_rpc_channel.send_command.side_effect = [data_with_mop_power, "ok", data_with_mop_power]

    await customize_clean_mode_trait.set_clean_then_mop(7, True, fan_power=101, water_box_mode=203, mop_mode=300)

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    assert sent_params == [
        {
            "segment": 7,
            "fan_power": 101,
            "water_box_mode": 203,
            "mop_mode": 300,
            "repeat": 1,
            "seq_type": 1,
            "mop_power": 50,
        }
    ]


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_preserves_unknown_field_on_untouched_room(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """A wire field this library doesn't model at all must still survive on an untouched room.

    Regression test for a real gap found in review: adding named fields
    (mop_power, custom_water_box_distance) to SegmentCleanMode only fixes
    those two keys specifically, not the general problem of truly unknown
    per-model keys. The setter must round-trip untouched rooms from their
    raw wire dict, not reconstruct them from typed fields.
    """
    assert customize_clean_mode_trait is not None
    data_with_unknown_field = [
        {
            "segment": 4,
            "fan_power": 102,
            "water_box_mode": 203,
            "mop_mode": 300,
            "repeat": 1,
            "seq_type": 0,
            "some_future_field_this_library_does_not_model": 999,
        },
        {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
    ]
    mock_rpc_channel.send_command.side_effect = [data_with_unknown_field, "ok", data_with_unknown_field]

    await customize_clean_mode_trait.set_clean_then_mop(7, False, fan_power=101, water_box_mode=203, mop_mode=300)

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    segment_4 = next(entry for entry in sent_params if entry["segment"] == 4)
    assert segment_4["some_future_field_this_library_does_not_model"] == 999


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_untouched_room_survives_mismatched_key_casing(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """An untouched room must not vanish from the write just because its raw dict spells
    "segment" differently (e.g. "Segment").

    Regression test for a real gap found in review: the raw-preservation
    cache used to be keyed by the literal `entry["segment"]` lookup, which
    silently excluded this room entirely (case-sensitive dict access) even
    though typed parsing (which decamelizes keys) correctly recognized it as
    segment 4 - so updating a DIFFERENT room would drop room 4 from the
    write without any error. The cache must be keyed by the canonical typed
    segment id instead.
    """
    assert customize_clean_mode_trait is not None
    data_with_capitalized_key = [
        {"Segment": 4, "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
        {"segment": 7, "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 1},
    ]
    mock_rpc_channel.send_command.side_effect = [data_with_capitalized_key, "ok", data_with_capitalized_key]

    await customize_clean_mode_trait.set_clean_then_mop(7, False, fan_power=101, water_box_mode=203, mop_mode=300)

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    assert {entry.get("segment", entry.get("Segment")) for entry in sent_params} == {4, 7}


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_segment_id_as_string_does_not_duplicate(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """A room reported with a stringified segment id ("7" instead of 7) must not end up sent
    twice - once under the original string key, once under the new integer key.

    Regression test for a real gap found in review: the raw cache used to be
    keyed by the raw, unconverted value, while the write path looks the room
    up by the caller-supplied int `segment`. A string/int mismatch meant
    `raw_entries.get(segment)` missed the existing raw entry (so model-
    specific fields on THIS room would also have been silently dropped) and
    the old string-keyed entry was never removed, so both ended up in the
    final SET payload for what the device would see as the same room.
    """
    assert customize_clean_mode_trait is not None
    data_with_string_segment = [
        {"segment": "7", "fan_power": 101, "water_box_mode": 203, "mop_mode": 300, "repeat": 1, "seq_type": 0},
    ]
    mock_rpc_channel.send_command.side_effect = [data_with_string_segment, "ok", data_with_string_segment]

    await customize_clean_mode_trait.set_clean_then_mop(7, True, fan_power=101, water_box_mode=203, mop_mode=300)

    sent_params = mock_rpc_channel.send_command.mock_calls[1].kwargs["params"]
    assert len(sent_params) == 1
    assert sent_params[0]["segment"] == 7
    assert sent_params[0]["seq_type"] == 1


async def test_set_clean_then_mop_unsupported(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Writing clean-then-mop on a device that doesn't support it raises, not silently sends seq_type.

    Uses the default device fixture (S7 MaxV / a27): it genuinely supports
    per-room custom modes but not clean-then-mop specifically, matching real
    hardware, rather than faking unsupport on a device that does support it.
    """
    assert customize_clean_mode_trait is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await customize_clean_mode_trait.set_clean_then_mop(7, True, fan_power=101, water_box_mode=203, mop_mode=300)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_set_clean_then_mop_concurrent_calls_do_not_clobber(
    customize_clean_mode_trait: CustomizeCleanModeTrait | None,
    mock_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
) -> None:
    """Two concurrent set_clean_then_mop calls for different rooms must not revert each other.

    Regression test for a real race found in review: without serializing the
    read-merge-write sequence, two concurrent calls (room 4, room 7) can each
    read the same starting table, then the second call's full-table write
    overwrites the first call's change because it was built from a stale
    snapshot that didn't see the first write yet.
    """
    assert customize_clean_mode_trait is not None

    # A minimal stateful fake device: GET returns the current table, SET
    # replaces it - same contract the real device has. This is what makes
    # the test meaningful: a non-stateful mock can't distinguish "read a
    # stale snapshot" from "read the latest state", which is exactly the
    # bug being guarded against.
    device_table = {entry["segment"]: dict(entry) for entry in CUSTOMIZE_CLEAN_MODE_DATA}

    # Without forcing it, asyncio won't actually interleave these two calls
    # at all: a plain async mock with no real suspension point lets the
    # first task run to completion before the second one gets scheduled, so
    # the race never has a chance to manifest either way - the lock's effect
    # couldn't be observed one way or the other. Force a genuine suspension
    # point on every call instead so the two tasks CAN interleave at the
    # event loop's discretion; whether they actually end up clobbering each
    # other then depends entirely on whether the lock serializes the whole
    # read-merge-write transaction (it must: the lock makes `set_clean_then_mop`
    # block here, not just at this one call, until the other task's whole
    # transaction - all 3 round trips - has finished).
    async def _send_command(command: RoborockCommand, params: list[dict] | None = None) -> object:
        await asyncio.sleep(0)
        if command is RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE:
            return list(device_table.values())
        assert command is RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE
        assert params is not None
        device_table.clear()
        device_table.update({entry["segment"]: entry for entry in params})
        return "ok"

    mock_rpc_channel.send_command.side_effect = _send_command

    await asyncio.gather(
        customize_clean_mode_trait.set_clean_then_mop(4, True, fan_power=102, water_box_mode=203, mop_mode=300),
        customize_clean_mode_trait.set_clean_then_mop(7, False, fan_power=101, water_box_mode=203, mop_mode=300),
    )

    set_calls = [
        c for c in mock_rpc_channel.send_command.mock_calls if c.args[:1] == (RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE,)
    ]
    assert len(set_calls) == 2
    # Final device state must have BOTH intended changes - room 4 enabled,
    # room 7 disabled. Without the lock, the second call's write (built from
    # a stale pre-first-call read) would revert whichever room the first
    # call changed.
    assert {segment: entry["seq_type"] for segment, entry in device_table.items()} == {4: 1, 7: 0}

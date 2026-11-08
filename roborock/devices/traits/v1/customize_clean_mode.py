"""Trait for per-room (segment) cleaning mode overrides on Roborock devices.

Rooms without an override are simply absent from `modes` - the robot falls
back to the global settings (fan power, water box mode, mop mode and
clean-then-mop) for those. An empty list means no room currently has one.

A per-room override set via `set_clean_then_mop` is persisted on the device:
it is a preference attached to that room and is re-applied whenever the room
is cleaned, until overwritten or cleared from the vendor app.
"""

import asyncio

from roborock.data import CustomizeCleanModes, SegmentCleanMode
from roborock.data.v1.v1_clean_modes import CleanRoutes, VacuumModes, WaterModes
from roborock.data.v1.v1_containers import SEQ_TYPE_CLEAN_THEN_MOP
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockParsingException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

from .common import V1ResponseData

_WRITE_KEYS = ("segment", "fan_power", "water_box_mode", "mop_mode", "repeat", "seq_type")


class CustomizeCleanModeConverter(common.V1TraitDataConverter):
    """Converts get_customize_clean_mode responses to CustomizeCleanModes."""

    def convert(self, response: V1ResponseData) -> CustomizeCleanModes:
        """Parse the response from the device into a CustomizeCleanModes."""
        if not isinstance(response, list) or not all(isinstance(entry, dict) for entry in response):
            raise ValueError(f"Unexpected CustomizeCleanModes response format: {response!r}")
        return CustomizeCleanModes(modes=[SegmentCleanMode.from_dict(entry) for entry in response])


class CustomizeCleanModeTrait(CustomizeCleanModes, common.V1TraitMixin):
    """Trait for reading and writing per-room clean mode overrides.

    Gated on `is_customized_clean_supported` - the feature that covers
    `get/set_customize_clean_mode` in general, not `is_clean_then_mop_mode_supported`
    (which only gates the narrower `seq_type` axis within it). A device can
    support per-room custom modes without supporting clean-then-mop
    specifically; on such a device `SegmentCleanMode.seq_type` (and therefore
    `.clean_then_mop`) is simply `None` for every room, same as when the
    device never reports it. `set_clean_then_mop` additionally checks
    `is_clean_then_mop_mode_supported` itself before writing, since writing
    `seq_type` to firmware that doesn't support it is not just a no-op read.
    """

    command = RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE
    converter = CustomizeCleanModeConverter()
    requires_feature = "is_customized_clean_supported"

    def __init__(self, device_features: DeviceFeaturesTrait) -> None:
        super().__init__()
        common.V1TraitMixin.__init__(self)
        self._device_features = device_features
        self._raw_by_segment: dict[int, dict] = {}
        self._write_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Refresh the contents of this trait.

        Overrides `V1TraitMixin.refresh()` to additionally retain each
        room's raw wire dict, by segment - `set_clean_then_mop` round-trips
        untouched rooms from this raw data rather than the typed
        `SegmentCleanMode` fields, so per-model keys this library doesn't
        model (or a value it failed to parse) are preserved on write instead
        of being silently dropped.
        """
        response = await self.rpc_channel.send_command(self.command)
        try:
            new_data = self.converter.convert(response)
        except (TypeError, ValueError) as err:
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=self.command,
                payload=response,
                inner_error=err,
            ) from err
        assert isinstance(response, list) and new_data.modes is not None  # converter.convert already validated this
        # Key the raw cache off the canonical TYPED segment id (int, already
        # decamelized/coerced by SegmentCleanMode.from_dict), not the raw
        # dict's own "segment" key - a device that ever sent a differently
        # cased key (e.g. "Segment") or a stringified id ("7" instead of 7)
        # would otherwise desync the raw cache from `by_segment`, so this
        # same room would be silently missing from (or duplicated in) a
        # later write. `response` and `new_data.modes` are the same length,
        # in the same order, by construction (one SegmentCleanMode per raw
        # entry, no filtering) - zip(strict=True) turns any future change to
        # that invariant into a loud error instead of silent misalignment.
        raw_by_segment: dict[int, dict] = {}
        for raw_entry, mode in zip(response, new_data.modes, strict=True):
            if mode.segment in raw_by_segment:
                raise RoborockParsingException(
                    trait_name=type(self).__name__,
                    command=self.command,
                    payload=response,
                    inner_error=ValueError(f"Duplicate segment {mode.segment} in response, cannot safely write"),
                )
            raw_by_segment[mode.segment] = raw_entry
        common.merge_trait_values(self, new_data)
        self._raw_by_segment = raw_by_segment

    async def set_clean_then_mop(
        self,
        segment: int,
        enabled: bool,
        *,
        fan_power: VacuumModes | int,
        water_box_mode: WaterModes | int,
        mop_mode: CleanRoutes | int,
        repeat: int = 1,
    ) -> None:
        """Set whether a single room is vacuumed fully before it is mopped.

        The firmware requires the room's full clean mode alongside the
        sequence type, not the flag on its own, so callers pass through the
        fan power / water box mode / mop mode that room already cleans with
        - typically read from the room's existing `SegmentCleanMode` (via
        `by_segment`) - so this call only changes the order, not the
        settings. `fan_power`, `water_box_mode` and `mop_mode` accept either
        the typed mode enum or a raw wire int (for codes this library
        doesn't model, e.g. water-slide values).

        Do NOT source these from `StatusTrait` as a fallback when a room has
        no override yet: while the device is in a per-room custom cleaning
        mode, `StatusTrait` itself reports the sentinel "customized" codes
        (`fan_power=106`, `water_box_mode=204`, `mop_mode=302`) rather than
        real settings, and those sentinels are not valid values to echo back
        here.

        `fan_power`, `water_box_mode` and `mop_mode` are all required: the
        device rejects the request outright (`Param error, no mop_mode`) if
        `mop_mode` is left out, confirmed against a real device - this isn't
        a case where a missing field is silently defaulted.

        `repeat` defaults to `1` rather than being left out when the caller
        doesn't have an opinion: omitting it from the wire request is NOT a
        no-op on the device, which resets it to `1` instead of preserving
        whatever the room's `repeat` was set to before this call - confirmed
        against a real device. Pass the room's current `repeat` explicitly if
        you want a different value preserved.

        Raises `RoborockUnsupportedFeature` if the device doesn't support
        clean-then-mop at all (`is_clean_then_mop_mode_supported`), even if
        it does support per-room custom modes in general.

        This whole read-merge-write sequence is serialized per trait
        instance (concurrent calls queue rather than racing): the device's
        SET_CUSTOMIZE_CLEAN_MODE replaces the whole per-room table rather
        than patching one entry (see below), so two overlapping calls each
        building their own full table from the same stale read would
        otherwise silently revert each other's room.
        """
        if not self._device_features.is_clean_then_mop_mode_supported:
            raise RoborockUnsupportedFeature("Device does not support clean-then-mop")

        async with self._write_lock:
            # Always refresh immediately before building the write, even if
            # `self.modes` is already populated: this merges-and-replaces
            # the whole table (see below), so writing from a stale cache
            # could silently revert another room's override changed since
            # the last refresh (e.g. from the vendor app) back to its old
            # value.
            await self.refresh()

            seq_type = SEQ_TYPE_CLEAN_THEN_MOP if enabled else 0
            new_entry = {
                "segment": segment,
                "fan_power": fan_power.code if isinstance(fan_power, VacuumModes) else fan_power,
                "water_box_mode": water_box_mode.code if isinstance(water_box_mode, WaterModes) else water_box_mode,
                "mop_mode": mop_mode.code if isinstance(mop_mode, CleanRoutes) else mop_mode,
                "repeat": repeat,
                "seq_type": seq_type,
            }
            # Start from this room's raw wire dict (if it already had an
            # override) so any field this library doesn't model - or
            # couldn't parse - survives the write, and only overlay the keys
            # this call actually changes. A room with no prior override
            # gets only the known fields; the device fills in its own
            # per-model defaults for the rest, same as the original
            # single-entry write did.
            raw_entries = dict(self._raw_by_segment)
            raw_entries[segment] = {**raw_entries.get(segment, {}), **new_entry}

            # Send the full known table, not just the changed room: on at
            # least some V1 firmware (confirmed first-hand for a Saros 20
            # Sonic, see https://github.com/orgs/home-assistant/discussions/3998),
            # SET_CUSTOMIZE_CLEAN_MODE replaces the customized segment table
            # rather than patching a single entry, so sending only
            # `[new_entry]` would silently wipe every other room's
            # override. This has not been re-verified against real hardware
            # for THIS device since this fix was written (no second
            # customized room available to test with); please confirm on a
            # device with two or more customized rooms before relying on
            # it.
            await self.rpc_channel.send_command(
                RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE, params=list(raw_entries.values())
            )
            await self.refresh()

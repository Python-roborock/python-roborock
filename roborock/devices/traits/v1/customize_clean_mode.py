"""Trait for per-room (segment) cleaning mode overrides on Roborock devices.

This exposes the same "vacuum then mop" axis as `StatusTrait.clean_then_mop`
(the global, per-job flag), but scoped to a single room. Where the global
flag is per-job and clears after every clean, a per-room override set here
is persisted on the device: it is a preference attached to that room and is
re-applied whenever the room is cleaned, until overwritten or cleared from
the vendor app.

Rooms without an override are simply absent from `modes` - the robot falls
back to the global settings (fan power, water box mode, mop mode and
clean-then-mop) for those. An empty list means no room currently has one.
"""

from dataclasses import dataclass

from roborock.data import RoborockBase
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

from .common import V1ResponseData

_SEQ_TYPE_CLEAN_THEN_MOP = 1


@dataclass
class SegmentCleanMode(RoborockBase):
    """A single room's clean mode override, as reported by the device."""

    segment: int
    fan_power: int | None = None
    water_box_mode: int | None = None
    mop_mode: int | None = None
    repeat: int | None = None
    seq_type: int | None = None

    @property
    def clean_then_mop(self) -> bool | None:
        """Whether this room is vacuumed fully before it is mopped.

        `None` means the device did not report a sequence type for this
        room's override.
        """
        if self.seq_type is None:
            return None
        return self.seq_type == _SEQ_TYPE_CLEAN_THEN_MOP


@dataclass
class CustomizeCleanModes(RoborockBase):
    """Collection of per-room clean mode overrides."""

    modes: list[SegmentCleanMode] | None = None

    @property
    def by_segment(self) -> dict[int, SegmentCleanMode]:
        """Index the overrides by segment id."""
        return {mode.segment: mode for mode in self.modes or []}


class CustomizeCleanModeConverter(common.V1TraitDataConverter):
    """Converts get_customize_clean_mode responses to CustomizeCleanModes."""

    def convert(self, response: V1ResponseData) -> CustomizeCleanModes:
        """Parse the response from the device into a CustomizeCleanModes."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected CustomizeCleanModes response format: {response!r}")
        return CustomizeCleanModes(
            modes=[SegmentCleanMode.from_dict(entry) for entry in response if isinstance(entry, dict)]
        )


class CustomizeCleanModeTrait(CustomizeCleanModes, common.V1TraitMixin):
    """Trait for reading and writing per-room clean mode overrides.

    This is the per-room counterpart to `StatusTrait.clean_then_mop` /
    `StatusTrait.set_clean_then_mop`. Both are gated by the same device
    feature: no device has been found that supports the global toggle but
    not the per-room one, since the vendor app presents them as a single
    "vacuum then mop" switch that can be applied globally or per room.
    """

    command = RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE
    converter = CustomizeCleanModeConverter()
    requires_feature = "is_clean_then_mop_mode_supported"

    async def set_clean_then_mop(
        self,
        segment: int,
        enabled: bool,
        *,
        fan_power: int,
        water_box_mode: int,
        mop_mode: int,
        repeat: int | None = None,
    ) -> None:
        """Set whether a single room is vacuumed fully before it is mopped.

        The firmware requires the room's full clean mode alongside the
        sequence type, not the flag on its own, so callers pass through the
        fan power / water box mode / mop mode that room already cleans with
        - typically read from the room's existing `SegmentCleanMode` (via
        `by_segment`) or, if the room has no override yet, from `StatusTrait`
        - so this call only changes the order, not the settings.

        `fan_power`, `water_box_mode` and `mop_mode` are all required: the
        device rejects the request outright (`Param error, no mop_mode`) if
        `mop_mode` is left out, confirmed against a real device - this isn't
        a case where a missing field is silently defaulted.

        `repeat` is the one genuinely optional field, but omitting it is NOT
        a no-op: the device resets it to its own default (observed: 1)
        rather than preserving whatever the room's `repeat` was set to
        before this call - also confirmed against a real device. Pass the
        room's current `repeat` explicitly if you want it preserved.
        """
        seq_type = _SEQ_TYPE_CLEAN_THEN_MOP if enabled else 0
        entry: dict[str, int] = {
            "segment": segment,
            "fan_power": fan_power,
            "water_box_mode": water_box_mode,
            "mop_mode": mop_mode,
            "seq_type": seq_type,
        }
        if repeat is not None:
            entry["repeat"] = repeat
        await self.rpc_channel.send_command(RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE, params=[entry])
        await self.refresh()

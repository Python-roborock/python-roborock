"""Trait for per-room (segment) cleaning mode overrides on Roborock devices.

This exposes the same "vacuum then mop" axis as `StatusTrait.clean_then_mop`
(the global, per-job flag), but scoped to a single room. The global flag is
itself persisted on the device - tracked while docked, not cleared after
every clean (see `StatusTrait.clean_then_mop`) - and a per-room override set
here is likewise persisted: it is a preference attached to that room and is
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
        if not isinstance(response, list) or not all(isinstance(entry, dict) for entry in response):
            raise ValueError(f"Unexpected CustomizeCleanModes response format: {response!r}")
        return CustomizeCleanModes(modes=[SegmentCleanMode.from_dict(entry) for entry in response])


class CustomizeCleanModeTrait(CustomizeCleanModes, common.V1TraitMixin):
    """Trait for reading and writing per-room clean mode overrides.

    This is the per-room counterpart to `StatusTrait.clean_then_mop` /
    `StatusTrait.set_clean_then_mop`. Gated on `is_customized_clean_supported`
    - the feature that covers `get/set_customize_clean_mode` in general, not
    `is_clean_then_mop_mode_supported` (which only gates the narrower
    `seq_type` axis within it). A device can support per-room custom modes
    without supporting clean-then-mop specifically; on such a device
    `SegmentCleanMode.seq_type` (and therefore `.clean_then_mop`) is simply
    `None` for every room, same as when the device never reports it.
    """

    command = RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE
    converter = CustomizeCleanModeConverter()
    requires_feature = "is_customized_clean_supported"

    async def set_clean_then_mop(
        self,
        segment: int,
        enabled: bool,
        *,
        fan_power: int,
        water_box_mode: int,
        mop_mode: int,
        repeat: int = 1,
    ) -> None:
        """Set whether a single room is vacuumed fully before it is mopped.

        The firmware requires the room's full clean mode alongside the
        sequence type, not the flag on its own, so callers pass through the
        fan power / water box mode / mop mode that room already cleans with
        - typically read from the room's existing `SegmentCleanMode` (via
        `by_segment`) - so this call only changes the order, not the
        settings.

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
        """
        seq_type = _SEQ_TYPE_CLEAN_THEN_MOP if enabled else 0
        entry: dict[str, int] = {
            "segment": segment,
            "fan_power": fan_power,
            "water_box_mode": water_box_mode,
            "mop_mode": mop_mode,
            "repeat": repeat,
            "seq_type": seq_type,
        }
        await self.rpc_channel.send_command(RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE, params=[entry])
        await self.refresh()

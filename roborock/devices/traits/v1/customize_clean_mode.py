"""Trait for per-room (segment) cleaning mode overrides on Roborock devices.

Rooms without an override are absent from `modes` (the robot falls back to
global settings for those; an empty list means no room has an override).

Per-room overrides are persisted on the device across cleaning runs and take
effect when cleaning with the global mode set to custom (`CleaningMode.CUSTOM`
where supported). When cleaning in an explicit global mode (`VACUUM`,
`VAC_AND_MOP`, `MOP`, or `SMART_MODE`), global settings take precedence.
"""

import asyncio
from typing import Any

from roborock.data import CustomizeCleanModes, SegmentCleanMode
from roborock.data.v1.v1_clean_modes import CleanRoutes, VacuumModes, WaterModes
from roborock.data.v1.v1_containers import SEQ_TYPE_CLEAN_THEN_MOP
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockParsingException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

from .common import V1ResponseData

# StatusTrait reports these sentinel codes while in custom or smart plan modes;
# they are not valid concrete per-room settings.
_INVALID_FAN_POWER_CODES = frozenset({VacuumModes.CUSTOMIZED.code, VacuumModes.SMART_MODE.code})
_INVALID_WATER_MODE_CODES = frozenset({WaterModes.CUSTOMIZED.code, WaterModes.SMART_MODE.code})
_INVALID_MOP_MODE_CODES = frozenset({CleanRoutes.CUSTOMIZED.code, CleanRoutes.SMART_MODE.code})


def _resolve_mode_codes(
    fan_power: VacuumModes | int | None,
    water_box_mode: WaterModes | int | None,
    mop_mode: CleanRoutes | int | None,
) -> tuple[int | None, int | None, int | None]:
    """Unwrap mode enums to wire codes and reject global sentinel codes."""
    fan_code = fan_power.code if isinstance(fan_power, VacuumModes) else fan_power
    water_code = water_box_mode.code if isinstance(water_box_mode, WaterModes) else water_box_mode
    mop_code = mop_mode.code if isinstance(mop_mode, CleanRoutes) else mop_mode

    if fan_code in _INVALID_FAN_POWER_CODES:
        raise ValueError(f"Invalid per-segment fan_power sentinel code: {fan_code}")
    if water_code in _INVALID_WATER_MODE_CODES:
        raise ValueError(f"Invalid per-segment water_box_mode sentinel code: {water_code}")
    if mop_code in _INVALID_MOP_MODE_CODES:
        raise ValueError(f"Invalid per-segment mop_mode sentinel code: {mop_code}")

    return fan_code, water_code, mop_code


class CustomizeCleanModeConverter(common.V1TraitDataConverter):
    """Converts get_customize_clean_mode responses to CustomizeCleanModes."""

    def convert(self, response: V1ResponseData) -> CustomizeCleanModes:
        """Parse the response from the device into a CustomizeCleanModes."""
        if not isinstance(response, list) or not all(isinstance(entry, dict) for entry in response):
            raise ValueError(f"Unexpected CustomizeCleanModes response format: {response!r}")
        return CustomizeCleanModes(modes=[SegmentCleanMode.from_dict(entry) for entry in response])


class CustomizeCleanModeTrait(CustomizeCleanModes, common.V1TraitMixin):
    """Trait for reading and writing per-room clean mode overrides.

    Gated on `is_customized_clean_supported` (which covers
    `get/set_customize_clean_mode` in general), while `repeat` and
    `clean_then_mop` writes are additionally gated on
    `is_custom_clean_mode_count_supported` and
    `is_clean_then_mop_mode_supported`.
    """

    command = RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE
    converter = CustomizeCleanModeConverter()
    requires_feature = "is_customized_clean_supported"

    def __init__(self, device_features: DeviceFeaturesTrait) -> None:
        super().__init__()
        common.V1TraitMixin.__init__(self)
        self._device_features = device_features
        self._raw_by_segment: dict[int, dict[str, Any]] = {}
        self._write_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Refresh the contents of this trait.

        Retains each room's raw wire dict keyed by canonical typed segment id
        so writes round-trip untouched rooms and unmodeled per-model fields.
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
        assert isinstance(response, list) and new_data.modes is not None
        # Key by canonical typed `mode.segment` (decamelized/coerced to int) so
        # `_raw_by_segment` stays aligned with `by_segment` across casing/type quirks.
        raw_by_segment: dict[int, dict[str, Any]] = {}
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
        fan_power: VacuumModes | int | None = None,
        water_box_mode: WaterModes | int | None = None,
        mop_mode: CleanRoutes | int | None = None,
        repeat: int | None = None,
    ) -> None:
        """Set whether a single room is vacuumed fully before it is mopped.

        Delegates to `set_segment_clean_mode(..., clean_then_mop=enabled)`;
        omitted mode/repeat arguments preserve an existing room's settings.
        """
        await self.set_segment_clean_mode(
            segment,
            fan_power=fan_power,
            water_box_mode=water_box_mode,
            mop_mode=mop_mode,
            repeat=repeat,
            clean_then_mop=enabled,
        )

    async def set_segment_clean_mode(
        self,
        segment: int,
        *,
        fan_power: VacuumModes | int | None = None,
        water_box_mode: WaterModes | int | None = None,
        mop_mode: CleanRoutes | int | None = None,
        repeat: int | None = None,
        clean_then_mop: bool | None = None,
    ) -> None:
        """Set or update a single room's custom cleaning mode override.

        Omitted fields preserve the room's existing override when present. For
        a room without an existing override, `fan_power`, `water_box_mode`, and
        `mop_mode` are required (firmware rejects requests missing `mop_mode`)
        and `repeat` defaults to `1` (omitting `repeat` on wire resets it to `1`
        on firmware).

        Do not pass `StatusTrait` mode values as a fallback: while in custom or
        smart plan mode, `StatusTrait` reports sentinel codes (`106/204/302` or
        `110/209/306`), which are rejected with `ValueError`.
        """
        if all(v is None for v in (fan_power, water_box_mode, mop_mode, repeat, clean_then_mop)):
            raise ValueError("At least one clean mode setting must be provided")
        if clean_then_mop is not None and not self._device_features.is_clean_then_mop_mode_supported:
            raise RoborockUnsupportedFeature("Device does not support clean-then-mop")
        if repeat is not None:
            if not self._device_features.is_custom_clean_mode_count_supported:
                raise RoborockUnsupportedFeature("Device does not support per-segment repeat count")
            if repeat < 1:
                raise ValueError(f"repeat must be >= 1, got {repeat}")

        fan_code, water_code, mop_code = _resolve_mode_codes(fan_power, water_box_mode, mop_mode)

        # Serialize read-merge-write since SET_CUSTOMIZE_CLEAN_MODE replaces the
        # entire per-room table on V1 firmware rather than patching a single entry.
        async with self._write_lock:
            # Always refresh immediately before merging so a full-table SET
            # never clobbers external edits (e.g. from the vendor app or a map switch).
            await self.refresh()

            existing_mode = self.by_segment.get(segment) or SegmentCleanMode(segment=segment)
            if (
                (fan_code if fan_code is not None else existing_mode.fan_power) is None
                or (water_code if water_code is not None else existing_mode.water_box_mode) is None
                or (mop_code if mop_code is not None else existing_mode.mop_mode) is None
            ):
                raise ValueError(
                    "fan_power, water_box_mode, and mop_mode must be provided when not already set "
                    f"on segment {segment}"
                )

            updates: dict[str, int | None] = {
                "segment": segment,
                "fan_power": fan_code,
                "water_box_mode": water_code,
                "mop_mode": mop_code,
                "repeat": (
                    (repeat or existing_mode.repeat or 1)
                    if self._device_features.is_custom_clean_mode_count_supported
                    else None
                ),
                "seq_type": (SEQ_TYPE_CLEAN_THEN_MOP if clean_then_mop else 0) if clean_then_mop is not None else None,
            }
            new_entry = {k: v for k, v in updates.items() if v is not None}

            # Overlay updated keys onto this room's raw dict (preserving any
            # unmodeled per-model fields) and send the full segment table.
            raw_entries = dict(self._raw_by_segment)
            raw_entries[segment] = {**raw_entries.get(segment, {}), **new_entry}

            await self.rpc_channel.send_command(
                RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE, params=list(raw_entries.values())
            )
            await self.refresh()

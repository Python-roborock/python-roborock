"""Data containers for Zeo (washing machine / dryer) devices."""

from dataclasses import dataclass

from ..containers import RoborockBase
from .zeo_code_mappings import (
    ZeoDryAndCare,
    ZeoDryingMethod,
    ZeoDryingMode,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoak,
    ZeoSpin,
    ZeoSteamVolume,
    ZeoTemperature,
)


@dataclass
class ZeoStartParams(RoborockBase):
    """Parameters that must be bundled with a START command.

    All Zeo devices require ``mode`` and ``program`` to be sent together
    with the start signal. The remaining fields are optional and only
    included when the device reports a non-None value.
    """

    mode: ZeoMode
    program: ZeoProgram
    temperature: ZeoTemperature | None = None
    rinse: ZeoRinse | None = None
    spin: ZeoSpin | None = None
    drying_mode: ZeoDryingMode | None = None


# ── DP 222 (LoadCloudProgram) bitfield decoder ──────────────────────────
# The official app packs all custom-program parameters into a single
# 32-bit integer at DP 222.  This mirrors WasherDpsCache.customMode in
# module 725 of the React Native plugin bundle.


@dataclass
class ZeoCustomMode(RoborockBase):
    """Decoded custom programme parameters from DP 222 (LoadCloudProgram).

    Null / absent fields are represented as ``0`` which matches the
    official app's behaviour (the right-shifted-and-masked value is
    always non-negative).
    """

    program: ZeoProgram
    """Wash program (bits 0-7)."""

    mode: ZeoMode
    """Wash mode (bits 8-9)."""

    temperature: ZeoTemperature
    """Temperature (bits 10-12)."""

    rinse: ZeoRinse
    """Rinse cycle (bits 13-15)."""

    spin: ZeoSpin
    """Spin speed (bits 16-18)."""

    drying_mode: ZeoDryingMode
    """Drying mode (bits 19-21)."""

    soak: ZeoSoak
    """Soak (bits 22-24)."""

    dry_and_care: ZeoDryAndCare
    """Dry-care mode (bits 25-27)."""

    steam_volume: ZeoSteamVolume
    """Steam volume (bits 28-30)."""

    total_time_min: int = 0
    """Total programme time in minutes (from DP 239)."""

    @classmethod
    def from_raw(cls, raw: int, total_time_min: int | None = None) -> "ZeoCustomMode":
        """Decode a raw 32-bit custom-programme value."""
        return cls(
            program=ZeoProgram(raw & 0xFF),
            mode=ZeoMode((raw >> 8) & 0x3),
            temperature=ZeoTemperature((raw >> 10) & 0x7),
            rinse=ZeoRinse((raw >> 13) & 0x7),
            spin=ZeoSpin((raw >> 16) & 0x7),
            drying_mode=ZeoDryingMode((raw >> 19) & 0x7),
            soak=ZeoSoak((raw >> 22) & 0x7),
            dry_and_care=ZeoDryAndCare((raw >> 25) & 0x7),
            steam_volume=ZeoSteamVolume((raw >> 28) & 0x7),
            total_time_min=total_time_min or 0,
        )


@dataclass
class ZeoDryerCustomMode(RoborockBase):
    """Decoded custom programme from DP 222 for a standalone dryer.

    Dryers pack a different (shorter) bitfield than washers — only 5
    fields after program/mode.  Mirrors ``WasherDpsCache.dryerCustomMode``
    in module 725 of the plugin bundle.
    """

    program: ZeoProgram
    """Drying program (bits 0-7)."""

    mode: ZeoMode
    """Drying mode (bits 8-10)."""

    drying_mode: ZeoDryingMode
    """Drying level (bits 11-13)."""

    drying_method: ZeoDryingMethod
    """Drying method (bits 14-16)."""

    steam_volume: ZeoSteamVolume
    """Steam volume (bits 17-19)."""

    total_time_min: int = 0
    """Total programme time in minutes (from DP 239)."""

    @classmethod
    def from_raw(cls, raw: int, total_time_min: int | None = None) -> "ZeoDryerCustomMode":
        """Decode a raw 32-bit dryer custom-programme value."""
        return cls(
            program=ZeoProgram(raw & 0xFF),
            # Dryer mode spans bits 8-10 (0x700, 3 bits) because the
            # temperature field is absent from the dryer bitfield and
            # bit 10 is re-allocated to mode.  Washer uses 2 bits
            # (0x300, bits 8-9) to make room for temperature at 10-12.
            mode=ZeoMode((raw >> 8) & 0x7),
            drying_mode=ZeoDryingMode((raw >> 11) & 0x7),
            drying_method=ZeoDryingMethod((raw >> 14) & 0x7),
            steam_volume=ZeoSteamVolume((raw >> 17) & 0x7),
            total_time_min=total_time_min or 0,
        )

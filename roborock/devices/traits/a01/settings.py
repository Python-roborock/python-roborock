"""Typed writable state and setters for Zeo (washing machine / dryer) devices.

This module provides ``ZeoSettingTrait``, a single typed trait holding the
*writable* state of a Zeo device (mode, programme, wash/dry parameters,
auto-dosing, switches) plus its typed setters. The trait is shared across
washers and dryers: washers expose wash parameters (temperature, rinse, spin,
drying mode, soak, dry care) and dryers expose drying parameters (drying
method, steam volume). Fields that a given device family does not support
simply remain ``None``.

Read-only device state (state code, errors, timers, tank levels, ...) lives
in :mod:`roborock.devices.traits.a01.status` (``ZeoStatusTrait``).
"""

import datetime
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from roborock.data.code_mappings import RoborockEnum
from roborock.data.containers import RoborockBase
from roborock.data.zeo.zeo_code_mappings import (
    ZeoDetergentExpansionType,
    ZeoDetergentType,
    ZeoDryAndCare,
    ZeoDryingMethod,
    ZeoDryingMode,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoak,
    ZeoSoftenerExpansionType,
    ZeoSoftenerType,
    ZeoSpin,
    ZeoSteamVolume,
    ZeoTemperature,
)
from roborock.data.zeo.zeo_containers import ZeoStartParams
from roborock.devices.rpc.a01_channel import send_decoded_command
from roborock.devices.traits.a01.device_feature import (
    ZeoFeatures,
    is_addition_type_control_auto_addition,
    is_hyperion_halia_hera,
    supports_uv_light,
)
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.mqtt.session import MqttQos
from roborock.roborock_message import RoborockZeoProtocol

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T", bound=RoborockEnum)

FeaturesFn = Callable[[], ZeoFeatures | None]

# Map ZeoStartParams field names to their DP ids.
# Field → DP ordering follows the order
# (wash branch): Start, Mode, Program, Soak, Temperature, Rinse, Spin,
# DryingMode, DryCareMode, DryingMethod, SteamVolume.
_FIELD_TO_DP: dict[str, RoborockZeoProtocol] = {
    "mode": RoborockZeoProtocol.MODE,
    "program": RoborockZeoProtocol.PROGRAM,
    "soak": RoborockZeoProtocol.SOAK,
    "temperature": RoborockZeoProtocol.TEMP,
    "rinse": RoborockZeoProtocol.RINSE_TIMES,
    "spin": RoborockZeoProtocol.SPIN_LEVEL,
    "drying_mode": RoborockZeoProtocol.DRYING_MODE,
    "dry_and_care": RoborockZeoProtocol.DRY_CARE_MODE,
    "drying_method": RoborockZeoProtocol.DRYING_METHOD,
    "steam_volume": RoborockZeoProtocol.STEAM_VOLUME,
    "total_time": RoborockZeoProtocol.TOTAL_TIME,
}


def build_param_dps(params: ZeoStartParams) -> dict[RoborockZeoProtocol, Any]:
    """Map the params onto their DP ids for a START/preset frame.

    - ``mode``/``program`` are always sent.
    - Every other optional enum parameter is pushed only when it is non-null.
    - ``total_time`` (DP 234) is only sent when ``> 0`` — it doubles as the
      washer/dryer branch selector.
    """
    # TODO(program-config): ``total_time`` is a fixed programme-config value
    dps: dict[RoborockZeoProtocol, Any] = {}
    for field_name, dp in _FIELD_TO_DP.items():
        val = getattr(params, field_name)
        if field_name == "total_time":
            if val is not None and val > 0:
                dps[dp] = val
        elif field_name in ("mode", "program"):
            if val is not None:
                dps[dp] = val
        elif val is not None and int(val) != 0:
            # Skip "empty" enum members (null/none/empty = 0), matching the
            # Bundle's `x != null` guards for optional parameters.
            dps[dp] = val
    return dps


@dataclass(init=False)
class ZeoSettingTrait(RoborockBase, TraitUpdateListener):
    """Base trait holding shared Zeo state and providing typed setters."""

    # Shared writable state (both washers and dryers), updated from the MQTT
    # push stream. Read-only state lives in ``ZeoStatusTrait`` (status.py).
    mode: ZeoMode | None = field(default=None, metadata={"dps": RoborockZeoProtocol.MODE})
    program: ZeoProgram | None = field(default=None, metadata={"dps": RoborockZeoProtocol.PROGRAM})
    # Countdown for a delayed start (minutes). Writable via preset_with; the
    # device also reports the active countdown here.
    countdown: int | None = field(default=None, metadata={"dps": RoborockZeoProtocol.COUNTDOWN})

    # Washer-specific state (None on dryers).
    temperature: ZeoTemperature | None = field(default=None, metadata={"dps": RoborockZeoProtocol.TEMP})
    rinse: ZeoRinse | None = field(default=None, metadata={"dps": RoborockZeoProtocol.RINSE_TIMES})
    spin: ZeoSpin | None = field(default=None, metadata={"dps": RoborockZeoProtocol.SPIN_LEVEL})
    drying_mode: ZeoDryingMode | None = field(default=None, metadata={"dps": RoborockZeoProtocol.DRYING_MODE})
    soak: ZeoSoak | None = field(default=None, metadata={"dps": RoborockZeoProtocol.SOAK})
    dry_and_care: ZeoDryAndCare | None = field(default=None, metadata={"dps": RoborockZeoProtocol.DRY_CARE_MODE})

    # Dryer-specific state (None on washers). Note ``total_time`` is read-only
    # (device-reported running duration) and lives in ZeoStatusTrait.
    drying_method: ZeoDryingMethod | None = field(default=None, metadata={"dps": RoborockZeoProtocol.DRYING_METHOD})
    steam_volume: ZeoSteamVolume | None = field(default=None, metadata={"dps": RoborockZeoProtocol.STEAM_VOLUME})

    # Auto-dosing state (washers only; None on dryers). ``detergent_set``/
    # ``softener_set`` are the dedicated toggles on new series, while
    # ``detergent_type``/``softener_type`` double as the toggle on old series
    # (where a non-``none`` type implies auto-addition is on).
    detergent_set: bool | None = field(default=None, metadata={"dps": RoborockZeoProtocol.DETERGENT_SET})
    softener_set: bool | None = field(default=None, metadata={"dps": RoborockZeoProtocol.SOFTENER_SET})
    detergent_type: ZeoDetergentType | None = field(default=None, metadata={"dps": RoborockZeoProtocol.DETERGENT_TYPE})
    softener_type: ZeoSoftenerType | None = field(default=None, metadata={"dps": RoborockZeoProtocol.SOFTENER_TYPE})

    # Feature-gated boolean state (shared across washers and dryers).
    ion_deodorization: bool | None = field(default=None, metadata={"dps": RoborockZeoProtocol.ION_DEODORIZATION})
    wash_dry_linked: bool | None = field(default=None, metadata={"dps": RoborockZeoProtocol.WASH_DRY_LINKED})

    def __init__(
        self,
        channel: MqttChannel,
        *,
        model: str | None,
        is_dryer: bool,
        features: FeaturesFn,
    ) -> None:
        """Initialize the settings trait."""
        TraitUpdateListener.__init__(self, _LOGGER)
        self._channel = channel
        self._model = model
        self._is_dryer = is_dryer
        self._features = features
        self._converter = DpsDataConverter.from_dataclass(type(self))

    def update_from_dps(self, decoded_dps: dict[int, Any]) -> bool:
        """Update trait fields from raw device DPS data.

        Returns True if any field changed (and notifies update listeners).
        """
        if self._converter.update_from_dps(self, decoded_dps):
            self._notify_update()
            return True
        return False

    @property
    def auto_detergent(self) -> bool | None:
        """Whether auto-dosing of detergent is on, derived from series state."""
        if self._is_dryer:
            return None
        if is_addition_type_control_auto_addition(self._model):
            return self.detergent_type is not None and self.detergent_type != ZeoDetergentType.empty
        return self.detergent_set

    @property
    def auto_softener(self) -> bool | None:
        """Whether auto-dosing of softener is on, derived from series state."""
        if self._is_dryer:
            return None
        if is_addition_type_control_auto_addition(self._model):
            return self.softener_type is not None and self.softener_type != ZeoSoftenerType.empty
        return self.softener_set

    async def _set_enum(
        self, dp: RoborockZeoProtocol, enum_cls: type[_T], value: _T
    ) -> dict[RoborockZeoProtocol, Any]:
        """Validate *value* against *enum_cls* and send it to the device."""
        if not isinstance(value, enum_cls):
            raise TypeError(f"Expected {enum_cls.__name__}, got {type(value).__name__}")
        return await self._send({dp: int(value)})

    # -- Start-parameter setters (TEST-ONLY) --------------------------------
    #
    # The individual setters below (mode/program/temperature/rinse/spin/
    # drying_mode/soak/dry_and_care/drying_method/steam_volume plus the
    # feature-gated ion_deodorization/wash_dry_linked setters) each map to a
    # DP that is *also* carried by the START command (see ``ZeoStartParams``
    # and ``build_param_dps``). Although the device responds to these
    # single-DP writes, they have no practical use in production: a start
    # sends the caller-supplied ``ZeoStartParams`` values, not the state held
    # here.
    #
    # They are retained purely as a test/debug convenience.

    async def set_mode(self, mode: ZeoMode) -> dict[RoborockZeoProtocol, Any]:
        """Set the current mode (DP 204). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.MODE, ZeoMode, mode)

    async def set_program(self, program: ZeoProgram) -> dict[RoborockZeoProtocol, Any]:
        """Set the current programme (DP 205). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.PROGRAM, ZeoProgram, program)

    # -- Washer-specific setters --------------------------------------------

    async def set_temperature(self, temperature: ZeoTemperature) -> dict[RoborockZeoProtocol, Any]:
        """Set the wash temperature (DP 207). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.TEMP, ZeoTemperature, temperature)

    async def set_rinse(self, rinse: ZeoRinse) -> dict[RoborockZeoProtocol, Any]:
        """Set the rinse count (DP 208). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.RINSE_TIMES, ZeoRinse, rinse)

    async def set_spin(self, spin: ZeoSpin) -> dict[RoborockZeoProtocol, Any]:
        """Set the spin speed (DP 209). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.SPIN_LEVEL, ZeoSpin, spin)

    async def set_drying_mode(self, drying_mode: ZeoDryingMode) -> dict[RoborockZeoProtocol, Any]:
        """Set the drying mode (DP 210). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.DRYING_MODE, ZeoDryingMode, drying_mode)

    async def set_soak(self, soak: ZeoSoak) -> dict[RoborockZeoProtocol, Any]:
        """Set the soak level (DP 233). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.SOAK, ZeoSoak, soak)

    async def set_dry_and_care(self, dry_and_care: ZeoDryAndCare) -> dict[RoborockZeoProtocol, Any]:
        """Set the dry-and-care mode (DP 244). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.DRY_CARE_MODE, ZeoDryAndCare, dry_and_care)

    # -- Dryer-specific setters ---------------------------------------------

    async def set_drying_method(self, drying_method: ZeoDryingMethod) -> dict[RoborockZeoProtocol, Any]:
        """Set the drying method (DP 256). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.DRYING_METHOD, ZeoDryingMethod, drying_method)

    async def set_steam_volume(self, steam_volume: ZeoSteamVolume) -> dict[RoborockZeoProtocol, Any]:
        """Set the steam volume (DP 257). Test-only: carried by START."""
        return await self._set_enum(RoborockZeoProtocol.STEAM_VOLUME, ZeoSteamVolume, steam_volume)

    async def set_detergent_type(self, detergent_type: ZeoDetergentType) -> dict[RoborockZeoProtocol, Any]:
        """Set the detergent type (DP 213), optionally toggling auto-dosing."""
        e = int(detergent_type)
        dps: dict[RoborockZeoProtocol, Any]
        if is_addition_type_control_auto_addition(self._model):
            dps = {RoborockZeoProtocol.DETERGENT_TYPE: e}
        elif is_hyperion_halia_hera(self._model):
            if e == 0:
                dps = {RoborockZeoProtocol.DETERGENT_SET: 0}
            else:
                dps = {
                    RoborockZeoProtocol.DETERGENT_SET: 1,
                    RoborockZeoProtocol.DETERGENT_TYPE: e,
                }
        else:
            dps = {
                RoborockZeoProtocol.DETERGENT_SET: 0 if e == 0 else 1,
                RoborockZeoProtocol.DETERGENT_TYPE: e,
            }
        return await self._send(dps)

    async def set_softener_type(self, softener_type: ZeoSoftenerType) -> dict[RoborockZeoProtocol, Any]:
        """Set the softener type (DP 214)."""
        e = int(softener_type)
        dps: dict[RoborockZeoProtocol, Any]
        if is_addition_type_control_auto_addition(self._model):
            dps = {RoborockZeoProtocol.SOFTENER_TYPE: e}
        elif is_hyperion_halia_hera(self._model):
            if e == 0:
                dps = {RoborockZeoProtocol.SOFTENER_SET: 0}
            else:
                dps = {
                    RoborockZeoProtocol.SOFTENER_SET: 1,
                    RoborockZeoProtocol.SOFTENER_TYPE: e,
                }
        else:
            dps = {
                RoborockZeoProtocol.SOFTENER_SET: 0 if e == 0 else 1,
                RoborockZeoProtocol.SOFTENER_TYPE: e,
            }
        return await self._send(dps)

    async def set_detergent_box_type(
        self, expansion_type: ZeoDetergentExpansionType
    ) -> dict[RoborockZeoProtocol, Any]:
        """Set the detergent expansion type (DP 248)."""
        dps = {RoborockZeoProtocol.DETERGENT_EXPANSION_TYPE: int(expansion_type)}
        return await self._send(dps)

    async def set_softener_box_type(
        self, expansion_type: ZeoSoftenerExpansionType
    ) -> dict[RoborockZeoProtocol, Any]:
        """Set the softener expansion type (DP 245)."""
        dps = {RoborockZeoProtocol.SOFTENER_EXPANSION_TYPE: int(expansion_type)}
        return await self._send(dps)

    async def set_cleanser_config(
        self,
        auto_detergent: bool,
        auto_softener: bool,
        detergent_type: ZeoDetergentType,
        softener_type: ZeoSoftenerType,
    ) -> dict[RoborockZeoProtocol, Any]:
        """Set the full cleanser config in one command (DP 211/212/213/214)."""
        dps: dict[RoborockZeoProtocol, Any] = {
            RoborockZeoProtocol.DETERGENT_SET: 1 if auto_detergent else 0,
            RoborockZeoProtocol.SOFTENER_SET: 1 if auto_softener else 0,
            RoborockZeoProtocol.DETERGENT_TYPE: int(detergent_type),
            RoborockZeoProtocol.SOFTENER_TYPE: int(softener_type),
        }
        return await self._send(dps)

    async def set_voice_volume(self, volume: int) -> dict[RoborockZeoProtocol, Any]:
        """Set the voice volume (DP 10009)."""
        dps = {RoborockZeoProtocol.VOICE_VOLUME: json.dumps({"snd_volume": volume})}
        return await self._send(dps)

    async def set_voice_switch(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable voice assistant (DP 10301)."""
        dps = {
            RoborockZeoProtocol.VOICE_SWITCH: json.dumps(
                {"speech_switch": 1 if enabled else 0}
            )
        }
        return await self._send(dps)

    async def delete_voice_record(self, record_id: str) -> dict[RoborockZeoProtocol, Any]:
        """Delete a voice record by id (DP 10304)."""
        dps = {
            RoborockZeoProtocol.VOICE_RECORD_DELETE: json.dumps(
                {"dialog_delete": record_id}
            )
        }
        return await self._send(dps)

    async def set_sound_package(self, package: dict[str, Any]) -> dict[RoborockZeoProtocol, Any]:
        """Set the sound package (DP 10003)."""
        dps = {RoborockZeoProtocol.SET_SOUND_PACKAGE: json.dumps(package)}
        return await self._send(dps)

    async def set_silent_mode(
        self,
        enabled: bool,
        start_time: datetime.time,
        end_time: datetime.time,
    ) -> dict[RoborockZeoProtocol, Any]:
        """Enable or disable silent mode with the given quiet hours.

        The three DPs (240/241/242) must be sent together.

        Requires the ``silent_mode`` feature bit; raises :class:`ValueError`
        if the device does not support it.
        """
        features = self._features()
        if features is not None and not features.silent_mode:
            raise ValueError("This device does not support silent mode")
        dps: dict[RoborockZeoProtocol, Any] = {
            RoborockZeoProtocol.SILENT_MODE_ON: 1 if enabled else 0,
            RoborockZeoProtocol.SILENT_MODE_START_TIME: start_time.hour * 60 + start_time.minute,
            RoborockZeoProtocol.SILENT_MODE_END_TIME: end_time.hour * 60 + end_time.minute,
        }
        return await self._send(dps)

    # -- Plain boolean switch setters ---------------------------------------
    #
    # These map one-to-one onto a boolean DP. Unlike the start-parameter
    # setters above, they are *not* carried by the START command, so they are
    # genuine runtime toggles. Each is feature-gated where the device has a
    # corresponding feature bit (or series whitelist); gated setters raise
    # :class:`ValueError` when the device does not support the feature.

    async def _set_bool(self, dp: RoborockZeoProtocol, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Send a boolean DP as its integer ``1``/``0`` (confirmed wire format)."""
        return await self._send({dp: 1 if enabled else 0})

    async def set_child_lock(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the child lock (DP 206)."""
        return await self._set_bool(RoborockZeoProtocol.CHILD_LOCK, enabled)

    async def set_sound(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the audible beeper (DP 223)."""
        return await self._set_bool(RoborockZeoProtocol.SOUND_SET, enabled)

    async def set_dirt_detection(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable dirt detection (DP 215).

        Requires the ``dirt_detection`` feature bit.
        """
        features = self._features()
        if features is not None and not features.dirt_detection:
            raise ValueError("This device does not support dirt detection")
        return await self._set_bool(RoborockZeoProtocol.DIRT_DETECTION_SWITCH, enabled)

    async def set_default_setting(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Set the default setting (DP 225)."""
        return await self._set_bool(RoborockZeoProtocol.DEFAULT_SETTING, enabled)

    async def set_uv_light(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the UV light (DP 228).

        Requires UV-light support for the device series.
        """
        if not supports_uv_light(self._model):
            raise ValueError("This device does not support UV light")
        return await self._set_bool(RoborockZeoProtocol.UV_LIGHT, enabled)

    async def set_smart_hosting(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable smart hosting (DP 235).

        Requires the ``smart_hosting`` feature bit.
        """
        features = self._features()
        if features is not None and not features.smart_hosting:
            raise ValueError("This device does not support smart hosting")
        return await self._set_bool(RoborockZeoProtocol.SMART_HOSTING, enabled)

    async def set_smile_light(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the smile light (DP 247).

        Requires the ``smile_light`` feature bit.
        """
        features = self._features()
        if features is not None and not features.smile_light:
            raise ValueError("This device does not support smile light")
        return await self._set_bool(RoborockZeoProtocol.SMILE_LIGHT_STATUS, enabled)

    async def set_fluff_cleaned(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Mark the fluff filter as cleaned (DP 249).

        Requires the ``fluff_clean_notification`` feature bit.
        """
        features = self._features()
        if features is not None and not features.fluff_clean_notification:
            raise ValueError("This device does not support fluff cleaning")
        return await self._set_bool(RoborockZeoProtocol.FLUFF_CLEANED, enabled)

    async def set_power_light(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the power-button indicator light (DP 251).

        Requires the ``power_button_indicator_light`` feature bit.
        """
        features = self._features()
        if features is not None and not features.power_button_indicator_light:
            raise ValueError("This device does not support the power indicator light")
        return await self._set_bool(RoborockZeoProtocol.POWER_LIGHT, enabled)

    async def set_ion_deodorization(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable ion deodorization (DP 258). Test-only: carried by START.

        Requires the ``ion_deodorization`` feature bit.
        """
        features = self._features()
        if features is not None and not features.ion_deodorization:
            raise ValueError("This device does not support ion deodorization")
        return await self._set_bool(RoborockZeoProtocol.ION_DEODORIZATION, enabled)

    async def set_wash_dry_linked(self, enabled: bool) -> dict[RoborockZeoProtocol, Any]:
        """Enable/disable the wash-dry linkage (DP 255). Test-only: carried by START.

        Requires the ``wash_dry_linkage`` feature bit.
        """
        features = self._features()
        if features is not None and not features.wash_dry_linkage:
            raise ValueError("This device does not support wash-dry linkage")
        return await self._set_bool(RoborockZeoProtocol.WASH_DRY_LINKED, enabled)

    async def _send(
        self,
        dps: dict[RoborockZeoProtocol, Any],
        qos: MqttQos = MqttQos.AT_MOST_ONCE,
    ) -> dict[RoborockZeoProtocol, Any]:
        """Send already wire-formatted DPs over the device channel."""
        return await send_decoded_command(self._channel, dps, value_encoder=lambda x: x, qos=qos)

    async def save_cloud_program(self, params: ZeoStartParams) -> dict[RoborockZeoProtocol, Any]:
        """Save the current programme parameters as a cloud custom program.

        Sends Mode/Program (and the optional Soak/Temperature/Rinse/Spin/
        DryingMode/DryCareMode/DryingMethod/SteamVolume) followed by a trigger
        signal of integer ``1``: either ``SaveAdaptedCloudProgram``(254) when
        the ``adapted_custom_program`` feature is supported, or
        ``SaveCloudProgram``(221) otherwise.
        """
        dps = build_param_dps(params)
        features = self._features()
        if features is not None and features.adapted_custom_program:
            dps[RoborockZeoProtocol.SAVE_ADAPTED_CLOUD_PROGRAM] = 1
        else:
            dps[RoborockZeoProtocol.CUSTOM_PARAM_SAVE] = 1
        return await self._send(dps, MqttQos.AT_LEAST_ONCE)

    async def save_panel_program(self, params: ZeoStartParams) -> dict[RoborockZeoProtocol, Any]:
        """Save the current programme parameters as a panel program (DP 252).

        Same parameter set as :meth:`save_cloud_program`, but the trigger
        signal is ``PanelProgramParamsSet``(252) instead.
        """
        dps = build_param_dps(params)
        dps[RoborockZeoProtocol.PANEL_PROGRAM_PARAMS_SET] = 1
        return await self._send(dps, MqttQos.AT_LEAST_ONCE)

    async def load_cloud_program(self) -> dict[RoborockZeoProtocol, Any]:
        """Apply the currently saved cloud custom program (DP 222 = 1).

        This only sends the trigger signal ``CUSTOM_PARAM_GET``(222) with an
        integer ``1``. The device responds by pushing the current program's
        32-bit bitfield back on DP 222 (see ``ZeoCustomMode.from_raw``).
        """
        dps: dict[RoborockZeoProtocol, Any] = {RoborockZeoProtocol.CUSTOM_PARAM_GET: 1}
        return await self._send(dps, MqttQos.AT_LEAST_ONCE)

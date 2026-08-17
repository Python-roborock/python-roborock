"""Create traits for A01 devices.

This module provides the API implementations for A01 protocol devices, which include
Dyad (Wet/Dry Vacuums) and Zeo (Washing Machines).

Using A01 APIs
--------------
A01 devices expose a single API object that handles all device interactions. This API is
available on the device instance (typically via `device.a01_properties`).

The API provides these methods:
1.  **query_values(protocols)**: Fetches current state for specific data points.
    You must pass a list of protocol enums (e.g. `RoborockDyadDataProtocol` or
    `RoborockZeoProtocol`) to request specific data.
2.  **set_value(protocol, value)**: Sends a command to the device to change a setting
    or perform an action.
3.  **add_listener(callback)**: Subscribes to state the device pushes on its own (for
    example when its state changes), invoking the callback with decoded values.

Note that these APIs fetch data directly from the device upon request and do not
cache state internally.
"""

import json
import logging
from collections.abc import Callable
from datetime import time
from typing import Any

from roborock.data import DyadProductInfo, DyadSndState, HomeDataProduct, RoborockCategory
from roborock.data.dyad.dyad_code_mappings import (
    DyadBrushSpeed,
    DyadCleanMode,
    DyadError,
    DyadSelfCleanLevel,
    DyadSelfCleanMode,
    DyadSuction,
    DyadWarmLevel,
    DyadWaterLevel,
    RoborockDyadStateCode,
)
from roborock.data.zeo.zeo_code_mappings import (
    ZeoDetergentExpansionType,
    ZeoDetergentType,
    ZeoDirtDetectionStatus,
    ZeoDryAndCare,
    ZeoDryerStartError,
    ZeoDryingMethod,
    ZeoDryingMode,
    ZeoError,
    ZeoFeatureBits,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoak,
    ZeoSoftenerExpansionType,
    ZeoSoftenerType,
    ZeoSpin,
    ZeoState,
    ZeoSteamVolume,
    ZeoTemperature,
)
from roborock.data.zeo.zeo_containers import (
    ZeoCustomMode,
    ZeoDryerCustomMode,
)
from roborock.devices.rpc.a01_channel import send_decoded_command
from roborock.devices.traits import Trait
from roborock.devices.traits.a01.command import ZeoCommandTrait
from roborock.devices.traits.a01.device_feature import (
    ZeoFeatures,
    build_feature_dp_list,
    build_force_load_dp_list,
    is_dryer,
    supports_uv_light,
)
from roborock.devices.traits.a01.settings import ZeoSettingTrait
from roborock.devices.traits.a01.status import ZeoStatusTrait
from roborock.devices.traits.common import TraitUpdateListener
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import decode_rpc_response
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "DyadApi",
    "ZeoApi",
    "ZeoCommandTrait",
    "ZeoFeatures",
    "ZeoSettingTrait",
    "ZeoStatusTrait",
]


DYAD_PROTOCOL_ENTRIES: dict[RoborockDyadDataProtocol, Callable] = {
    RoborockDyadDataProtocol.STATUS: lambda val: RoborockDyadStateCode(val).name,
    RoborockDyadDataProtocol.SELF_CLEAN_MODE: lambda val: DyadSelfCleanMode(val).name,
    RoborockDyadDataProtocol.SELF_CLEAN_LEVEL: lambda val: DyadSelfCleanLevel(val).name,
    RoborockDyadDataProtocol.WARM_LEVEL: lambda val: DyadWarmLevel(val).name,
    RoborockDyadDataProtocol.CLEAN_MODE: lambda val: DyadCleanMode(val).name,
    RoborockDyadDataProtocol.SUCTION: lambda val: DyadSuction(val).name,
    RoborockDyadDataProtocol.WATER_LEVEL: lambda val: DyadWaterLevel(val).name,
    RoborockDyadDataProtocol.BRUSH_SPEED: lambda val: DyadBrushSpeed(val).name,
    RoborockDyadDataProtocol.POWER: lambda val: int(val),
    RoborockDyadDataProtocol.AUTO_DRY: lambda val: bool(val),
    RoborockDyadDataProtocol.MESH_LEFT: lambda val: int(360000 - val * 60),
    RoborockDyadDataProtocol.BRUSH_LEFT: lambda val: int(360000 - val * 60),
    RoborockDyadDataProtocol.ERROR: lambda val: DyadError(val).name,
    RoborockDyadDataProtocol.VOLUME_SET: lambda val: int(val),
    RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: lambda val: bool(val),
    RoborockDyadDataProtocol.AUTO_DRY_MODE: lambda val: bool(val),
    RoborockDyadDataProtocol.SILENT_DRY_DURATION: lambda val: int(val),  # in minutes
    RoborockDyadDataProtocol.SILENT_MODE: lambda val: bool(val),
    RoborockDyadDataProtocol.SILENT_MODE_START_TIME: lambda val: time(
        hour=int(val / 60), minute=val % 60
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.SILENT_MODE_END_TIME: lambda val: time(
        hour=int(val / 60), minute=val % 60
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.RECENT_RUN_TIME: lambda val: [
        int(v) for v in val.split(",")
    ],  # minutes of cleaning in past few days.
    RoborockDyadDataProtocol.TOTAL_RUN_TIME: lambda val: int(val),
    RoborockDyadDataProtocol.SND_STATE: lambda val: DyadSndState.from_dict(val),
    RoborockDyadDataProtocol.PRODUCT_INFO: lambda val: DyadProductInfo.from_dict(val),
}


def _try_json(val: Any) -> Any:
    """Return *val* parsed as JSON when it is a JSON string, else *val*."""
    if isinstance(val, str):
        try:
            return json.loads(val)
        except ValueError:
            _LOGGER.debug("Failed to parse JSON for value %r, returning as-is", val)
    return val


ZEO_PROTOCOL_ENTRIES: dict[RoborockZeoProtocol, Callable] = {
    # read-only
    RoborockZeoProtocol.STATE: lambda val: ZeoState(val).name,
    RoborockZeoProtocol.COUNTDOWN: lambda val: int(val),
    RoborockZeoProtocol.WASHING_LEFT: lambda val: int(val),
    RoborockZeoProtocol.ERROR: lambda val: ZeoError(val).name,
    RoborockZeoProtocol.TIMES_AFTER_CLEAN: lambda val: int(val),
    RoborockZeoProtocol.DETERGENT_EMPTY: lambda val: bool(val),
    RoborockZeoProtocol.SOFTENER_EMPTY: lambda val: bool(val),
    RoborockZeoProtocol.DIRT_DETECTION_STATUS: lambda val: ZeoDirtDetectionStatus(val).name,
    RoborockZeoProtocol.TOTAL_TIME: lambda val: int(val),
    RoborockZeoProtocol.FEATURE_BITS: lambda val: int(val),
    RoborockZeoProtocol.SMART_HOSTING_WAITED_TIME: lambda val: int(val),
    RoborockZeoProtocol.IS_NEED_FLUFF_CLEAN: lambda val: bool(val),
    RoborockZeoProtocol.PANEL_PROGRAM_PARAMS_SET_RESULT: lambda val: int(val),
    RoborockZeoProtocol.DEVICE_BOUND: lambda val: bool(val),
    RoborockZeoProtocol.CLOTH_PUT_IN: lambda val: bool(val),
    RoborockZeoProtocol.CLOTH_READY_TO_DRY_COUNT_DOWN: lambda val: int(val),
    RoborockZeoProtocol.START_DRYER_ERROR: lambda val: ZeoDryerStartError(val).name,
    RoborockZeoProtocol.DOORLOCK_STATE: lambda val: bool(val),
    RoborockZeoProtocol.APP_AUTHORIZATION: lambda val: bool(val),
    RoborockZeoProtocol.SMART_HOSTING_TIME: lambda val: int(val),
    RoborockZeoProtocol.CUSTOM_PROGRAM_CLEANING_TIME: lambda val: int(val),
    RoborockZeoProtocol.PANEL_TIMING_PROGRAM_PARAMS: lambda val: int(val),
    RoborockZeoProtocol.STEAM_CARE_TIME: lambda val: int(val),
    # meta — read-only (JSON)
    RoborockZeoProtocol.PRODUCT_INFO: lambda val: _try_json(val),
    RoborockZeoProtocol.WASHING_LOG: lambda val: _try_json(val),
    RoborockZeoProtocol.SOUND_PACKAGE_INFO: lambda val: _try_json(val),
    RoborockZeoProtocol.VOICE_RECORD_INFO: lambda val: _try_json(val),
    RoborockZeoProtocol.VOICE_RECORD: lambda val: _try_json(val),
    # read-write
    RoborockZeoProtocol.MODE: lambda val: ZeoMode(val).name,
    RoborockZeoProtocol.PROGRAM: lambda val: ZeoProgram(val).name,
    RoborockZeoProtocol.TEMP: lambda val: ZeoTemperature(val).name,
    RoborockZeoProtocol.RINSE_TIMES: lambda val: ZeoRinse(val).name,
    RoborockZeoProtocol.SPIN_LEVEL: lambda val: ZeoSpin(val).name,
    RoborockZeoProtocol.DRYING_MODE: lambda val: ZeoDryingMode(val).name,
    RoborockZeoProtocol.DETERGENT_TYPE: lambda val: ZeoDetergentType(val).name,
    RoborockZeoProtocol.SOFTENER_TYPE: lambda val: ZeoSoftenerType(val).name,
    RoborockZeoProtocol.SOUND_SET: lambda val: bool(val),
    RoborockZeoProtocol.DIRT_DETECTION_SWITCH: lambda val: bool(val),
    RoborockZeoProtocol.SOAK: lambda val: ZeoSoak(val).name,
    RoborockZeoProtocol.SILENT_MODE_ON: lambda val: bool(val),
    RoborockZeoProtocol.SILENT_MODE_START_TIME: lambda val: int(val),
    RoborockZeoProtocol.SILENT_MODE_END_TIME: lambda val: int(val),
    RoborockZeoProtocol.DRY_CARE_MODE: lambda val: ZeoDryAndCare(val).name,
    RoborockZeoProtocol.WASH_DRY_LINKED: lambda val: bool(val),
    RoborockZeoProtocol.DRYING_METHOD: lambda val: ZeoDryingMethod(val).name,
    RoborockZeoProtocol.STEAM_VOLUME: lambda val: ZeoSteamVolume(val).name,
    RoborockZeoProtocol.ION_DEODORIZATION: lambda val: bool(val),
    RoborockZeoProtocol.UV_LIGHT: lambda val: bool(val),
    RoborockZeoProtocol.SMART_HOSTING: lambda val: bool(val),
    RoborockZeoProtocol.SOFTENER_EXPANSION_TYPE: lambda val: ZeoSoftenerExpansionType(val).name,
    RoborockZeoProtocol.DETERGENT_EXPANSION_TYPE: lambda val: ZeoDetergentExpansionType(val).name,
    RoborockZeoProtocol.SMILE_LIGHT_STATUS: lambda val: bool(val),
    RoborockZeoProtocol.POWER_LIGHT: lambda val: bool(val),
    RoborockZeoProtocol.PANEL_PROGRAM_PARAMS_SET: lambda val: int(val),
    RoborockZeoProtocol.WIFI_LINKAGE_RESET: lambda val: int(val),
    RoborockZeoProtocol.SAVE_ADAPTED_CLOUD_PROGRAM: lambda val: int(val),
    RoborockZeoProtocol.CHILD_LOCK: lambda val: bool(val),
    RoborockZeoProtocol.DETERGENT_SET: lambda val: bool(val),
    RoborockZeoProtocol.SOFTENER_SET: lambda val: bool(val),
    RoborockZeoProtocol.FLUFF_CLEANED: lambda val: bool(val),
    # read-write (JSON objects — bundle reads via JSON.parse)
    RoborockZeoProtocol.VOICE_VOLUME: lambda val: _try_json(val),  # {"snd_volume": int}
    RoborockZeoProtocol.VOICE_SWITCH: lambda val: _try_json(val),  # {"speech_switch": 1/0}
    # read-write (int-valued)
    RoborockZeoProtocol.CUSTOM_PARAM_SAVE: lambda val: int(val),
    RoborockZeoProtocol.CUSTOM_PARAM_GET: lambda val: int(val),
    RoborockZeoProtocol.DEFAULT_SETTING: lambda val: bool(val),
    # NOTE: LIGHT_SETTING(229) / DETERGENT_VOLUME(230) / SOFTENER_VOLUME(231)
    # are "server schema only" and do NOT exist in the device bundle — they
    # have no device-side implementation, so no converters are registered.
}


def convert_dyad_value(protocol_value: RoborockDyadDataProtocol, value: Any) -> Any:
    """Convert a dyad protocol value to its corresponding type."""
    if (converter := DYAD_PROTOCOL_ENTRIES.get(protocol_value)) is not None:
        try:
            return converter(value)
        except (ValueError, TypeError):
            return None
    return None


def convert_zeo_value(protocol_value: RoborockZeoProtocol, value: Any) -> Any:
    """Convert a zeo protocol value to its corresponding type."""
    if (converter := ZEO_PROTOCOL_ENTRIES.get(protocol_value)) is not None:
        try:
            return converter(value)
        except (ValueError, TypeError):
            return None
    return None


_DYAD_PROTOCOL_VALUES = frozenset(protocol.value for protocol in RoborockDyadDataProtocol)


class DyadApi(Trait):
    """API for interacting with Dyad devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Dyad API."""
        self._channel = channel

    async def query_values(self, protocols: list[RoborockDyadDataProtocol]) -> dict[RoborockDyadDataProtocol, Any]:
        """Query the device for the values of the given Dyad protocols."""
        response = await send_decoded_command(
            self._channel,
            {RoborockDyadDataProtocol.ID_QUERY: protocols},
            value_encoder=json.dumps,
        )
        return {protocol: convert_dyad_value(protocol, response.get(protocol)) for protocol in protocols}

    async def set_value(self, protocol: RoborockDyadDataProtocol, value: Any) -> dict[RoborockDyadDataProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)

    async def add_listener(self, callback: Callable[[dict[RoborockDyadDataProtocol, Any]], None]) -> Callable[[], None]:
        """Listen for state the device pushes on its own.

        The callback is invoked with decoded values whenever the device sends a
        message, including unsolicited pushes when its state changes. Only known
        protocols are delivered. Returns a callable to remove the listener.
        """

        def on_message(message: RoborockMessage) -> None:
            try:
                datapoints = decode_rpc_response(message)
            except RoborockException:
                return
            values: dict[RoborockDyadDataProtocol, Any] = {}
            for code, value in datapoints.items():
                if code not in _DYAD_PROTOCOL_VALUES:
                    continue
                protocol = RoborockDyadDataProtocol(code)
                values[protocol] = convert_dyad_value(protocol, value)
            if values:
                callback(values)

        return await self._channel.subscribe(on_message)


class ZeoApi(Trait, TraitUpdateListener):
    """API for interacting with Zeo devices."""

    def __init__(self, channel: MqttChannel, model: str | None = None) -> None:
        """Initialize the Zeo API."""
        TraitUpdateListener.__init__(self, _LOGGER)
        self._channel = channel
        self._dps_cache: dict[int, Any] = {}
        self._dps_unsub: Callable[[], None] | None = None
        self._feature_bits: int = 0
        self._features: ZeoFeatures | None = None
        self._model = model
        self._command: ZeoCommandTrait | None = None
        self._settings: ZeoSettingTrait | None = None
        self._status: ZeoStatusTrait | None = None

    @property
    def features(self) -> ZeoFeatures | None:
        """The device capabilities parsed from FEATURE_BITS (DP 237).

        ``None`` until the first force-load completes.
        """
        return self._features

    @property
    def command(self) -> ZeoCommandTrait:
        """Lazily-built trait for wash-programme commands."""
        if self._command is None:
            self._command = ZeoCommandTrait(
                channel=self._channel,
                settings=lambda: self.settings,
                features=lambda: self._features,
                custom_mode=lambda: self.get_custom_mode(),
            )
        return self._command

    @property
    def settings(self) -> ZeoSettingTrait:
        """Lazily-built typed writable-state/setter trait.

        Holds typed writable state (``mode``, ``temperature``,
        ``drying_method``, ...) refreshed from the device push stream, plus
        typed setters (``set_temperature(ZeoTemperature)``, ...). Fields that
        the device family does not support (e.g. ``temperature`` on a dryer)
        remain ``None``.
        """
        if self._settings is None:
            self._settings = ZeoSettingTrait(
                self._channel,
                model=self._model,
                is_dryer=is_dryer(self._model),
                features=lambda: self._features,
            )
        return self._settings

    @property
    def status(self) -> ZeoStatusTrait:
        """Lazily-built typed read-only state trait.

        Holds device-reported read-only state (``state``, ``error``,
        ``washing_left``, ``countdown``, tank levels, ...) refreshed from the
        MQTT push stream. No setters — this is status only.
        """
        if self._status is None:
            self._status = ZeoStatusTrait()
        return self._status

    def _update_settings_from_dps(self, decoded_dps: dict[int, Any]) -> None:
        """Route raw DPS data to the settings/status traits, if built.

        Writable DPs go to :class:`ZeoSettingTrait`; read-only DPs go to
        :class:`ZeoStatusTrait`. Both are lazily built, so pushes received
        before they exist are re-processed on first access via the raw cache.
        """
        if self._settings is not None:
            self._settings.update_from_dps(decoded_dps)
        if self._status is not None:
            self._status.update_from_dps(decoded_dps)

    async def start(self) -> None:
        """Subscribe to MQTT push and trigger a full state sync.

        Subscribes to the DPS MQTT topic, then performs a two-stage
        force-load: first the base DP list (including FEATURE_BITS),
        then a second query for the DPs gated behind each enabled feature.
        The device responds with a complete state dump;
        subsequent changes arrive via incremental MQTT push.
        """
        await self._ensure_subscribed()
        await self._force_load()
        await self._load_feature_dps()

    def close(self) -> None:
        """Unsubscribe from MQTT push and release resources."""
        if self._dps_unsub is not None:
            self._dps_unsub()
            self._dps_unsub = None

    async def _ensure_subscribed(self) -> None:
        """Subscribe to MQTT DPS push (idempotent)."""
        if self._dps_unsub is not None:
            return
        self._dps_unsub = await self._channel.subscribe(self._on_dps_message)

    async def _force_load(self) -> None:
        """Send ID_QUERY with the base DP list to trigger a full state push.

        For devices known to lack FEATURE_BITS, the DP is excluded
        from the query list and ``_feature_bits`` stays at 0.
        """
        dp_list = build_force_load_dp_list(self._model)
        result = await self.query_values(dp_list)
        self._feature_bits = result.get(RoborockZeoProtocol.FEATURE_BITS, 0)
        self._features = ZeoFeatures.from_feature_bits(self._feature_bits)

    async def _load_feature_dps(self) -> None:
        """Second-stage query for feature-gated DPs.

        Called unconditionally after the first force-load; each DP is
        independently gated:

        - Feature-gated DPs are queried only when their feature bit is set
          in FEATURE_BITS (DP 237).
        - UV light (DP 228) is gated by :func:`supports_uv_light` (series
          whitelist), independent of the feature bits.
        """
        feature_dps: list[RoborockZeoProtocol] = []
        if self._feature_bits:
            feature_dps.extend(build_feature_dp_list(self._feature_bits))
        if supports_uv_light(self._model):
            feature_dps.append(RoborockZeoProtocol.UV_LIGHT)
        if not feature_dps:
            return
        try:
            await self.query_values(feature_dps)
        except RoborockException as exc:
            _LOGGER.warning("Feature DPS load failed (non-fatal): %s", exc)

    def _on_dps_message(self, message: RoborockMessage) -> None:
        """Handle unsolicited MQTT push (protocol 102 — RPC_RESPONSE)."""
        if message.protocol != RoborockMessageProtocol.RPC_RESPONSE:
            return
        try:
            decoded = decode_rpc_response(message)
        except RoborockException:
            _LOGGER.debug("Dropped malformed push message", exc_info=True)
            return
        self._dps_cache.update(decoded)
        self._update_settings_from_dps(decoded)
        self._notify_update()

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """Query the device for the values of the given protocols."""
        response = await send_decoded_command(
            self._channel,
            {RoborockZeoProtocol.ID_QUERY: protocols},
            value_encoder=json.dumps,
        )
        for protocol in protocols:
            if (raw := response.get(protocol)) is not None:
                self._dps_cache[int(protocol)] = raw
        return {protocol: convert_zeo_value(protocol, response.get(protocol)) for protocol in protocols}

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params, value_encoder=lambda x: x)

    async def get_custom_mode(self) -> ZeoCustomMode | ZeoDryerCustomMode | None:
        """Query and decode the current custom programme (DP 222)."""
        await self.query_values([RoborockZeoProtocol.CUSTOM_PARAM_GET, RoborockZeoProtocol.TOTAL_TIME])
        raw = self._dps_cache.get(int(RoborockZeoProtocol.CUSTOM_PARAM_GET))
        if raw is None:
            return None
        total_time = self._dps_cache.get(int(RoborockZeoProtocol.TOTAL_TIME))
        try:
            raw_int = int(raw)
        except (TypeError, ValueError):
            return None
        if is_dryer(self._model):
            return ZeoDryerCustomMode.from_raw(raw_int, total_time)
        return ZeoCustomMode.from_raw(raw_int, total_time)

    async def update_sound_package_info(self) -> Any:
        """Query the sound-package info (DP 10004)."""
        result = await self.query_values([RoborockZeoProtocol.SOUND_PACKAGE_INFO])
        return result.get(RoborockZeoProtocol.SOUND_PACKAGE_INFO)


def create(product: HomeDataProduct, mqtt_channel: MqttChannel) -> DyadApi | ZeoApi:
    """Create traits for A01 devices."""
    match product.category:
        case RoborockCategory.WET_DRY_VAC:
            return DyadApi(mqtt_channel)
        case RoborockCategory.WASHING_MACHINE:
            return ZeoApi(mqtt_channel, model=product.model)
        case _:
            raise NotImplementedError(f"Unsupported category {product.category}")

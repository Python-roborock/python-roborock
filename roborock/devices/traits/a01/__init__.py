"""Create traits for A01 devices.

This module provides the API implementations for A01 protocol devices, which include
Dyad (Wet/Dry Vacuums) and Zeo (Washing Machines).

Using A01 APIs
--------------
A01 devices expose a single API object that handles all device interactions. This API is
available on the device instance (`device.dyad` or `device.zeo`).

The API provides these methods:
1.  **query_values(protocols)**: Fetches current state for specific data points.
    You must pass a list of protocol enums (e.g. `RoborockDyadDataProtocol` or
    `RoborockZeoProtocol`) to request specific data.
2.  **set_value(protocol, value)**: Sends a command to the device to change a setting
    or perform an action.
3.  **values**: The latest known state, merged from query responses and unsolicited
    pushes in arrival order.
4.  **add_update_listener(callback)**: Registers a callback invoked whenever `values`
    changes; read `values` from the callback to get the updated state.

The device pushes only the data points that changed, so `values` is the merged view
of everything seen so far. State tracking is active once the device is connected
(the device calls `start()` on the API, which subscribes to the MQTT topic).
"""

import json
import logging
from abc import abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime, time
from typing import Any, Generic, TypeVar

from roborock.data import DyadProductInfo, DyadScheduleTask, DyadSndState, HomeDataProduct, RoborockCategory
from roborock.data.dyad.dyad_code_mappings import (
    DyadBrushSpeed,
    DyadCleanAssistPower,
    DyadCleanMode,
    DyadCleanserAmount,
    DyadDryingMode,
    DyadError,
    DyadFeatureBits,
    DyadFlatStatus,
    DyadPowerwheelDirection,
    DyadSelfCleanIntensity,
    DyadSelfCleanLevel,
    DyadSelfCleanMode,
    DyadSelfCleanWaterTemp,
    DyadSuction,
    DyadWarmLevel,
    DyadWaterLevel,
    RoborockDyadStateCode,
)
from roborock.data.zeo.zeo_code_mappings import (
    ZeoDetergentType,
    ZeoDryingMode,
    ZeoError,
    ZeoFeatureBits,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoftenerType,
    ZeoSpin,
    ZeoState,
    ZeoTemperature,
)
from roborock.devices.rpc.a01_channel import send_decoded_command
from roborock.devices.traits import Trait
from roborock.devices.traits.a01 import dyad_feature
from roborock.devices.traits.a01.device_feature import (
    build_feature_dp_list,
    build_force_load_dp_list,
    supports_uv_light,
)
from roborock.devices.traits.common import TraitUpdateListener
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.protocols.a01_protocol import decode_rpc_response
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "A01Api",
    "DyadApi",
    "ZeoApi",
]


def _decode_dyad_schedule(value: str) -> list[DyadScheduleTask]:
    """Decode the schedule data point, which is a JSON list or an empty string."""
    if not value:
        return []
    return [DyadScheduleTask.from_dict(task) for task in json.loads(value)]


# The app pairs each suction level (eco, standard, turbo) with a brush speed.
_PAIRED_SUCTION_BRUSH_SPEED = {
    DyadSuction.l2: DyadBrushSpeed.l1,
    DyadSuction.l3: DyadBrushSpeed.l2,
    DyadSuction.l4: DyadBrushSpeed.l2,
}
_WATER_LEVELS = (DyadWaterLevel.l2, DyadWaterLevel.l3, DyadWaterLevel.l4)
_DRYING_MODES = (DyadDryingMode.fast, DyadDryingMode.silent)
_SELF_CLEAN_INTENSITIES = (DyadSelfCleanIntensity.smart, DyadSelfCleanIntensity.standard, DyadSelfCleanIntensity.deep)

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
    RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET: lambda val: bool(val),  # self-clean after docking
    RoborockDyadDataProtocol.AUTO_DRY: lambda val: bool(val),
    RoborockDyadDataProtocol.MESH_LEFT: lambda val: int(360000 - val * 60),
    RoborockDyadDataProtocol.BRUSH_LEFT: lambda val: int(360000 - val * 60),
    RoborockDyadDataProtocol.ERROR: lambda val: DyadError(val).name,
    RoborockDyadDataProtocol.VOLUME_SET: lambda val: int(val),
    RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: lambda val: bool(val),
    RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET_MODE: lambda val: DyadSelfCleanLevel(val).name,
    RoborockDyadDataProtocol.AUTO_DRY_MODE: lambda val: bool(val),
    RoborockDyadDataProtocol.SILENT_DRY_DURATION: lambda val: int(val),  # minutes, or a DyadDryingMode code
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
    RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT: lambda val: DyadCleanserAmount(val).name,
    RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET: lambda val: bool(val),
    RoborockDyadDataProtocol.LIGHT_SET: lambda val: bool(val),
    RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET: lambda val: DyadCleanAssistPower(val).name,
    RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET: lambda val: DyadSelfCleanWaterTemp(val).name,
    RoborockDyadDataProtocol.DOCK_TYPE: lambda val: int(val),
    RoborockDyadDataProtocol.WATER_MODE_SUCTION: lambda val: DyadSuction(val).name,
    RoborockDyadDataProtocol.WATER_MODE_BRUSH_SPEED: lambda val: DyadBrushSpeed(val).name,
    RoborockDyadDataProtocol.CHARGE_ERROR_STATUS: lambda val: bool(val),
    RoborockDyadDataProtocol.DRYING_RATE: lambda val: int(val),  # percent
    RoborockDyadDataProtocol.FLAT_STATUS: lambda val: DyadFlatStatus(val).name,
    RoborockDyadDataProtocol.POWERWHEEL_DIRECTION: lambda val: DyadPowerwheelDirection(val).name,
    RoborockDyadDataProtocol.POWERWHEEL_SPEED: lambda val: int(val),
    RoborockDyadDataProtocol.FEATURE_INFO: lambda val: int(val),
    RoborockDyadDataProtocol.SELF_CLEAN_PROGRESS: lambda val: int(val),  # percent
    RoborockDyadDataProtocol.SPRAY_MODE: lambda val: int(val),
    RoborockDyadDataProtocol.MECHANICAL_ARM: lambda val: bool(val),
    RoborockDyadDataProtocol.TRIGGER_MODE: lambda val: int(val),
    RoborockDyadDataProtocol.SELF_CLEAN_REMINDER: lambda val: int(val),
    RoborockDyadDataProtocol.BATTERY_THRESHOLD: lambda val: int(val),
    RoborockDyadDataProtocol.SELF_CLEAN_CUR_MODE: lambda val: DyadSelfCleanIntensity(val).name,
    RoborockDyadDataProtocol.SELF_CLEAN_CUR_TEMP: lambda val: DyadSelfCleanWaterTemp(val).name,
    RoborockDyadDataProtocol.DRY_CUR_MODE: lambda val: DyadDryingMode(val).name,
    RoborockDyadDataProtocol.SCHEDULE_TASK: _decode_dyad_schedule,
    RoborockDyadDataProtocol.SND_STATE: lambda val: DyadSndState.from_dict(val),
    RoborockDyadDataProtocol.PRODUCT_INFO: lambda val: DyadProductInfo.from_dict(val),
}

ZEO_PROTOCOL_ENTRIES: dict[RoborockZeoProtocol, Callable] = {
    # read-only
    RoborockZeoProtocol.STATE: lambda val: ZeoState(val).name,
    RoborockZeoProtocol.COUNTDOWN: lambda val: int(val),
    RoborockZeoProtocol.WASHING_LEFT: lambda val: int(val),
    RoborockZeoProtocol.ERROR: lambda val: ZeoError(val).name,
    RoborockZeoProtocol.TIMES_AFTER_CLEAN: lambda val: int(val),
    RoborockZeoProtocol.DETERGENT_EMPTY: lambda val: bool(val),
    RoborockZeoProtocol.SOFTENER_EMPTY: lambda val: bool(val),
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
    RoborockZeoProtocol.FEATURE_BITS: lambda val: int(val),
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
_ZEO_PROTOCOL_VALUES = frozenset(protocol.value for protocol in RoborockZeoProtocol)

_P = TypeVar("_P", RoborockDyadDataProtocol, RoborockZeoProtocol)


class A01Api(Trait, TraitUpdateListener, Generic[_P]):
    """Base class for A01 device APIs with device state tracking.

    Query responses and unsolicited pushes both arrive on the same MQTT topic,
    so a single subscription merges every decoded message into `values` in
    arrival order. Update listeners are notified whenever a value changes.
    """

    def __init__(self, channel: MqttChannel, initial_status: dict[int, Any] | None = None) -> None:
        """Initialize the A01 API, optionally seeding `values` from a cloud status snapshot."""
        TraitUpdateListener.__init__(self, _LOGGER)
        self._channel = channel
        self._values: dict[_P, Any] = {}
        self._unsub: Callable[[], None] | None = None
        self._last_message_time: datetime | None = None
        if initial_status:
            self._merge_values(self._decode_datapoints(initial_status))

    @property
    def values(self) -> dict[_P, Any]:
        """Latest known device state, merged from query responses and pushes.

        The device pushes only the data points that changed, so this is the
        merged view of everything seen so far. A protocol the device has not
        reported yet is absent from the dictionary.
        """
        return dict(self._values)

    @property
    def last_message_time(self) -> datetime | None:
        """Time the last message was received from the device.

        Updated on every decoded message, even when no value changed: idle
        devices push an identical heartbeat, so this is the liveness signal
        even when `values` stays the same and update listeners stay silent.
        The initial cloud status snapshot does not count as a message.
        """
        return self._last_message_time

    async def start(self) -> None:
        """Subscribe to the device state topic and start tracking `values`."""
        await self._ensure_subscribed()

    def close(self) -> None:
        """Unsubscribe from MQTT push and release resources."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _ensure_subscribed(self) -> None:
        """Subscribe to MQTT DPS push (idempotent)."""
        if self._unsub is not None:
            return
        self._unsub = await self._channel.subscribe(self._on_message)

    @abstractmethod
    def _decode_datapoints(self, datapoints: dict[int, Any]) -> dict[_P, Any]:
        """Convert raw datapoints to typed values, skipping unknown codes."""

    def _on_message(self, message: RoborockMessage) -> None:
        """Handle a message on the device topic (query response or push)."""
        if message.protocol != RoborockMessageProtocol.RPC_RESPONSE:
            return
        try:
            datapoints = decode_rpc_response(message)
        except RoborockException:
            _LOGGER.debug("Dropped malformed push message", exc_info=True)
            return
        self._last_message_time = datetime.now(UTC)
        self._merge_values(self._decode_datapoints(datapoints))

    def _merge_query_response(self, values: dict[_P, Any]) -> None:
        """Record a successful query response when there is no subscription.

        When subscribed, the response was already merged in arrival order and
        timestamped by `_on_message`; merging again here could overwrite a
        push that arrived after it.
        """
        if self._unsub is not None:
            return
        self._last_message_time = datetime.now(UTC)
        self._merge_values(values)

    def _merge_values(self, values: dict[_P, Any]) -> None:
        """Merge decoded values into the cache and notify on change."""
        changed = False
        for protocol, value in values.items():
            if value is None:
                continue
            if protocol not in self._values or self._values[protocol] != value:
                self._values[protocol] = value
                changed = True
        if changed:
            self._notify_update()


class DyadApi(A01Api[RoborockDyadDataProtocol]):
    """API for interacting with Dyad devices."""

    name = "dyad"

    def __init__(
        self, channel: MqttChannel, model: str | None = None, initial_status: dict[int, Any] | None = None
    ) -> None:
        """Initialize the Dyad API."""
        self._model = model
        super().__init__(channel, initial_status)

    def _require_support(self, is_supported: Callable[[str | None], bool]) -> None:
        """Raise if the device model does not support a command."""
        if not is_supported(self._model):
            raise RoborockUnsupportedFeature(f"Command is not supported on model {self._model}")

    def supports(self, feature: DyadFeatureBits) -> bool:
        """Return whether the device reported a feature bit on `FEATURE_INFO`.

        The result is False until the device has reported `FEATURE_INFO`.
        """
        if feature == DyadFeatureBits.unknown:
            return False
        return bool(self._values.get(RoborockDyadDataProtocol.FEATURE_INFO, 0) & (1 << feature.value))

    def _decode_datapoints(self, datapoints: dict[int, Any]) -> dict[RoborockDyadDataProtocol, Any]:
        """Convert raw datapoints to typed values, skipping unknown codes."""
        values: dict[RoborockDyadDataProtocol, Any] = {}
        for code, value in datapoints.items():
            if code not in _DYAD_PROTOCOL_VALUES:
                continue
            protocol = RoborockDyadDataProtocol(code)
            values[protocol] = convert_dyad_value(protocol, value)
        return values

    async def query_values(self, protocols: list[RoborockDyadDataProtocol]) -> dict[RoborockDyadDataProtocol, Any]:
        """Query the device for the values of the given Dyad protocols."""
        response = await send_decoded_command(
            self._channel,
            {RoborockDyadDataProtocol.ID_QUERY: protocols},
            value_encoder=json.dumps,
        )
        values = {protocol: convert_dyad_value(protocol, response.get(protocol)) for protocol in protocols}
        self._merge_query_response(values)
        return values

    async def set_value(self, protocol: RoborockDyadDataProtocol, value: Any) -> dict[RoborockDyadDataProtocol, Any]:
        """Set a value for a specific protocol on the device.

        The value is sent as is and is not checked against the model. Prefer the
        dedicated methods, which accept only what the app offers for the model.
        """
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)

    async def set_clean_mode(self, mode: DyadCleanMode) -> None:
        """Set the clean mode, limited to the modes the app offers for the model."""
        if mode not in dyad_feature.clean_modes(self._model):
            raise RoborockUnsupportedFeature(f"Clean mode {mode!r} is not supported on model {self._model}")
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.CLEAN_MODE: int(mode)})

    async def set_water_level(self, level: DyadWaterLevel) -> None:
        """Set the auto mode water level.

        Supports `l2`, `l3` and `l4` on models where the app offers these levels.
        """
        self._require_support(dyad_feature.supports_clean_intensity)
        if level not in _WATER_LEVELS:
            raise ValueError(f"Unsupported water level: {level!r}")
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.WATER_LEVEL: int(level)})

    async def start_drying(self) -> None:
        """Start drying with the drying mode currently set on the device.

        The app sends the same command for fast and silent drying.
        """
        await send_decoded_command(
            self._channel,
            {RoborockDyadDataProtocol.START: 1, RoborockDyadDataProtocol.WARM_LEVEL: 1},
        )

    async def stop(self) -> None:
        """Stop a running drying or self-clean cycle.

        The device has one stop command for both cycles.
        """
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.START: 0})

    async def set_drying_mode(self, mode: DyadDryingMode) -> None:
        """Set the drying mode on models that have one, such as the F25 series.

        Other models raise `RoborockUnsupportedFeature`: there the same data point is
        the silent drying duration in minutes. The device reports the selected mode on
        `DRY_CUR_MODE`.
        """
        self._require_support(dyad_feature.supports_drying_mode)
        if mode not in _DRYING_MODES:
            raise ValueError(f"Unsupported drying mode: {mode!r}")
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.SILENT_DRY_DURATION: int(mode)})

    async def set_self_clean_intensity(self, intensity: DyadSelfCleanIntensity) -> None:
        """Set the self-clean intensity.

        The setting spans several data points, and smart differs from standard only in
        `AUTO_SMART_SELF_CLEAN_SET`. Models without smart self-clean raise
        `RoborockUnsupportedFeature` for `smart`. `SELF_CLEAN_CUR_MODE` reports the
        current or last run, not this setting.
        """
        self._require_support(dyad_feature.is_known_model)
        if intensity not in _SELF_CLEAN_INTENSITIES:
            raise ValueError(f"Unsupported self-clean intensity: {intensity!r}")
        has_smart = dyad_feature.supports_smart_self_clean(self._model)
        if intensity == DyadSelfCleanIntensity.smart and not has_smart:
            raise RoborockUnsupportedFeature(f"Smart self-clean is not supported on model {self._model}")
        level = DyadSelfCleanLevel.deep if intensity == DyadSelfCleanIntensity.deep else DyadSelfCleanLevel.normal
        params = {
            RoborockDyadDataProtocol.SELF_CLEAN_LEVEL: int(level),
            RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET_MODE: int(level),
        }
        if has_smart:
            params[RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET] = int(intensity == DyadSelfCleanIntensity.smart)
        await send_decoded_command(self._channel, params)

    async def set_suction(self, suction: DyadSuction) -> None:
        """Set the auto mode suction on models that pair it with a brush speed.

        Supports `l2` (eco), `l3` (standard) and `l4` (turbo). The device does not
        change the brush speed by itself, so it is sent along with the suction.
        """
        await self._set_paired_suction(
            RoborockDyadDataProtocol.SUCTION,
            RoborockDyadDataProtocol.BRUSH_SPEED,
            suction,
        )

    async def set_sponge_suction(self, suction: DyadSuction) -> None:
        """Set the sponge mode suction on models that pair it with a brush speed.

        Supports `l2` (eco), `l3` (standard) and `l4` (turbo). The device does not
        change the brush speed by itself, so it is sent along with the suction.
        """
        await self._set_paired_suction(
            RoborockDyadDataProtocol.WATER_MODE_SUCTION,
            RoborockDyadDataProtocol.WATER_MODE_BRUSH_SPEED,
            suction,
        )

    async def _set_paired_suction(
        self,
        suction_protocol: RoborockDyadDataProtocol,
        brush_protocol: RoborockDyadDataProtocol,
        suction: DyadSuction,
    ) -> None:
        """Send a suction level with the brush speed the app pairs with it."""
        self._require_support(dyad_feature.supports_clean_intensity)
        if (brush_speed := _PAIRED_SUCTION_BRUSH_SPEED.get(suction)) is None:
            raise ValueError(f"Unsupported suction level: {suction!r}")
        await send_decoded_command(
            self._channel,
            {suction_protocol: int(suction), brush_protocol: int(brush_speed)},
        )

    async def start_self_clean(self) -> None:
        """Start self-clean with the settings currently set on the device.

        The app includes the current `SELF_CLEAN_LEVEL` in the start command, so it
        is read from the device first. After changing the intensity, wait until the
        device reports the new value before calling this.
        """
        response = await send_decoded_command(
            self._channel,
            {RoborockDyadDataProtocol.ID_QUERY: [RoborockDyadDataProtocol.SELF_CLEAN_LEVEL]},
            value_encoder=json.dumps,
        )
        await send_decoded_command(
            self._channel,
            {
                RoborockDyadDataProtocol.START: 1,
                RoborockDyadDataProtocol.SELF_CLEAN_LEVEL: response[RoborockDyadDataProtocol.SELF_CLEAN_LEVEL],
            },
        )

    async def pause_self_clean(self) -> None:
        """Pause a running self-clean cycle."""
        self._require_support(dyad_feature.supports_self_clean_pause)
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.START: 2})

    async def resume_self_clean(self) -> None:
        """Resume a paused self-clean cycle."""
        self._require_support(dyad_feature.supports_self_clean_pause)
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.START: 1})

    async def reset_filter(self) -> None:
        """Reset the filter usage counter."""
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.MESH_RESET: 1})

    async def reset_brush(self) -> None:
        """Reset the brush roller usage counter."""
        await send_decoded_command(self._channel, {RoborockDyadDataProtocol.BRUSH_RESET: 1})

    async def add_listener(self, callback: Callable[[dict[RoborockDyadDataProtocol, Any]], None]) -> Callable[[], None]:
        """Listen for state the device pushes on its own.

        The callback is invoked with decoded values whenever the device sends a
        message, including unsolicited pushes when its state changes. Only known
        protocols are delivered. Returns a callable to remove the listener.

        Prefer `add_update_listener` together with `values`, which handle the
        merging of partial pushes for you.
        """

        def on_message(message: RoborockMessage) -> None:
            try:
                datapoints = decode_rpc_response(message)
            except RoborockException:
                return
            if values := self._decode_datapoints(datapoints):
                callback(values)

        return await self._channel.subscribe(on_message)


class ZeoApi(A01Api[RoborockZeoProtocol]):
    """API for interacting with Zeo devices."""

    name = "zeo"

    def __init__(
        self, channel: MqttChannel, model: str | None = None, initial_status: dict[int, Any] | None = None
    ) -> None:
        """Initialize the Zeo API."""
        self._feature_bits: int = 0
        self._model = model
        super().__init__(channel, initial_status)

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

    def _decode_datapoints(self, datapoints: dict[int, Any]) -> dict[RoborockZeoProtocol, Any]:
        """Convert raw datapoints to typed values, skipping unknown codes."""
        values: dict[RoborockZeoProtocol, Any] = {}
        for code, value in datapoints.items():
            if code not in _ZEO_PROTOCOL_VALUES:
                continue
            protocol = RoborockZeoProtocol(code)
            values[protocol] = convert_zeo_value(protocol, value)
        return values

    async def _force_load(self) -> None:
        """Send ID_QUERY with the base DP list to trigger a full state push.

        For devices known to lack FEATURE_BITS, the DP is excluded
        from the query list and ``_feature_bits`` stays at 0.
        """
        dp_list = build_force_load_dp_list(self._model)
        result = await self.query_values(dp_list)
        self._feature_bits = result.get(RoborockZeoProtocol.FEATURE_BITS, 0)

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

    def supports(self, feature: ZeoFeatureBits) -> bool:
        """Check whether the device supports a given feature bit."""
        return bool(self._feature_bits & (1 << feature.value))

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """Query the device for the values of the given protocols."""
        response = await send_decoded_command(
            self._channel,
            {RoborockZeoProtocol.ID_QUERY: protocols},
            value_encoder=json.dumps,
        )
        values = {protocol: convert_zeo_value(protocol, response.get(protocol)) for protocol in protocols}
        self._merge_query_response(values)
        return values

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params, value_encoder=lambda x: x)


def _parse_device_status(device_status: dict | None) -> dict[int, Any] | None:
    """Normalize the cloud home data status snapshot to integer datapoint codes."""
    if not device_status:
        return None
    try:
        return {int(code): value for code, value in device_status.items()}
    except (TypeError, ValueError):
        _LOGGER.debug("Ignoring malformed device status snapshot: %s", device_status)
        return None


def create(product: HomeDataProduct, mqtt_channel: MqttChannel, device_status: dict | None = None) -> DyadApi | ZeoApi:
    """Create traits for A01 devices.

    The optional `device_status` is the cloud home data status snapshot, used
    to seed `values` so state is available before the first device round trip.
    """
    initial_status = _parse_device_status(device_status)
    match product.category:
        case RoborockCategory.WET_DRY_VAC:
            return DyadApi(mqtt_channel, model=product.model, initial_status=initial_status)
        case RoborockCategory.WASHING_MACHINE:
            return ZeoApi(mqtt_channel, model=product.model, initial_status=initial_status)
        case _:
            raise NotImplementedError(f"Unsupported category {product.category}")

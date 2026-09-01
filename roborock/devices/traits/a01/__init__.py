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
from roborock.devices.traits.a01.device_feature import (
    build_feature_dp_list,
    build_force_load_dp_list,
    supports_uv_light,
)
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
    "A01Api",
    "DyadApi",
    "ZeoApi",
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
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)

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
            return DyadApi(mqtt_channel, initial_status=initial_status)
        case RoborockCategory.WASHING_MACHINE:
            return ZeoApi(mqtt_channel, model=product.model, initial_status=initial_status)
        case _:
            raise NotImplementedError(f"Unsupported category {product.category}")

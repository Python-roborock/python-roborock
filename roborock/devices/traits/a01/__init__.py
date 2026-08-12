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
from roborock.devices.traits.common import TraitUpdateListener
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException, RoborockTimeout
from roborock.protocols.a01_protocol import decode_rpc_response
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)

__init__ = [
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

# Devices known to lack FEATURE_BITS (DP 237).
_UNSUPPORTED_FEATURE_BITS: frozenset[str] = frozenset(
    {
        "roborock.wm.a63",  # H1
        "roborock.wm.a90",  # H1 Lite
    }
)

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

    name = "zeo"

    def __init__(self, channel: MqttChannel, product_id: str | None = None) -> None:
        """Initialize the Zeo API."""
        TraitUpdateListener.__init__(self, _LOGGER)
        self._channel = channel
        self._dps_cache: dict[int, Any] = {}
        self._dps_unsub: Callable[[], None] | None = None
        self._feature_bits: int = 0
        self._product_id = product_id

    async def start(self) -> None:
        """Subscribe to MQTT push and discover device features.

        Subscribes to the DPS MQTT topic, then queries FEATURE_BITS
        (DP 237) to wake the device and cache supported capabilities.
        """
        await self._ensure_subscribed()
        await self._discover_features()

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

    async def _discover_features(self) -> None:
        """Query FEATURE_BITS to wake the device and cache capabilities.

        Only devices that support the FeatureBits DP will respond;
        For devices known to lack this DP
        the query is skipped entirely; for all other devices a
        timeout propagates as a connection error.
        """
        if self._product_id in _UNSUPPORTED_FEATURE_BITS:
            return
        try:
            result = await self.query_values([RoborockZeoProtocol.FEATURE_BITS])
            self._feature_bits = result.get(RoborockZeoProtocol.FEATURE_BITS, 0)
        except RoborockTimeout:
            self._feature_bits = 0

    def supports(self, feature: ZeoFeatureBits) -> bool:
        """Check whether the device supports a given feature bit."""
        return bool(self._feature_bits & (1 << feature.value))

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
        self._notify_update()

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """Query the device for the values of the given protocols."""
        response = await send_decoded_command(
            self._channel,
            {RoborockZeoProtocol.ID_QUERY: protocols},
            value_encoder=json.dumps,
        )
        return {protocol: convert_zeo_value(protocol, response.get(protocol)) for protocol in protocols}

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params, value_encoder=lambda x: x)


def create(product: HomeDataProduct, mqtt_channel: MqttChannel) -> DyadApi | ZeoApi:
    """Create traits for A01 devices."""
    match product.category:
        case RoborockCategory.WET_DRY_VAC:
            return DyadApi(mqtt_channel)
        case RoborockCategory.WASHING_MACHINE:
            return ZeoApi(mqtt_channel, product_id=product.id)
        case _:
            raise NotImplementedError(f"Unsupported category {product.category}")

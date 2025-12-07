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
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSoftenerType,
    ZeoSpin,
    ZeoState,
    ZeoTemperature,
)
from roborock.devices.a01_channel import send_decoded_command
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol

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


def convert_dyad_value(protocol: int, value: Any) -> Any:
    """Convert a dyad protocol value to its corresponding type."""
    protocol_value = RoborockDyadDataProtocol(protocol)
    if (converter := DYAD_PROTOCOL_ENTRIES.get(protocol_value)) is not None:
        return converter(value)
    return None


def convert_zeo_value(protocol: int, value: Any) -> Any:
    """Convert a zeo protocol value to its corresponding type."""
    protocol_value = RoborockZeoProtocol(protocol)
    if (converter := ZEO_PROTOCOL_ENTRIES.get(protocol_value)) is not None:
        return converter(value)
    return None


class DyadApi(Trait):
    """API for interacting with Dyad devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Dyad API."""
        self._channel = channel

    async def query_values(self, protocols: list[RoborockDyadDataProtocol]) -> dict[RoborockDyadDataProtocol, Any]:
        """Query the device for the values of the given Dyad protocols."""
        params = {RoborockDyadDataProtocol.ID_QUERY: str([int(p) for p in protocols])}
        response = await send_decoded_command(self._channel, params)
        return {
            RoborockDyadDataProtocol(int(k)): v
            for k, val in response.items()
            if (v := convert_dyad_value(int(k), val)) is not None
        }

    async def set_value(self, protocol: RoborockDyadDataProtocol, value: Any) -> dict[RoborockDyadDataProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)


class ZeoApi(Trait):
    """API for interacting with Zeo devices."""

    name = "zeo"

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Zeo API."""
        self._channel = channel

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """Query the device for the values of the given protocols."""
        params = {RoborockZeoProtocol.ID_QUERY: str([int(p) for p in protocols])}
        response = await send_decoded_command(self._channel, params)
        return {
            RoborockZeoProtocol(int(k)): v
            for k, val in response.items()
            if (v := convert_zeo_value(int(k), val)) is not None
        }

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)


def create(product: HomeDataProduct, mqtt_channel: MqttChannel) -> DyadApi | ZeoApi:
    """Create traits for A01 devices."""
    match product.category:
        case RoborockCategory.WET_DRY_VAC:
            return DyadApi(mqtt_channel)
        case RoborockCategory.WASHING_MACHINE:
            return ZeoApi(mqtt_channel)
        case _:
            raise NotImplementedError(f"Unsupported category {product.category}")

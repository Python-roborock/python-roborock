import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import time
from typing import Any

from roborock import DeviceData
from roborock.api import RoborockClient
from roborock.code_mappings import (
    DyadBrushSpeed,
    DyadCleanMode,
    DyadError,
    DyadSelfCleanLevel,
    DyadSelfCleanMode,
    DyadSuction,
    DyadWarmLevel,
    DyadWaterLevel,
    RoborockDyadStateCode,
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
from roborock.containers import DyadProductInfo, DyadSndState, RoborockCategory
from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import decode_rpc_response
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)


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
    # ro
    RoborockZeoProtocol.STATE: lambda val: ZeoState(val).name,
    RoborockZeoProtocol.COUNTDOWN: lambda val: int(val),
    RoborockZeoProtocol.WASHING_LEFT: lambda val: int(val),
    RoborockZeoProtocol.ERROR: lambda val: ZeoError(val).name,
    RoborockZeoProtocol.TIMES_AFTER_CLEAN: lambda val: int(val),
    RoborockZeoProtocol.DETERGENT_EMPTY: lambda val: bool(val),
    RoborockZeoProtocol.SOFTENER_EMPTY: lambda val: bool(val),
    # rw
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


class RoborockClientA01(RoborockClient, ABC):
    """Roborock client base class for A01 devices."""

    value_converter: Callable[[int, Any], Any] | None = None

    def __init__(self, device_info: DeviceData, category: RoborockCategory):
        """Initialize the Roborock client."""
        super().__init__(device_info)
        if category == RoborockCategory.WET_DRY_VAC:
            self.value_converter = convert_dyad_value
        elif category == RoborockCategory.WASHING_MACHINE:
            self.value_converter = convert_zeo_value
        else:
            _LOGGER.debug("Device category %s is not (yet) supported", category)
            self.value_converter = None

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        if self.value_converter is None:
            return
        for message in messages:
            protocol = message.protocol
            if message.payload and protocol in [
                RoborockMessageProtocol.RPC_RESPONSE,
                RoborockMessageProtocol.GENERAL_REQUEST,
            ]:
                try:
                    data_points = decode_rpc_response(message)
                except RoborockException as err:
                    self._logger.debug("Failed to decode message: %s", err)
                    continue
                for data_point_number, data_point in data_points.items():
                    self._logger.debug("received msg with dps, protocol: %s, %s", data_point_number, protocol)
                    if converted_response := self.value_converter(data_point_number, data_point):
                        queue = self._waiting_queue.get(int(data_point_number))
                        if queue and queue.protocol == protocol:
                            queue.set_result(converted_response)
                    else:
                        self._logger.debug(
                            "Received unknown data point %s for protocol %s, ignoring", data_point_number, protocol
                        )

    @abstractmethod
    async def update_values(
        self, dyad_data_protocols: list[RoborockDyadDataProtocol | RoborockZeoProtocol]
    ) -> dict[RoborockDyadDataProtocol | RoborockZeoProtocol, Any]:
        """This should handle updating for each given protocol."""

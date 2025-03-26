import dataclasses
import json
import logging
import typing
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

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
from roborock.roborock_future import RequestKey
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class A01ProtocolCacheEntry:
    post_process_fn: Callable
    value: typing.Any | None = None


# Right now this cache is not active, it was too much complexity for the initial addition of dyad.
protocol_entries = {
    RoborockDyadDataProtocol.STATUS: A01ProtocolCacheEntry(lambda val: RoborockDyadStateCode(val).name),
    RoborockDyadDataProtocol.SELF_CLEAN_MODE: A01ProtocolCacheEntry(lambda val: DyadSelfCleanMode(val).name),
    RoborockDyadDataProtocol.SELF_CLEAN_LEVEL: A01ProtocolCacheEntry(lambda val: DyadSelfCleanLevel(val).name),
    RoborockDyadDataProtocol.WARM_LEVEL: A01ProtocolCacheEntry(lambda val: DyadWarmLevel(val).name),
    RoborockDyadDataProtocol.CLEAN_MODE: A01ProtocolCacheEntry(lambda val: DyadCleanMode(val).name),
    RoborockDyadDataProtocol.SUCTION: A01ProtocolCacheEntry(lambda val: DyadSuction(val).name),
    RoborockDyadDataProtocol.WATER_LEVEL: A01ProtocolCacheEntry(lambda val: DyadWaterLevel(val).name),
    RoborockDyadDataProtocol.BRUSH_SPEED: A01ProtocolCacheEntry(lambda val: DyadBrushSpeed(val).name),
    RoborockDyadDataProtocol.POWER: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.AUTO_DRY: A01ProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.MESH_LEFT: A01ProtocolCacheEntry(lambda val: int(360000 - val * 60)),
    RoborockDyadDataProtocol.BRUSH_LEFT: A01ProtocolCacheEntry(lambda val: int(360000 - val * 60)),
    RoborockDyadDataProtocol.ERROR: A01ProtocolCacheEntry(lambda val: DyadError(val).name),
    RoborockDyadDataProtocol.VOLUME_SET: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: A01ProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.AUTO_DRY_MODE: A01ProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.SILENT_DRY_DURATION: A01ProtocolCacheEntry(lambda val: int(val)),  # in minutes
    RoborockDyadDataProtocol.SILENT_MODE: A01ProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.SILENT_MODE_START_TIME: A01ProtocolCacheEntry(
        lambda val: time(hour=int(val / 60), minute=val % 60)
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.SILENT_MODE_END_TIME: A01ProtocolCacheEntry(
        lambda val: time(hour=int(val / 60), minute=val % 60)
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.RECENT_RUN_TIME: A01ProtocolCacheEntry(
        lambda val: [int(v) for v in val.split(",")]
    ),  # minutes of cleaning in past few days.
    RoborockDyadDataProtocol.TOTAL_RUN_TIME: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.SND_STATE: A01ProtocolCacheEntry(lambda val: DyadSndState.from_dict(val)),
    RoborockDyadDataProtocol.PRODUCT_INFO: A01ProtocolCacheEntry(lambda val: DyadProductInfo.from_dict(val)),
}

zeo_data_protocol_entries = {
    # ro
    RoborockZeoProtocol.STATE: A01ProtocolCacheEntry(lambda val: ZeoState(val).name),
    RoborockZeoProtocol.COUNTDOWN: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockZeoProtocol.WASHING_LEFT: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockZeoProtocol.ERROR: A01ProtocolCacheEntry(lambda val: ZeoError(val).name),
    RoborockZeoProtocol.TIMES_AFTER_CLEAN: A01ProtocolCacheEntry(lambda val: int(val)),
    RoborockZeoProtocol.DETERGENT_EMPTY: A01ProtocolCacheEntry(lambda val: bool(val)),
    RoborockZeoProtocol.SOFTENER_EMPTY: A01ProtocolCacheEntry(lambda val: bool(val)),
    # rw
    RoborockZeoProtocol.MODE: A01ProtocolCacheEntry(lambda val: ZeoMode(val).name),
    RoborockZeoProtocol.PROGRAM: A01ProtocolCacheEntry(lambda val: ZeoProgram(val).name),
    RoborockZeoProtocol.TEMP: A01ProtocolCacheEntry(lambda val: ZeoTemperature(val).name),
    RoborockZeoProtocol.RINSE_TIMES: A01ProtocolCacheEntry(lambda val: ZeoRinse(val).name),
    RoborockZeoProtocol.SPIN_LEVEL: A01ProtocolCacheEntry(lambda val: ZeoSpin(val).name),
    RoborockZeoProtocol.DRYING_MODE: A01ProtocolCacheEntry(lambda val: ZeoDryingMode(val).name),
    RoborockZeoProtocol.DETERGENT_TYPE: A01ProtocolCacheEntry(lambda val: ZeoDetergentType(val).name),
    RoborockZeoProtocol.SOFTENER_TYPE: A01ProtocolCacheEntry(lambda val: ZeoSoftenerType(val).name),
    RoborockZeoProtocol.SOUND_SET: A01ProtocolCacheEntry(lambda val: bool(val)),
}


class RoborockClientA01(RoborockClient, ABC):
    """Roborock client base class for A01 devices."""

    def __init__(self, device_info: DeviceData, category: RoborockCategory):
        """Initialize the Roborock client."""
        super().__init__(device_info)
        self.category = category

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        for message in messages:
            protocol = message.protocol
            if message.payload and protocol in [
                RoborockMessageProtocol.RPC_RESPONSE,
                RoborockMessageProtocol.GENERAL_REQUEST,
            ]:
                payload = message.payload
                try:
                    payload = unpad(payload, AES.block_size)
                except Exception as err:
                    self._logger.debug("Failed to unpad payload: %s", err)
                    continue
                payload_json = json.loads(payload.decode())
                for data_point_number, data_point in payload_json.get("dps").items():
                    data_point_protocol: RoborockDyadDataProtocol | RoborockZeoProtocol
                    self._logger.debug("received msg with dps, protocol: %s, %s", data_point_number, protocol)
                    entries: dict
                    if self.category == RoborockCategory.WET_DRY_VAC:
                        data_point_protocol = RoborockDyadDataProtocol(int(data_point_number))
                        entries = protocol_entries
                    elif self.category == RoborockCategory.WASHING_MACHINE:
                        data_point_protocol = RoborockZeoProtocol(int(data_point_number))
                        entries = zeo_data_protocol_entries
                    else:
                        continue
                    if data_point_protocol in entries:
                        # Auto convert into data struct we want.
                        converted_response = entries[data_point_protocol].post_process_fn(data_point)
                        request_key = RequestKey(int(data_point_number), protocol)
                        if future := self._waiting_queue.safe_pop(request_key, "a01"):
                            future.set_result(converted_response)

    @abstractmethod
    async def update_values(
        self, dyad_data_protocols: list[RoborockDyadDataProtocol | RoborockZeoProtocol]
    ) -> dict[RoborockDyadDataProtocol | RoborockZeoProtocol, typing.Any]:
        """This should handle updating for each given protocol."""

"""Stateful simulator for Roborock A01 (Dyad and Zeo) devices."""

import copy
from dataclasses import replace
import enum
import json
import logging
from typing import Any

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.data.dyad.dyad_code_mappings import (
    DyadCleanMode,
    DyadError,
    DyadSuction,
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
from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import (
    A01_VERSION,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockZeoProtocol,
)
from roborock.testing.simulator import DEFAULT_LOCAL_KEY, RoborockDeviceSimulator

_LOGGER = logging.getLogger(__name__)

DEFAULT_DYAD_PRODUCT_ID = "product-id-dyad"
DEFAULT_ZEO_PRODUCT_ID = "product-id-zeo"

DEFAULT_DYAD_PRODUCT = HomeDataProduct(
    id=DEFAULT_DYAD_PRODUCT_ID,
    name="Roborock Dyad",
    model="roborock.wetdryvac.a01",
    category=RoborockCategory.WET_DRY_VAC,
)

DEFAULT_DYAD_DEVICE_INFO = HomeDataDevice(
    duid="fake_dyad_duid",
    name="Roborock Dyad",
    local_key=DEFAULT_LOCAL_KEY,
    product_id=DEFAULT_DYAD_PRODUCT_ID,
    sn="fake_dyad_sn",
    pv="A01",
)

DEFAULT_ZEO_PRODUCT = HomeDataProduct(
    id=DEFAULT_ZEO_PRODUCT_ID,
    name="Roborock Zeo One",
    model="roborock.washer.a01",
    category=RoborockCategory.WASHING_MACHINE,
)

DEFAULT_ZEO_DEVICE_INFO = HomeDataDevice(
    duid="fake_zeo_duid",
    name="Roborock Zeo One",
    local_key=DEFAULT_LOCAL_KEY,
    product_id=DEFAULT_ZEO_PRODUCT_ID,
    sn="fake_zeo_sn",
    pv="A01",
)

# Dyad protocol default values
DEFAULT_DYAD_STATUS: dict[int, Any] = {
    int(RoborockDyadDataProtocol.STATUS): RoborockDyadStateCode.charging.value,
    int(RoborockDyadDataProtocol.POWER): 100,
    int(RoborockDyadDataProtocol.SUCTION): DyadSuction.l1.value,
    int(RoborockDyadDataProtocol.WATER_LEVEL): DyadWaterLevel.l1.value,
    int(RoborockDyadDataProtocol.CLEAN_MODE): DyadCleanMode.auto.value,
    int(RoborockDyadDataProtocol.AUTO_DRY): 1,
    int(RoborockDyadDataProtocol.VOLUME_SET): 80,
    int(RoborockDyadDataProtocol.ERROR): DyadError.none.value,
    int(RoborockDyadDataProtocol.TOTAL_RUN_TIME): 120,
    int(RoborockDyadDataProtocol.SILENT_MODE): 0,
}

# Zeo protocol default values
DEFAULT_ZEO_STATUS: dict[int, Any] = {
    int(RoborockZeoProtocol.STATE): ZeoState.standby.value,
    int(RoborockZeoProtocol.MODE): ZeoMode.wash_and_dry.value,
    int(RoborockZeoProtocol.PROGRAM): ZeoProgram.standard.value,
    int(RoborockZeoProtocol.TEMP): ZeoTemperature.medium.value,
    int(RoborockZeoProtocol.RINSE_TIMES): ZeoRinse.low.value,
    int(RoborockZeoProtocol.SPIN_LEVEL): ZeoSpin.high.value,
    int(RoborockZeoProtocol.DRYING_MODE): ZeoDryingMode.store.value,
    int(RoborockZeoProtocol.DETERGENT_EMPTY): False,
    int(RoborockZeoProtocol.SOFTENER_EMPTY): False,
    int(RoborockZeoProtocol.SOUND_SET): True,
    int(RoborockZeoProtocol.ERROR): ZeoError.none.value,
    int(RoborockZeoProtocol.WASHING_LEFT): 0,
    int(RoborockZeoProtocol.COUNTDOWN): 0,
    int(RoborockZeoProtocol.TIMES_AFTER_CLEAN): 0,
    int(RoborockZeoProtocol.DETERGENT_TYPE): ZeoDetergentType.low.value,
    int(RoborockZeoProtocol.SOFTENER_TYPE): ZeoSoftenerType.low.value,
}


def _extract_int_value(val: Any) -> Any:
    """Helper to extract raw value from Enum members or return primitive values directly."""
    if isinstance(val, enum.Enum):
        return val.value
    return val


class A01DeviceSimulator(RoborockDeviceSimulator):
    """Base stateful firmware simulator for Roborock A01 devices."""

    def __init__(
        self,
        duid: str,
        device_info: HomeDataDevice,
        product: HomeDataProduct,
        status: dict[int | enum.Enum, Any] | None = None,
    ):
        super().__init__(duid, device_info, product, has_local_channel=False)
        raw_status = status or {}
        self.status: dict[int, Any] = {
            int(_extract_int_value(k)): _extract_int_value(v) for k, v in raw_status.items()
        }

    def set_protocol_value(self, protocol: Any, value: Any, push: bool = False) -> None:
        """Set a protocol value in the simulator status.

        Accepts protocol enums (e.g. RoborockDyadDataProtocol, RoborockZeoProtocol)
        or raw integer IDs, and value enums or raw primitive values.
        """
        protocol_key = int(_extract_int_value(protocol))
        raw_value = _extract_int_value(value)
        self.status[protocol_key] = raw_value

        if push:
            self.push_dps({protocol_key: raw_value})

    async def _handle_publish(self, message: RoborockMessage, channel: Any) -> None:
        """Process incoming A01 encrypted payload and respond."""
        if not message.payload:
            return

        try:
            decoded_dps = decode_rpc_response(message)
        except RoborockException as ex:
            _LOGGER.warning("Simulator failed to decode A01 payload: %s", ex)
            return

        updated_dps: dict[int, Any] = {}

        # Check for query (ID_QUERY key = 10000)
        id_query_key = 10000
        if query_raw := decoded_dps.get(id_query_key):
            query_list: list[Any] = []
            if isinstance(query_raw, str):
                try:
                    parsed = json.loads(query_raw)
                    if isinstance(parsed, list):
                        query_list = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(query_raw, list):
                query_list = query_raw

            for key_val in query_list:
                key_int = int(_extract_int_value(key_val))
                if key_int in self.status:
                    updated_dps[key_int] = self.status[key_int]

            if updated_dps:
                self.push_dps(updated_dps)
            return

        # Direct setters: update internal state for received DPS
        for code, val in decoded_dps.items():
            if code != id_query_key:
                self.status[code] = val
                updated_dps[code] = val

        if updated_dps:
            self.push_dps(updated_dps)

    def push_dps(self, dps_updates: dict[int, Any]) -> None:
        """Push encrypted A01 status datapoint updates to subscribers."""
        msg = encode_mqtt_payload(dps_updates)
        self.mqtt_channel.notify_subscribers(msg)

    def trigger_push_update(self) -> None:
        """Send the full status dump to subscribers."""
        self.push_dps(self.status)


class DyadSimulator(A01DeviceSimulator):
    """Stateful firmware simulator for Roborock Dyad (WET_DRY_VAC) A01 devices."""

    def __init__(
        self,
        duid: str = "fake_dyad_duid",
        status: dict[int | enum.Enum, Any] | None = None,
        device_info: HomeDataDevice | None = None,
        product: HomeDataProduct | None = None,
    ):
        product = product or DEFAULT_DYAD_PRODUCT
        if device_info is None:
            device_info = replace(DEFAULT_DYAD_DEVICE_INFO, duid=duid, name=f"Dyad {duid}")
        merged_status = copy.deepcopy(DEFAULT_DYAD_STATUS)
        if status:
            for k, v in status.items():
                merged_status[int(_extract_int_value(k))] = _extract_int_value(v)

        super().__init__(duid, device_info, product, merged_status)

    def set_state(self, state: RoborockDyadStateCode | int, push: bool = False) -> None:
        """Set the Dyad state code."""
        self.set_protocol_value(RoborockDyadDataProtocol.STATUS, state, push=push)

    def set_suction(self, suction: DyadSuction | int, push: bool = False) -> None:
        """Set the Dyad suction level."""
        self.set_protocol_value(RoborockDyadDataProtocol.SUCTION, suction, push=push)

    def set_water_level(self, level: DyadWaterLevel | int, push: bool = False) -> None:
        """Set the Dyad water level."""
        self.set_protocol_value(RoborockDyadDataProtocol.WATER_LEVEL, level, push=push)

    def set_error(self, error: DyadError | int, push: bool = False) -> None:
        """Set the Dyad error code."""
        self.set_protocol_value(RoborockDyadDataProtocol.ERROR, error, push=push)

    def set_volume(self, volume: int, push: bool = False) -> None:
        """Set the Dyad speaker volume."""
        self.set_protocol_value(RoborockDyadDataProtocol.VOLUME_SET, volume, push=push)


class ZeoSimulator(A01DeviceSimulator):
    """Stateful firmware simulator for Roborock Zeo (WASHING_MACHINE) A01 devices."""

    def __init__(
        self,
        duid: str = "fake_zeo_duid",
        status: dict[int | enum.Enum, Any] | None = None,
        device_info: HomeDataDevice | None = None,
        product: HomeDataProduct | None = None,
    ):
        product = product or DEFAULT_ZEO_PRODUCT
        if device_info is None:
            device_info = replace(DEFAULT_ZEO_DEVICE_INFO, duid=duid, name=f"Zeo {duid}")
        merged_status = copy.deepcopy(DEFAULT_ZEO_STATUS)
        if status:
            for k, v in status.items():
                merged_status[int(_extract_int_value(k))] = _extract_int_value(v)

        super().__init__(duid, device_info, product, merged_status)

    def set_state(self, state: ZeoState | int, push: bool = False) -> None:
        """Set the Zeo washing state."""
        self.set_protocol_value(RoborockZeoProtocol.STATE, state, push=push)

    def set_mode(self, mode: ZeoMode | int, push: bool = False) -> None:
        """Set the Zeo wash mode."""
        self.set_protocol_value(RoborockZeoProtocol.MODE, mode, push=push)

    def set_program(self, program: ZeoProgram | int, push: bool = False) -> None:
        """Set the Zeo wash program."""
        self.set_protocol_value(RoborockZeoProtocol.PROGRAM, program, push=push)

    def set_temperature(self, temp: ZeoTemperature | int, push: bool = False) -> None:
        """Set the Zeo water temperature."""
        self.set_protocol_value(RoborockZeoProtocol.TEMP, temp, push=push)

    def set_error(self, error: ZeoError | int, push: bool = False) -> None:
        """Set the Zeo error code."""
        self.set_protocol_value(RoborockZeoProtocol.ERROR, error, push=push)

    def set_detergent_empty(self, empty: bool, push: bool = False) -> None:
        """Set detergent empty indicator."""
        self.set_protocol_value(RoborockZeoProtocol.DETERGENT_EMPTY, empty, push=push)

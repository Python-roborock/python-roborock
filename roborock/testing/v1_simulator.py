"""Stateful V1/L01 vacuum device firmware simulator.

This module provides `V1VacuumSimulator` which simulates the firmware state
machine and JSON RPC commands for V1 vacuum cleaners.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict
from enum import Enum
from typing import Any
from unittest.mock import Mock

from roborock.data import HomeDataDevice, HomeDataProduct
from roborock.data.v1 import RoborockStateCode
from roborock.data.v1.v1_code_mappings import (
    RoborockChargeStatus,
    RoborockCleanType,
    RoborockDockErrorCode,
    RoborockDockTypeCode,
    RoborockErrorCode,
    RoborockFinishReason,
    RoborockInCleaning,
    RoborockStartType,
)
from roborock.data.v1.v1_containers import (
    AppInitStatus,
    AppInitStatusLocalInfo,
    CleanRecord,
    CleanSummary,
    Consumable,
    DnDTimer,
    NetworkInfo,
    StatusV2,
)
from roborock.devices.cache import DeviceCache, InMemoryCache
from roborock.devices.rpc.v1_channel import V1Channel
from roborock.protocols.v1_protocol import SecurityData
from roborock.roborock_message import RoborockDataProtocol, RoborockMessage, RoborockMessageProtocol
from roborock.testing.channel import FakeChannel
from roborock.testing.simulator import RoborockDeviceSimulator

_LOGGER = logging.getLogger(__name__)


def _serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Helper to convert dataclass instances to dictionaries with serialized enums and filtered Nones."""
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in asdict(obj).items() if v is not None}


class V1VacuumSimulator(RoborockDeviceSimulator):
    """Firmware simulator for a V1/L01 vacuum device.

    This class holds the simulated physical hardware state (such as battery levels,
    cleaning state, fan speeds, and consumable wear). When it receives JSON RPC
    commands (like `app_start` or `get_consumable`), it updates these state variables
    and returns a response corresponding to the expected firmware behavior.

    Default command handlers are mapped in `self.default_handlers` and can be
    overridden during initialization by passing `custom_handlers`.
    """

    def __init__(
        self,
        duid: str = "fake_duid",
        battery: int = 100,
        state: int = RoborockStateCode.charging,
        fan_power: int = 102,  # balanced
        dnd_enabled: int = 0,
        mop_mode: int = 300,
        water_box_mode: int = 200,
        custom_handlers: dict[str, Callable[[list[Any]], Any]] | None = None,
        device_info: HomeDataDevice | None = None,
        product: HomeDataProduct | None = None,
        dss: int = 169,
        dock_type: int = 3,
    ):
        super().__init__(duid=duid, device_info=device_info, product=product)
        self.battery = battery
        self.state = state
        self.fan_power = fan_power
        self.dnd_enabled = dnd_enabled
        self.mop_mode = mop_mode
        self.water_box_mode = water_box_mode
        self.custom_handlers = custom_handlers or {}
        self.dss = dss
        self.dock_type = dock_type

        self.network_info = NetworkInfo(
            ip="1.1.1.1",
            ssid="test_wifi",
            mac="aa:bb:cc:dd:ee:ff",
            bssid="aa:bb:cc:dd:ee:ff",
            rssi=-50,
        )

        self.consumables = Consumable(
            main_brush_work_time=74382,
            side_brush_work_time=74383,
            filter_work_time=74384,
            filter_element_work_time=0,
            sensor_dirty_time=74385,
            strainer_work_times=65,
            dust_collection_work_times=25,
            cleaning_brush_work_times=66,
        )

        self.dnd_timer = DnDTimer(
            start_hour=22,
            start_minute=0,
            end_hour=7,
            end_minute=0,
            enabled=1,
        )

        self.clean_summary = CleanSummary(
            clean_time=74382,
            clean_area=1159182500,
            clean_count=31,
            dust_collection_count=25,
            records=[1672543330, 1672458041],
        )

        self.last_clean_record = CleanRecord(
            begin=1672543330,
            end=1672544638,
            duration=1176,
            area=20965000,
            error=0,
            complete=1,
            start_type=RoborockStartType.app,
            clean_type=RoborockCleanType.select_zone,
            finish_reason=RoborockFinishReason.finished_cleaning_4,
            dust_collection_status=1,
            avoid_count=19,
            wash_count=2,
            map_flag=0,
        )

        # Set up default handlers dictionary
        self.default_handlers: dict[str, Callable[[Any], Any]] = {
            "get_status": lambda params: [self.get_status_dict()],
            "get_consumable": lambda params: [_serialize_dataclass(self.consumables)],
            "get_dnd_timer": lambda params: _serialize_dataclass(self.dnd_timer),
            "get_clean_summary": lambda params: _serialize_dataclass(self.clean_summary),
            "get_clean_record": lambda params: _serialize_dataclass(self.last_clean_record),
            "app_start": self._handle_app_start,
            "app_stop": self._handle_app_stop,
            "app_charge": self._handle_app_charge,
            "set_custom_mode": self._handle_set_custom_mode,
            "set_mop_mode": self._handle_set_mop_mode,
            "set_water_box_custom_mode": self._handle_set_water_box_custom_mode,
            "reset_consumable": self._handle_reset_consumable,
            "app_get_init_status": self._handle_app_get_init_status,
            "get_network_info": self._handle_get_network_info,
        }

        self.device_cache = DeviceCache(self.duid, InMemoryCache())
        self.security_data = SecurityData(endpoint="fake_endpoint", nonce=b"fake_nonce_16bytes")
        local_session = Mock(return_value=self.local_channel)

        self._v1_channel = V1Channel(
            device_uid=self.duid,
            security_data=self.security_data,
            mqtt_channel=self.mqtt_channel,  # type: ignore[arg-type]
            local_session=local_session,
            device_cache=self.device_cache,
        )

    @property
    def v1_channel(self) -> V1Channel:
        """Returns the real V1Channel bound to the fake channels."""
        return self._v1_channel

    @property
    def in_cleaning(self) -> RoborockInCleaning:
        """Return global_clean_not_complete if cleaning, else complete."""
        return (
            RoborockInCleaning.global_clean_not_complete
            if self.state == RoborockStateCode.cleaning
            else RoborockInCleaning.complete
        )

    @property
    def in_returning(self) -> int:
        """Return 1 if returning, else 0."""
        return 1 if self.state == RoborockStateCode.returning_home else 0

    @property
    def charge_status(self) -> RoborockChargeStatus:
        """Return charging if charging, else charge_waiting."""
        return (
            RoborockChargeStatus.charging
            if self.state == RoborockStateCode.charging
            else RoborockChargeStatus.charge_waiting
        )

    def get_status_dict(self) -> dict[str, Any]:
        """Generate status dict using the current simulated state."""
        status = StatusV2(
            msg_ver=2,
            msg_seq=458,
            state=RoborockStateCode(self.state),
            battery=self.battery,
            clean_time=1176,
            clean_area=20965000,
            error_code=RoborockErrorCode(0),
            map_present=1,
            in_cleaning=self.in_cleaning,
            in_returning=self.in_returning,
            in_fresh_state=1,
            lab_status=1,
            water_box_status=1,
            back_type=-1,
            wash_phase=0,
            wash_ready=0,
            fan_power=self.fan_power,
            dnd_enabled=self.dnd_enabled,
            map_status=3,
            is_locating=0,
            lock_status=0,
            water_box_mode=self.water_box_mode,
            water_box_carriage_status=1,
            mop_forbidden_enable=1,
            camera_status=3457,
            is_exploring=0,
            home_sec_status=0,
            home_sec_enable_password=0,
            adbumper_status=[0, 0, 0],
            water_shortage_status=0,
            dock_type=RoborockDockTypeCode(self.dock_type),
            dust_collection_status=0,
            auto_dust_collection=1,
            avoid_count=19,
            mop_mode=self.mop_mode,
            debug_mode=0,
            collision_avoid_status=1,
            switch_map_mode=0,
            dock_error_status=RoborockDockErrorCode(0),
            charge_status=self.charge_status,
            unsave_map_reason=0,
            unsave_map_flag=0,
            dss=self.dss,
        )
        return _serialize_dataclass(status)

    def _handle_app_start(self, params: Any) -> str:
        self.state = RoborockStateCode.cleaning
        return "ok"

    def _handle_app_stop(self, params: Any) -> str:
        self.state = RoborockStateCode.paused
        return "ok"

    def _handle_app_charge(self, params: Any) -> str:
        self.state = RoborockStateCode.returning_home
        return "ok"

    def _handle_set_custom_mode(self, params: Any) -> str:
        if isinstance(params, list) and len(params) > 0:
            self.fan_power = params[0]
        elif isinstance(params, dict):
            self.fan_power = params.get("fan_power", self.fan_power)
        return "ok"

    def _handle_set_mop_mode(self, params: Any) -> str:
        if isinstance(params, list) and len(params) > 0:
            self.mop_mode = params[0]
        return "ok"

    def _handle_set_water_box_custom_mode(self, params: Any) -> str:
        if isinstance(params, list) and len(params) > 0:
            self.water_box_mode = params[0]
        return "ok"

    def _handle_reset_consumable(self, params: Any) -> str:
        if isinstance(params, list) and len(params) > 0:
            consumable_name = params[0]
            if hasattr(self.consumables, consumable_name):
                setattr(self.consumables, consumable_name, 0)
        return "ok"

    def _handle_app_get_init_status(self, params: Any) -> list[dict[str, Any]]:
        local_info = AppInitStatusLocalInfo(
            location="us",
            bom="A.03.0069",
            featureset=1,
            language="en",
            logserver="awsusor0.fds.api.xiaomi.com",
            wifiplan="0x39",
            timezone="US/Pacific",
            name="custom_A.03.0069_FCC",
        )
        app_init = AppInitStatus(
            local_info=local_info,
            feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125],
            new_feature_info=633887780925447,
            new_feature_info_str="0000000000002000",
            new_feature_info_2=8192,
        )
        payload = _serialize_dataclass(app_init)
        if "new_feature_info_2" in payload:
            payload["new_feature_info2"] = payload.pop("new_feature_info_2")

        payload["status_info"] = {
            "state": self.state,
            "battery": self.battery,
            "clean_time": 5610,
            "clean_area": 96490000,
            "error_code": 0,
            "in_cleaning": self.in_cleaning.value,
            "in_returning": self.in_returning,
            "in_fresh_state": 1,
            "lab_status": 1,
            "water_box_status": 0,
            "map_status": 3,
            "is_locating": 0,
            "lock_status": 0,
            "water_box_mode": self.water_box_mode,
            "distance_off": 0,
            "water_box_carriage_status": 0,
            "mop_forbidden_enable": 0,
        }
        return [payload]

    def _handle_get_network_info(self, params: Any) -> dict[str, Any]:
        return _serialize_dataclass(self.network_info)

    async def _handle_publish(self, message: RoborockMessage, channel: FakeChannel) -> None:
        if not message.payload:
            return

        try:
            payload = json.loads(message.payload.decode())
            dps = payload.get("dps", {})
            if "101" not in dps:
                return
            inner = json.loads(dps["101"])
            msg_id = inner["id"]
            method = inner["method"]
            params = inner.get("params", [])
        except Exception as e:
            _LOGGER.debug("Failed to parse plaintext JSON RPC payload: %s", e, exc_info=True)
            return

        result = None
        error = None

        # Check custom handlers override first, then fall back to default handlers
        handler = self.custom_handlers.get(method) or self.default_handlers.get(method)
        if handler:
            try:
                result = handler(params)
            except Exception as e:
                error = str(e)
                _LOGGER.debug("Error executing command handler for %s: %s", method, e, exc_info=True)
        else:
            result = "ok"

        response_data = {
            "dps": {"102": json.dumps({"id": msg_id, "result": result, "error": error})},
            "t": int(time.time()),
        }

        response_msg = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=json.dumps(response_data).encode(), seq=msg_id
        )

        channel.notify_subscribers(response_msg)

    def trigger_push_update(self) -> None:
        """Trigger an unsolicited push state update to all subscribers."""
        dps_payload = {
            str(int(RoborockDataProtocol.STATE)): self.state,
            str(int(RoborockDataProtocol.BATTERY)): self.battery,
            str(int(RoborockDataProtocol.FAN_POWER)): self.fan_power,
            str(int(RoborockDataProtocol.WATER_BOX_MODE)): self.water_box_mode,
        }

        payload = {"dps": dps_payload, "t": int(time.time())}

        push_msg = RoborockMessage(
            protocol=RoborockMessageProtocol.GENERAL_RESPONSE, payload=json.dumps(payload).encode()
        )

        self.mqtt_channel.notify_subscribers(push_msg)
        if self.local_channel is not None:
            self.local_channel.notify_subscribers(push_msg)

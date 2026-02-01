"""Status trait for Q10 B01 devices."""

from __future__ import annotations

from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXDeviceCleanTask,
    YXDeviceState,
    YXDeviceWorkMode,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.devices.rpc.b01_q10_channel import send_decoded_command
from roborock.devices.transport.mqtt_channel import MqttChannel


class StatusTrait:
    """Trait for requesting and holding Q10 status values."""

    def __init__(self, channel: MqttChannel) -> None:
        self._channel = channel
        self._data: dict[B01_Q10_DP, Any] = {}

    @property
    def data(self) -> dict[B01_Q10_DP, Any]:
        """Return the latest raw status data."""
        return self._data

    async def refresh(self) -> dict[B01_Q10_DP, Any]:
        """Refresh status values from the device."""
        decoded = await send_decoded_command(
            self._channel,
            command=B01_Q10_DP.REQUETDPS,
            params={},
            expected_dps={B01_Q10_DP.STATUS, B01_Q10_DP.BATTERY},
        )
        self._data = decoded
        return decoded

    @property
    def state_code(self) -> int | None:
        return self._data.get(B01_Q10_DP.STATUS)

    @property
    def state(self) -> YXDeviceState | None:
        code = self.state_code
        return YXDeviceState.from_code_optional(code) if code is not None else None

    @property
    def battery(self) -> int | None:
        return self._data.get(B01_Q10_DP.BATTERY)

    @property
    def fan_level(self) -> YXFanLevel | None:
        value = self._data.get(B01_Q10_DP.FUN_LEVEL)
        return YXFanLevel.from_code_optional(value) if value is not None else None

    @property
    def water_level(self) -> YXWaterLevel | None:
        value = self._data.get(B01_Q10_DP.WATER_LEVEL)
        return YXWaterLevel.from_code_optional(value) if value is not None else None

    @property
    def clean_mode(self) -> YXDeviceWorkMode | None:
        value = self._data.get(B01_Q10_DP.CLEAN_MODE)
        return YXDeviceWorkMode.from_code_optional(value) if value is not None else None

    @property
    def clean_task(self) -> YXDeviceCleanTask | None:
        value = self._data.get(B01_Q10_DP.CLEAN_TASK_TYPE)
        return YXDeviceCleanTask.from_code_optional(value) if value is not None else None

    @property
    def cleaning_progress(self) -> int | None:
        return self._data.get(B01_Q10_DP.CLEANING_PROGRESS)

"""Traits for Q7 B01 devices.
Potentially other devices may fall into this category in the future."""

import asyncio
from typing import Any

from roborock import B01Props
from roborock.data.b01_q7.b01_q7_code_mappings import (
    CleanPathPreferenceMapping,
    CleanRepeatMapping,
    CleanTaskTypeMapping,
    CleanTypeMapping,
    SCDeviceCleanParam,
    SCWindMapping,
    WaterLevelMapping,
)
from roborock.devices.rpc.b01_q7_channel import send_decoded_command, send_map_command
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import CommandType, ParamsType, Q7RequestMessage
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

from .clean_summary import CleanSummaryTrait

__all__ = [
    "Q7PropertiesApi",
    "CleanSummaryTrait",
]

_Q7_DPS = 10000


class Q7PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    clean_summary: CleanSummaryTrait
    """Trait for clean records / clean summary (Q7 `service.get_record_list`)."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self.clean_summary = CleanSummaryTrait(channel)
        # Map uploads are serialized per-device to avoid response cross-wiring.
        self._map_command_lock = asyncio.Lock()

    async def query_values(self, props: list[RoborockB01Props]) -> B01Props | None:
        """Query the device for the values of the given Q7 properties."""
        result = await self.send(
            RoborockB01Q7Methods.GET_PROP,
            {"property": props},
        )
        if not isinstance(result, dict):
            raise TypeError(f"Unexpected response type for GET_PROP: {type(result).__name__}: {result!r}")
        return B01Props.from_dict(result)

    async def set_prop(self, prop: RoborockB01Props, value: Any) -> None:
        """Set a property on the device."""
        await self.send(
            command=RoborockB01Q7Methods.SET_PROP,
            params={prop: value},
        )

    async def set_fan_speed(self, fan_speed: SCWindMapping) -> None:
        """Set the fan speed (wind)."""
        await self.set_prop(RoborockB01Props.WIND, fan_speed.code)

    async def set_water_level(self, water_level: WaterLevelMapping) -> None:
        """Set the water level (water)."""
        await self.set_prop(RoborockB01Props.WATER, water_level.code)

    async def set_mode(self, mode: CleanTypeMapping) -> None:
        """Set the cleaning mode (vacuum, mop, or vacuum and mop)."""
        await self.set_prop(RoborockB01Props.MODE, mode.code)

    async def set_clean_path_preference(self, preference: CleanPathPreferenceMapping) -> None:
        """Set the cleaning path preference (route)."""
        await self.set_prop(RoborockB01Props.CLEAN_PATH_PREFERENCE, preference.code)

    async def set_repeat_state(self, repeat: CleanRepeatMapping) -> None:
        """Set the cleaning repeat state (cycles)."""
        await self.set_prop(RoborockB01Props.REPEAT_STATE, repeat.code)

    async def start_clean(self) -> None:
        """Start cleaning."""
        await self.send(
            command=RoborockB01Q7Methods.SET_ROOM_CLEAN,
            params={
                "clean_type": CleanTaskTypeMapping.ALL.code,
                "ctrl_value": SCDeviceCleanParam.START.code,
                "room_ids": [],
            },
        )

    async def clean_segments(self, segment_ids: list[int]) -> None:
        """Start segment cleaning for the given ids (Q7 uses room ids)."""
        await self.send(
            command=RoborockB01Q7Methods.SET_ROOM_CLEAN,
            params={
                "clean_type": CleanTaskTypeMapping.ROOM.code,
                "ctrl_value": SCDeviceCleanParam.START.code,
                "room_ids": segment_ids,
            },
        )

    async def pause_clean(self) -> None:
        """Pause cleaning."""
        await self.send(
            command=RoborockB01Q7Methods.SET_ROOM_CLEAN,
            params={
                "clean_type": CleanTaskTypeMapping.ALL.code,
                "ctrl_value": SCDeviceCleanParam.PAUSE.code,
                "room_ids": [],
            },
        )

    async def stop_clean(self) -> None:
        """Stop cleaning."""
        await self.send(
            command=RoborockB01Q7Methods.SET_ROOM_CLEAN,
            params={
                "clean_type": CleanTaskTypeMapping.ALL.code,
                "ctrl_value": SCDeviceCleanParam.STOP.code,
                "room_ids": [],
            },
        )

    async def return_to_dock(self) -> None:
        """Return to dock."""
        await self.send(
            command=RoborockB01Q7Methods.START_RECHARGE,
            params={},
        )

    async def find_me(self) -> None:
        """Locate the robot."""
        await self.send(
            command=RoborockB01Q7Methods.FIND_DEVICE,
            params={},
        )

    async def get_map_list(self) -> dict[str, Any] | None:
        """Return map list metadata from the robot."""
        response = await self.send(
            command=RoborockB01Q7Methods.GET_MAP_LIST,
            params={},
        )
        if response is None:
            return None
        if not isinstance(response, dict):
            raise TypeError(f"Unexpected response type for GET_MAP_LIST: {type(response).__name__}: {response!r}")
        return response

    async def get_current_map_id(self) -> int:
        """Resolve and return the currently active map id."""
        map_list_response = await self.get_map_list()
        map_id = self._extract_current_map_id(map_list_response)
        if map_id is None:
            raise RoborockException(f"Unable to determine map_id from map list response: {map_list_response!r}")
        return map_id

    async def get_map_payload(self, *, map_id: int) -> bytes:
        """Fetch raw map payload bytes for the given map id."""
        request = Q7RequestMessage(
            dps=_Q7_DPS,
            command=RoborockB01Q7Methods.UPLOAD_BY_MAPID,
            params={"map_id": map_id},
        )
        async with self._map_command_lock:
            return await send_map_command(self._channel, request)

    async def get_current_map_payload(self) -> bytes:
        """Fetch raw map payload bytes for the map currently selected by the robot."""
        return await self.get_map_payload(map_id=await self.get_current_map_id())

    def _extract_current_map_id(self, map_list_response: dict[str, Any] | None) -> int | None:
        if not isinstance(map_list_response, dict):
            return None
        map_list = map_list_response.get("map_list")
        if not isinstance(map_list, list) or not map_list:
            return None

        for entry in map_list:
            if isinstance(entry, dict) and entry.get("cur") and isinstance(entry.get("id"), int):
                return entry["id"]

        first = map_list[0]
        if isinstance(first, dict) and isinstance(first.get("id"), int):
            return first["id"]
        return None

    async def send(self, command: CommandType, params: ParamsType) -> Any:
        """Send a command to the device."""
        return await send_decoded_command(
            self._channel,
            Q7RequestMessage(dps=_Q7_DPS, command=command, params=params),
        )


def create(channel: MqttChannel) -> Q7PropertiesApi:
    """Create traits for B01 devices."""
    return Q7PropertiesApi(channel)

"""Traits for Q7 B01 devices.

Potentially other devices may fall into this category in the future.
"""

from typing import Any

from roborock import B01Props
from roborock.data import HomeDataDevice, HomeDataProduct, Q7MapList, Q7MapListEntry
from roborock.data.b01_q7.b01_q7_code_mappings import (
    CleanPathPreferenceMapping,
    CleanRepeatMapping,
    CleanTaskTypeMapping,
    CleanTypeMapping,
    SCDeviceCleanParam,
    SCWindMapping,
    WaterLevelMapping,
)
from roborock.devices.rpc.b01_q7_channel import Q7MapRpcChannel, Q7RpcChannel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import CommandType, ParamsType
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

from .clean_summary import CleanSummaryTrait
from .map import MapTrait
from .map_content import MapContentTrait

__all__ = [
    "Q7PropertiesApi",
    "CleanSummaryTrait",
    "MapTrait",
    "MapContentTrait",
    "Q7MapList",
    "Q7MapListEntry",
]


class Q7PropertiesApi(Trait):
    """API for interacting with B01 Q7 devices."""

    clean_summary: CleanSummaryTrait
    """Trait for clean records / clean summary (Q7 `service.get_record_list`)."""

    map: MapTrait
    """Trait for map list metadata + raw map payload retrieval."""

    map_content: MapContentTrait
    """Trait for fetching parsed current map content."""

    def __init__(
        self,
        rpc_channel: Q7RpcChannel,
        map_rpc_channel: Q7MapRpcChannel,
        device: HomeDataDevice,
        product: HomeDataProduct,
    ) -> None:
        """Initialize the Q7 API."""
        self._rpc_channel = rpc_channel
        self._map_rpc_channel = map_rpc_channel
        self._device = device
        self._product = product

        if not device.sn or not product.model:
            raise ValueError("B01 Q7 map content requires device serial number and product model metadata")

        self.clean_summary = CleanSummaryTrait(rpc_channel)
        self.map = MapTrait(rpc_channel)
        self.map_content = MapContentTrait(
            self._map_rpc_channel,
            self.map,
        )

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

    async def set_volume(self, volume: int) -> None:
        """Set the robot voice volume (0-100)."""
        await self.set_prop(RoborockB01Props.VOLUME, volume)

    async def set_child_lock(self, enabled: bool) -> None:
        """Enable or disable the child lock."""
        await self.set_prop(RoborockB01Props.CHILD_LOCK, int(enabled))

    async def set_do_not_disturb(self, enabled: bool, begin_time: int, end_time: int) -> None:
        """Configure do-not-disturb.

        The device expects all three values together via ``service.set_quiet_time``
        (individual ``prop.set`` calls are ignored). ``begin_time``/``end_time`` are
        minutes since midnight and must be in the range 0-1439 (inclusive).

        Ranges that cross midnight are supported by passing a ``begin_time`` that is
        greater than ``end_time`` (e.g. 22:00-07:00 is ``begin_time=1320``,
        ``end_time=420``).
        """
        for name, value in (("begin_time", begin_time), ("end_time", end_time)):
            if not 0 <= value <= 1439:
                raise ValueError(f"{name} must be between 0 and 1439 minutes since midnight, got {value}")
        await self.send(
            RoborockB01Q7Methods.SET_QUIET_TIME,
            {
                "is_open": int(enabled),
                "quiet_begin_time": begin_time,
                "quiet_end_time": end_time,
            },
        )

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

    async def send(self, command: CommandType, params: ParamsType) -> Any:
        """Send a command to the device."""
        return await self._rpc_channel.send_command(command, params)


def create(
    product: HomeDataProduct,
    device: HomeDataDevice,
    rpc_channel: Q7RpcChannel,
    map_rpc_channel: Q7MapRpcChannel,
) -> Q7PropertiesApi:
    """Create traits for B01 Q7 devices."""
    if device.sn is None or product.model is None:
        raise RoborockException(
            f"Device serial number and product model are required (sn: {device.sn}, model: {product.model})"
        )
    return Q7PropertiesApi(
        rpc_channel=rpc_channel,
        map_rpc_channel=map_rpc_channel,
        device=device,
        product=product,
    )

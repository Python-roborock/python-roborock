"""Traits for Q7 B01 devices.

Potentially other devices may fall into this category in the future.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from roborock import B01Props
from roborock.data import HomeDataDevice, HomeDataProduct, Q7MapList, Q7MapListEntry, Q7RoborockPoint
from roborock.data.b01_q7.b01_q7_code_mappings import (
    CleanPathPreferenceMapping,
    CleanRepeatMapping,
    CleanTaskTypeMapping,
    CleanTypeMapping,
    SCDeviceCleanParam,
    SCWindMapping,
    WaterLevelMapping,
    WorkModeMapping,
)
from roborock.devices.rpc.b01_q7_channel import Q7MapRpcChannel, Q7PushChannel, Q7RpcChannel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import CommandType, ParamsType, Q7DevicePush
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

from .clean_summary import CleanSummaryTrait
from .goto import GotoAction, GotoActionCommand, GotoSnapshot
from .map import MapTrait
from .map_content import MapContentTrait
from .remote import RemoteTrait

__all__ = [
    "Q7PropertiesApi",
    "CleanSummaryTrait",
    "MapTrait",
    "MapContentTrait",
    "RemoteTrait",
    "Q7MapList",
    "Q7MapListEntry",
    "Q7RoborockPoint",
]

_LOGGER = logging.getLogger(__name__)

# ``service.set_preference_type`` value that selects zone cleaning (``custom_type`` 4).
_ZONE_PREFERENCE_TYPE = 4

# Emulated goto: a small zone around the target, stopped once the robot is close.
_GOTO_HALF_ZONE_MM = 250
_GOTO_TOLERANCE_MM = 300
# Leaving the dock alone takes ~30 s before the robot moves.
_GOTO_TIMEOUT = 300
_GOTO_RETRY_INTERVAL = 1
# While a goto is active the live map is requested periodically: it carries the
# current pose and keeps the device streaming ``cur_path`` positions.
_GOTO_LIVE_MAP_INTERVAL = 3


class Q7PropertiesApi(Trait):
    """API for interacting with B01 Q7 devices."""

    clean_summary: CleanSummaryTrait
    """Trait for clean records / clean summary (Q7 `service.get_record_list`)."""

    map: MapTrait
    """Trait for map list metadata + raw map payload retrieval."""

    map_content: MapContentTrait
    """Trait for fetching parsed current map content."""

    remote: RemoteTrait
    """Trait for remote (manual) control of the robot."""

    def __init__(
        self,
        rpc_channel: Q7RpcChannel,
        map_rpc_channel: Q7MapRpcChannel,
        push_channel: Q7PushChannel,
        device: HomeDataDevice,
        product: HomeDataProduct,
    ) -> None:
        """Initialize the Q7 API."""
        self._rpc_channel = rpc_channel
        self._map_rpc_channel = map_rpc_channel
        self._push_channel = push_channel
        self._device = device
        self._product = product

        if not device.sn or not product.model:
            raise ValueError("B01 Q7 map content requires device serial number and product model metadata")

        self.clean_summary = CleanSummaryTrait(rpc_channel)
        self.remote = RemoteTrait(rpc_channel)
        self.map = MapTrait(rpc_channel)
        self.map_content = MapContentTrait(
            self._map_rpc_channel,
            self.map,
        )
        self._unsub_map_pushes: Callable[[], None] | None = None
        self._unsub_device_pushes: Callable[[], None] | None = None
        self._remove_map_listener: Callable[[], None] | None = None
        self._work_mode: WorkModeMapping | None = None
        self._goto_action: GotoAction | None = None
        self._goto_action_remove_listener: Callable[[], None] | None = None
        self._goto_track_task: asyncio.Task[None] | None = None
        self._goto_command_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start listening for unsolicited map frames and device pushes."""
        if self._unsub_map_pushes is None:
            self._unsub_map_pushes = await self._map_rpc_channel.subscribe_map_pushes(self.map_content.update_from_push)
        if self._unsub_device_pushes is None:
            self._unsub_device_pushes = await self._push_channel.subscribe_device_pushes(self._handle_device_push)
        if self._remove_map_listener is None:
            self._remove_map_listener = self.map_content.add_update_listener(self._goto_source_updated)

    async def close(self) -> None:
        """Stop listening for unsolicited map frames and device pushes."""
        self.cancel_goto()
        if self._unsub_map_pushes is not None:
            self._unsub_map_pushes()
            self._unsub_map_pushes = None
        if self._unsub_device_pushes is not None:
            self._unsub_device_pushes()
            self._unsub_device_pushes = None
        if self._remove_map_listener is not None:
            self._remove_map_listener()
            self._remove_map_listener = None

    def _handle_device_push(self, push: Q7DevicePush) -> None:
        """Route an unsolicited device push to the state that depends on it."""
        self.map_content.update_from_device_push(push)
        if push.method == "prop.post" and isinstance(work_mode := push.params.get("work_mode"), int):
            self._work_mode = WorkModeMapping.from_code_optional(work_mode)
            self._goto_source_updated()

    def cancel_goto(self) -> None:
        """Cancel an emulated goto, e.g. because another command replaced it."""
        if self._goto_action is not None:
            self._goto_action.complete()
            self._goto_action = None
        if self._goto_action_remove_listener is not None:
            self._goto_action_remove_listener()
            self._goto_action_remove_listener = None
        current_task = asyncio.current_task()
        for task_name in ("_goto_track_task", "_goto_command_task"):
            if (task := getattr(self, task_name)) is not None:
                if task is not current_task:
                    task.cancel()
                setattr(self, task_name, None)

    def _goto_snapshot(self) -> GotoSnapshot:
        """Return the latest push-derived state used by an active goto action."""
        return GotoSnapshot(position=self.map_content.robot_position, work_mode=self._work_mode)

    def _goto_source_updated(self) -> None:
        """Feed the latest position / work mode to the active goto action."""
        if self._goto_action is not None:
            self._goto_action.update(self._goto_snapshot())

    def _goto_action_updated(self, action: GotoAction, command: GotoActionCommand) -> None:
        """Schedule a device command requested by the active goto action."""
        if action is not self._goto_action:
            return
        if command is GotoActionCommand.COMPLETE:
            self.cancel_goto()
            return
        if self._goto_command_task is None:
            self._goto_command_task = asyncio.create_task(
                self._async_stop_goto_zone(action),
                name="roborock_q7_goto_stop",
            )

    async def _async_stop_goto_zone(self, action: GotoAction) -> None:
        """Stop the goto zone task, leaving the robot where it is."""
        current_task = asyncio.current_task()
        try:
            await self.send(RoborockB01Q7Methods.SET_ZONE_CLEAN, {"ctrl_value": SCDeviceCleanParam.STOP.code})
        except RoborockException as err:
            _LOGGER.warning("Failed to stop Q7 goto zone task; retrying: %s", err)
            await asyncio.sleep(_GOTO_RETRY_INTERVAL)
            if action is self._goto_action:
                self._goto_command_task = None
                action.retry()
            return
        if action is self._goto_action:
            action.complete()
            self.cancel_goto()
        if self._goto_command_task is current_task:
            self._goto_command_task = None

    async def _async_track_goto(self, action: GotoAction) -> None:
        """Keep live positions flowing while the goto is active, then apply the safety timeout."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _GOTO_TIMEOUT
        try:
            while action is self._goto_action and loop.time() < deadline:
                try:
                    await self.map_content.refresh_live()
                except RoborockException as err:
                    _LOGGER.debug("Failed to refresh the Q7 live map during goto: %s", err)
                await asyncio.sleep(_GOTO_LIVE_MAP_INTERVAL)
        except asyncio.CancelledError:
            return
        if action is self._goto_action:
            action.timeout(self._goto_snapshot())

    async def goto_position(self, target: Q7RoborockPoint) -> None:
        """Move to a coordinate (common Roborock coordinates), then stay there.

        The firmware has no goto command, so (like the Q10) this starts a small
        zone-clean task around ``target`` and stops it once the live position is
        within ``_GOTO_TOLERANCE_MM``. Requires :meth:`start` so that live
        positions are received. Any other cleaning command cancels the goto.
        """
        probe = GotoAction(target, tolerance=_GOTO_TOLERANCE_MM)
        if probe.is_near_target(self.map_content.robot_position):
            return

        await self.clean_zone(
            Q7RoborockPoint(x=target.x - _GOTO_HALF_ZONE_MM, y=target.y - _GOTO_HALF_ZONE_MM),
            Q7RoborockPoint(x=target.x + _GOTO_HALF_ZONE_MM, y=target.y + _GOTO_HALF_ZONE_MM),
        )
        action = probe
        self._goto_action = action
        self._goto_action_remove_listener = action.add_update_listener(
            lambda command: self._goto_action_updated(action, command)
        )
        self._goto_track_task = asyncio.create_task(self._async_track_goto(action), name="roborock_q7_goto_track")
        action.update(self._goto_snapshot())

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

    async def set_dust_collection(self, enabled: bool) -> None:
        """Enable or disable automatic dust collection at the dock."""
        await self.set_prop(RoborockB01Props.DUST_AUTO_STATE, int(enabled))

    async def set_dust_collection_frequency(self, frequency: int) -> None:
        """Set how often the dock auto-empties, in cleans per emptying (1 = every clean)."""
        if frequency < 1:
            raise ValueError(f"frequency must be a positive number of cleans, got {frequency}")
        await self.set_prop(RoborockB01Props.DUST_FREQUENCY, frequency)

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

    async def set_button_lights(self, enabled: bool) -> None:
        """Enable or disable the button/panel lights."""
        await self.set_prop(RoborockB01Props.LIGHT_MODE, int(enabled))

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
        self.cancel_goto()

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
        self.cancel_goto()

    async def clean_zone(self, first_corner: Q7RoborockPoint, second_corner: Q7RoborockPoint) -> None:
        """Clean one rectangular zone given two opposite corners in common Roborock coordinates."""
        await self.clean_zones([(first_corner, second_corner)])

    async def clean_zones(self, zones: list[tuple[Q7RoborockPoint, Q7RoborockPoint]]) -> None:
        """Clean one or more rectangular zones in a single task.

        Each zone is given by two opposite corners in common Roborock coordinates.
        The device takes the zones as a flat list of rectangle corners in world
        meters (``[x1, y1, x2, y1, x2, y2, x1, y2, ...]``) and needs the zone
        preference type selected first; ``set_zone_clean`` then starts the task.
        """
        if not zones:
            raise ValueError("at least one zone is required")
        zone_points: list[float] = []
        for first_corner, second_corner in zones:
            x1, y1 = first_corner.to_world()
            x2, y2 = second_corner.to_world()
            if x1 == x2 or y1 == y2:
                raise ValueError(f"zone corners must span an area: {first_corner}, {second_corner}")
            min_x, max_x = sorted((x1, x2))
            min_y, max_y = sorted((y1, y2))
            zone_points += [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]
        await self.send(RoborockB01Q7Methods.SET_PREFERENCE_TYPE, {"prefer_type": _ZONE_PREFERENCE_TYPE})
        await self.send(RoborockB01Q7Methods.SET_ZONE_POINTS, {"zone_points": zone_points})
        await self.send(RoborockB01Q7Methods.SET_ZONE_CLEAN, {"ctrl_value": SCDeviceCleanParam.START.code})
        self.cancel_goto()

    async def set_carpet_turbo(self, enabled: bool) -> None:
        """Enable or disable increased suction on carpets."""
        await self.set_prop(RoborockB01Props.CARPET_TURBO, int(enabled))

    async def set_carpet_avoid(self, enabled: bool) -> None:
        """Enable or disable carpet avoidance."""
        await self.set_prop(RoborockB01Props.CARPET_AVOID, int(enabled))

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
        self.cancel_goto()

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
        self.cancel_goto()

    async def return_to_dock(self) -> None:
        """Return to dock."""
        await self.send(
            command=RoborockB01Q7Methods.START_RECHARGE,
            params={},
        )
        self.cancel_goto()

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
    push_channel: Q7PushChannel,
) -> Q7PropertiesApi:
    """Create traits for B01 Q7 devices."""
    if device.sn is None or product.model is None:
        raise RoborockException(
            f"Device serial number and product model are required (sn: {device.sn}, model: {product.model})"
        )
    return Q7PropertiesApi(
        rpc_channel=rpc_channel,
        map_rpc_channel=map_rpc_channel,
        push_channel=push_channel,
        device=device,
        product=product,
    )

"""Trait for fetching parsed map content from B01/Q7 devices.

This intentionally mirrors the v1 `MapContentTrait` contract:
- `refresh()` performs I/O and populates cached fields
- `parse_map_content()` reparses cached raw bytes without I/O
- fields `image_content`, `map_data`, and `raw_api_response` are then readable

For B01/Q7 devices, the underlying raw map payload is retrieved via `MapTrait`.

Q7 devices additionally stream map frames unprompted while cleaning; those arrive
through `update_from_push()`, which keeps the same cached fields current and
notifies registered update listeners.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from vacuum_map_parser_base.map_data import MapData

from roborock.data import Q7RoborockPoint, RoborockBase
from roborock.devices.rpc.b01_q7_channel import Q7MapRpcChannel
from roborock.devices.traits import Trait
from roborock.devices.traits.common import TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import B01MapParser, B01MapParserConfig, parse_map_type, parse_robot_pose
from roborock.protocols.b01_q7_protocol import Q7DevicePush
from roborock.roborock_typing import RoborockB01Q7Methods

from .map import MapTrait

_LOGGER = logging.getLogger(__name__)
_TRUNCATE_LENGTH = 20
_LIVE_MAP_TYPE = 0


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """Parsed map data (metadata for points on the map)."""

    raw_api_response: bytes | None = None
    """Raw bytes of the map payload from the device.

    This should be treated as an opaque blob used only internally by this
    library to re-parse the map data when needed.
    """

    robot_position: Q7RoborockPoint | None = None
    """Latest known robot position in common Roborock coordinates.

    Updated from map frames and, while the robot moves, from the live
    ``cur_path`` pushes the device publishes roughly once per second.
    """

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, map_data={self.map_data!r}, robot_position={self.robot_position!r})"


def latest_position_from_cur_path(cur_path: list[Any]) -> Q7RoborockPoint | None:
    """Return the newest pose of a ``cur_path`` push, or ``None`` if malformed.

    The device sends ``[start_index, x, y, phi, kind, (x, y, phi, kind)..., timestamp]``
    with world coordinates in meters; ``kind`` is 0 while travelling and 5 while
    cleaning.
    """
    samples = cur_path[1:-1]
    if not samples or len(samples) % 4:
        return None
    x, y = samples[-4], samples[-3]
    if not all(isinstance(value, int | float) and not isinstance(value, bool) for value in (x, y)):
        return None
    return Q7RoborockPoint.from_world(x, y)


class MapContentTrait(MapContent, Trait, TraitUpdateListener):
    """Trait for fetching parsed map content for Q7 devices."""

    def __init__(
        self,
        map_rpc_channel: Q7MapRpcChannel,
        map_trait: MapTrait,
        *,
        map_parser_config: B01MapParserConfig | None = None,
    ) -> None:
        MapContent.__init__(self)
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._map_rpc_channel = map_rpc_channel
        self._map_trait = map_trait
        self._map_parser = B01MapParser(map_parser_config)
        # Map uploads are serialized per-device to avoid response cross-wiring.
        self._map_command_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Fetch, decode, and parse the current map payload.

        This relies on the Map Trait already having fetched the map list metadata
        so it can determine the current map_id.
        """
        # Users must call first
        if (map_id := self._map_trait.current_map_id) is None:
            raise RoborockException("Unable to determine current map ID")

        async with self._map_command_lock:
            raw_payload = await self._map_rpc_channel.send_map_command(
                RoborockB01Q7Methods.UPLOAD_BY_MAPID,
                {"map_id": map_id},
            )

        self._parse_and_store(raw_payload)

    async def refresh_live(self) -> None:
        """Fetch and parse the live map of the current task, including the robot pose.

        Unlike :meth:`refresh` (the saved map, which carries no live pose), this
        requests the live map (``service.upload_by_maptype`` with map type 0), as the
        official app does. Requesting it also makes the device stream ``cur_path``
        pushes while it moves (verified on a Q7 sc05: without a live-map request no
        ``cur_path`` is published), keeping :attr:`robot_position` current about
        once per second.
        """
        async with self._map_command_lock:
            raw_payload = await self._map_rpc_channel.send_map_command(
                RoborockB01Q7Methods.UPLOAD_BY_MAPTYPE,
                {"map_type": _LIVE_MAP_TYPE},
            )

        self._parse_and_store(raw_payload)

    def update_from_push(self, raw_payload: bytes) -> None:
        """Store an unsolicited SCMap frame pushed by the device during cleaning.

        Pushed frames carry the live robot pose and cleaning path, so the
        rendered image stays current without polling. Frames for other maps
        than the live one are ignored to not overwrite the current map.
        """
        try:
            map_type = parse_map_type(raw_payload)
        except RoborockException as ex:
            _LOGGER.debug("Failed to parse pushed B01 map frame: %s", ex)
            return

        if map_type != _LIVE_MAP_TYPE:
            _LOGGER.debug("Ignoring pushed B01 map frame of type %s", map_type)
            return

        try:
            self._parse_and_store(raw_payload)
        except RoborockException as ex:
            _LOGGER.debug("Failed to parse pushed B01 map frame: %s", ex)
            return
        self._notify_update()

    def _parse_and_store(self, raw_payload: bytes) -> None:
        """Parse decoded SCMap bytes and update the cached fields."""
        try:
            parsed_data = self._map_parser.parse(raw_payload)
        except RoborockException:
            raise
        except Exception as ex:
            raise RoborockException("Failed to parse B01 map data") from ex

        if parsed_data.image_content is None:
            raise RoborockException("Failed to render B01 map image")

        self.image_content = parsed_data.image_content
        self.map_data = parsed_data.map_data
        self.raw_api_response = raw_payload
        # Saved maps and frames without a fix carry no usable pose: keep the last known one.
        try:
            pose = parse_robot_pose(raw_payload)
        except RoborockException as ex:
            _LOGGER.debug("Failed to read robot pose from B01 map frame: %s", ex)
            return
        if pose is not None:
            self.robot_position = Q7RoborockPoint.from_world(*pose)

    def update_from_device_push(self, push: Q7DevicePush) -> None:
        """Update the robot position from a live ``cur_path`` push and notify listeners."""
        if push.method != "prop.post" or not isinstance(cur_path := push.params.get("cur_path"), list):
            return
        if (position := latest_position_from_cur_path(cur_path)) is None:
            _LOGGER.debug("Ignoring malformed Q7 cur_path push: %s", cur_path)
            return
        if position == self.robot_position:
            return
        self.robot_position = position
        self._notify_update()

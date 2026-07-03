"""Map content trait for B01 Q10 devices.

Unlike the v1 / Q7 maps, the Q10 has no synchronous "get map" command, so this
trait is purely push-driven and mirrors the Q10 ``StatusTrait`` contract:

- The device pushes its current map/path as protocol-301 ``MAP_RESPONSE``
  messages (a ``dpRequestDps`` nudges it to do so). The protocol layer decodes
  those into :class:`Q10MapPacket` / :class:`Q10TracePacket` objects and the
  ``Q10PropertiesApi`` subscribe loop routes them to
  :meth:`MapContentTrait.update_from_map_packet` /
  :meth:`MapContentTrait.update_from_trace_packet`.
- Those methods render/cache the content and notify update listeners (register
  via :meth:`add_update_listener`).
- ``image_content``, ``map_data``, ``rooms``, ``path`` and ``robot_position``
  are readable and reflect the most recently pushed map.

Unlike the Q7, the Q10 map payload is unencrypted, so no map key is required.
"""

import logging
from dataclasses import dataclass, field

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.traits.common import TraitUpdateListener
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10MapPacket,
    Q10Point,
    Q10Room,
    Q10TracePacket,
)

_LOGGER = logging.getLogger(__name__)

_TRUNCATE_LENGTH = 20


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing Q10 map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """Parsed map data (image metadata + room names)."""

    rooms: list[Q10Room] = field(default_factory=list)
    """Rooms (segments) reported by the device, with ids and names."""

    path: list[Q10Point] = field(default_factory=list)
    """Full path of the current cleaning session (oldest point first).

    The robot accumulates this server-side and serves the whole trajectory so
    far in one packet, so it is complete even if we connect mid-session. Only
    populated while a cleaning session is active."""

    robot_position: Q10Point | None = None
    """Current robot position (the most recent path point), if known."""

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, rooms={self.rooms!r})"


class MapContentTrait(MapContent, TraitUpdateListener):
    """Trait holding the most recently pushed parsed map content for Q10 devices.

    The Q10 has no synchronous get-map request; the device pushes map and trace
    packets, which the protocol layer decodes and the ``Q10PropertiesApi``
    subscribe loop feeds into :meth:`update_from_map_packet` /
    :meth:`update_from_trace_packet`. Consumers read the cached fields and/or
    register a callback with :meth:`add_update_listener` to be notified when new
    map content arrives.
    """

    def __init__(
        self,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._map_parser = B01Q10MapParser(map_parser_config)

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Render a pushed full-map packet into the cached image/rooms.

        Rendering failures are logged and skipped (listeners are not notified) so
        a single bad push cannot tear down the subscribe loop.
        """
        parsed = self._map_parser.parse_packet(packet)
        if parsed.image_content is None:
            _LOGGER.debug("Failed to render Q10 map image")
            return
        self.image_content = parsed.image_content
        self.map_data = parsed.map_data
        self.rooms = packet.rooms
        self._notify_update()

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Cache the path/robot position from a pushed trace packet."""
        self.path = packet.points
        self.robot_position = packet.robot_position
        self._notify_update()

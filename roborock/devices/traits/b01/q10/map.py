"""Map content trait for B01 Q10 devices.

Unlike the v1 / Q7 maps, the Q10 has no synchronous "get map" command, so this
trait is purely push-driven and mirrors the Q10 ``StatusTrait`` contract:

- The device pushes its current map/path as protocol-301 ``MAP_RESPONSE``
  messages (a ``dpRequestDps`` nudges it to do so). The ``Q10PropertiesApi``
  subscribe loop routes those messages to :meth:`MapContentTrait.update_from_map_response`.
- ``update_from_map_response`` parses the payload, updates the cached fields and
  notifies update listeners (register via :meth:`add_update_listener`).
- ``parse_map_content()`` reparses the cached raw bytes without I/O.
- ``image_content``, ``map_data``, ``rooms``, ``path``, ``robot_position`` and
  ``raw_api_response`` are readable and reflect the most recently pushed map.

Unlike the Q7, the Q10 map payload is unencrypted, so no map key is required.
"""

import logging
from dataclasses import dataclass, field

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.traits.common import TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.map.b01_grid_layers import GridLayers
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10Point,
    Q10Room,
    decompose_layers,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)

_TRUNCATE_LENGTH = 20

# MAP_RESPONSE (protocol 301) payloads start with a 2-byte marker identifying the
# packet kind: a full map (``01 01``) or a live trace/path (``02 01``).
_MAP_PACKET_MARKER = b"\x01\x01"
_TRACE_PACKET_MARKER = b"\x02\x01"


@dataclass
class MapContent(RoborockBase):
    """Dataclass representing Q10 map content."""

    image_content: bytes | None = None
    """The rendered image of the map in PNG format."""

    map_data: MapData | None = None
    """Parsed map data (image metadata + room names)."""

    rooms: list[Q10Room] = field(default_factory=list)
    """Rooms (segments) reported by the device, with ids and names."""

    layers: GridLayers | None = None
    """Separable map layers (background / wall / floor / per-room) in grid-pixel
    space, each renderable to a transparent PNG for frontend compositing."""

    path: list[Q10Point] = field(default_factory=list)
    """Full path of the current cleaning session (oldest point first).

    The robot accumulates this server-side and serves the whole trajectory so
    far in one packet, so it is complete even if we connect mid-session. Only
    populated while a cleaning session is active."""

    robot_position: Q10Point | None = None
    """Current robot position (the most recent path point), if known."""

    raw_api_response: bytes | None = None
    """Raw bytes of the map payload from the device (opaque blob for re-parsing)."""

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, rooms={self.rooms!r})"


class MapContentTrait(MapContent, TraitUpdateListener):
    """Trait holding the most recently pushed parsed map content for Q10 devices.

    The Q10 has no synchronous get-map request; the device pushes map and trace
    packets, which the ``Q10PropertiesApi`` subscribe loop feeds into
    :meth:`update_from_map_response`. Consumers read the cached fields and/or
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

    def update_from_map_response(self, message: RoborockMessage) -> bool:
        """Update cached map/trace state from a pushed ``MAP_RESPONSE`` message.

        Returns ``True`` if the message was a recognized Q10 map (``01 01``) or
        trace (``02 01``) packet (so the caller can stop processing it), and
        ``False`` otherwise. Update listeners are notified only when a packet is
        parsed successfully.
        """
        if message.protocol != RoborockMessageProtocol.MAP_RESPONSE or not message.payload:
            return False
        marker = message.payload[:2]
        if marker == _MAP_PACKET_MARKER:
            self.raw_api_response = message.payload
            try:
                self.parse_map_content()
            except RoborockException as ex:
                _LOGGER.debug("Failed to parse Q10 map packet: %s", ex)
                return True
            self._notify_update()
            return True
        if marker == _TRACE_PACKET_MARKER:
            try:
                trace = parse_trace_packet(message.payload)
            except RoborockException as ex:
                _LOGGER.debug("Failed to parse Q10 trace packet: %s", ex)
                return True
            self.path = trace.points
            self.robot_position = trace.robot_position
            self._notify_update()
            return True
        return False

    def parse_map_content(self) -> None:
        """Reparse the cached raw map payload without performing any I/O."""
        if self.raw_api_response is None:
            raise RoborockException("No map payload available; no map has been pushed yet")

        try:
            parsed = self._map_parser.parse(self.raw_api_response)
            packet = parse_map_packet(self.raw_api_response)
        except RoborockException:
            raise
        except Exception as ex:
            raise RoborockException("Failed to parse Q10 map data") from ex

        if parsed.image_content is None:
            raise RoborockException("Failed to render Q10 map image")

        self.image_content = parsed.image_content
        self.map_data = parsed.map_data
        self.rooms = packet.rooms
        self.layers = decompose_layers(packet)

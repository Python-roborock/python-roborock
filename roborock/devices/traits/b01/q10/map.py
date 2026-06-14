"""Map content trait for B01 Q10 devices.

This mirrors the v1 / Q7 ``MapContentTrait`` contract:
- ``refresh()`` performs I/O and populates cached fields.
- ``parse_map_content()`` reparses cached raw bytes without I/O.
- ``image_content``, ``map_data``, ``rooms`` and ``raw_api_response`` are readable.

Unlike the Q7, the Q10 map payload is unencrypted, so no map key is required.
The raw payload is retrieved by :func:`request_map`, which triggers the device
to push its current map.
"""

from dataclasses import dataclass, field

from vacuum_map_parser_base.map_data import MapData

from roborock.data import RoborockBase
from roborock.devices.rpc.b01_q10_channel import request_map, request_trace
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10Point,
    Q10Room,
    parse_map_packet,
    parse_trace_packet,
)

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

    raw_api_response: bytes | None = None
    """Raw bytes of the map payload from the device (opaque blob for re-parsing)."""

    def __repr__(self) -> str:
        img = self.image_content
        if img and len(img) > _TRUNCATE_LENGTH:
            img = img[: _TRUNCATE_LENGTH - 3] + b"..."
        return f"MapContent(image_content={img!r}, rooms={self.rooms!r})"


class MapContentTrait(MapContent, Trait):
    """Trait for fetching parsed map content for Q10 devices."""

    def __init__(
        self,
        channel: MqttChannel,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        super().__init__()
        self._channel = channel
        self._map_parser = B01Q10MapParser(map_parser_config)

    async def refresh(self) -> None:
        """Fetch, decode, and parse the current map payload."""
        raw_payload = await request_map(self._channel)
        self.raw_api_response = raw_payload
        self.parse_map_content()

    def parse_map_content(self) -> None:
        """Reparse the cached raw map payload without performing any I/O."""
        if self.raw_api_response is None:
            raise RoborockException("No map payload available; call refresh() first")

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

    async def refresh_trace(self) -> None:
        """Fetch the current session's cleaning path and robot position.

        Populates :attr:`path` with the full trajectory of the active cleaning
        session (the robot accumulates it, so the whole path is returned even
        when we connect mid-session) and :attr:`robot_position` with the most
        recent point. The robot only emits trace packets while a session is
        active, so this raises :class:`RoborockException` (timeout) for an
        idle/docked robot.
        """
        raw_payload = await request_trace(self._channel)
        trace = parse_trace_packet(raw_payload)
        self.path = trace.points
        self.robot_position = trace.robot_position

"""Push-driven map traits for B01 Q10 devices.

Map-related state arrives on three independent streams:

* map packets are decoded from map-protocol responses;
* trace packets are decoded from trace-protocol responses;
* restricted zones and virtual walls arrive as ordinary DPS values.

``MapDpsTrait`` owns the low-level DPS read model. ``MapContentTrait`` depends
on it and combines that state with the latest map/trace packets through the pure
functions in :mod:`roborock.map.b01_q10_render`. The high-level trait keeps only
the latest value from each source and one replace-whole rendered image;
calibration, path placement and overlay placement remain inside the renderer.
"""

import logging
from dataclasses import dataclass, field

from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10MapPacket,
    Q10Point,
    Q10Room,
    Q10TracePacket,
)
from roborock.map.b01_q10_overlays import Q10Zone, parse_virtual_wall_blob, parse_zone_blob
from roborock.map.b01_q10_render import Q10MapOverlays, render_q10_map

from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


@dataclass
class MapDps(RoborockBase):
    """Low-level map values delivered in the Q10 DPS stream."""

    restricted_zone_up: str | None = field(default=None, metadata={"dps": B01_Q10_DP.RESTRICTED_ZONE_UP})
    virtual_wall_up: str | None = field(default=None, metadata={"dps": B01_Q10_DP.VIRTUAL_WALL_UP})


class MapDpsTrait(MapDps, UpdatableTrait):
    """Converter-backed read model for map-related DPS values."""

    _CONVERTER = DpsDataConverter.from_dataclass(MapDps)

    def __init__(self) -> None:
        MapDps.__init__(self)
        UpdatableTrait.__init__(self, command=None, logger=_LOGGER)

    @property
    def zones(self) -> list[Q10Zone]:
        """Restricted zones decoded from the latest DPS value."""
        return parse_zone_blob(self.restricted_zone_up)

    @property
    def virtual_walls(self) -> list[Q10Zone]:
        """Virtual walls decoded from the latest DPS value."""
        return parse_virtual_wall_blob(self.virtual_wall_up)


class MapContentTrait(TraitUpdateListener):
    """High-level composed Q10 map view.

    The latest map and trace packets are combined with the injected
    :class:`MapDpsTrait` whenever any of those three sources changes.
    """

    def __init__(
        self,
        map_dps: MapDpsTrait | None = None,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._config = map_parser_config or B01Q10MapParserConfig()
        self._map_dps = map_dps or MapDpsTrait()
        self._map_packet: Q10MapPacket | None = None
        self._trace_packet: Q10TracePacket | None = None
        self._image_content: bytes | None = None
        self._map_dps.add_update_listener(self._map_dps_updated)

    @property
    def image_content(self) -> bytes | None:
        """The composed map PNG, if a map has been pushed."""
        return self._image_content

    @property
    def rooms(self) -> list[Q10Room]:
        """Rooms reported by the device."""
        return self._map_packet.rooms if self._map_packet else []

    @property
    def path(self) -> list[Q10Point]:
        """Full path from the latest trace packet."""
        return self._trace_packet.points if self._trace_packet else []

    @property
    def robot_position(self) -> Q10Point | None:
        """Current robot position from the latest trace packet."""
        return self._trace_packet.robot_position if self._trace_packet else None

    @property
    def robot_heading(self) -> int | None:
        """Current robot heading from the latest trace packet."""
        return self._trace_packet.heading if self._trace_packet else None

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Store a map-protocol update and render the latest sources."""
        self._map_packet = packet
        self._render()
        self._notify_update()

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Store a trace-protocol update and render the latest sources."""
        self._trace_packet = packet
        self._render()
        self._notify_update()

    def _map_dps_updated(self) -> None:
        """Render after the low-level DPS source changes."""
        self._render()
        self._notify_update()

    def _render(self) -> None:
        """Render the latest map, trace and DPS sources, if a map is available."""
        if self._map_packet is None:
            return
        try:
            self._image_content = render_q10_map(
                self._map_packet,
                self._trace_packet,
                Q10MapOverlays(
                    zones=tuple(self._map_dps.zones),
                    virtual_walls=tuple(self._map_dps.virtual_walls),
                ),
                config=self._config,
            )
        except RoborockException as ex:
            _LOGGER.debug("Failed to render Q10 map packet: %s", ex)

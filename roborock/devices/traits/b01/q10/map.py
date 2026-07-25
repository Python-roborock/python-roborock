"""Push-driven map traits for B01 Q10 devices.

Map-related state arrives on four independent streams:

* map packets are decoded from map-protocol responses;
* trace packets are decoded from trace-protocol responses;
* restricted zones and virtual walls arrive as ordinary DPS values.
* the device status indicates when an idle robot is charging at the saved dock.

``MapDpsTrait`` owns the low-level DPS read model. ``MapContentTrait`` depends
on it and the status trait, then combines that state with the latest map/trace
packets through the pure functions in :mod:`roborock.map.b01_q10_render`. The
high-level trait keeps only the latest value from each source and one
replace-whole rendered image;
calibration, path placement and overlay placement remain inside the renderer.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXDeviceState
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10MapPacket,
    Q10Point,
    Q10Room,
    Q10TracePacket,
)
from roborock.map.b01_q10_overlays import parse_virtual_wall_blob, parse_zone_blob
from roborock.map.b01_q10_render import Q10MapOverlays, render_q10_map

from .common import UpdatableTrait
from .status import StatusTrait

_LOGGER = logging.getLogger(__name__)
_DOCKED_STATES = {YXDeviceState.CHARGING, YXDeviceState.EMPTYING_THE_BIN}


@dataclass
class MapDps(RoborockBase):
    """Low-level map values delivered in the Q10 DPS stream."""

    restricted_zone_up: str | None = field(default=None, metadata={"dps": B01_Q10_DP.RESTRICTED_ZONE_UP})
    virtual_wall_up: str | None = field(default=None, metadata={"dps": B01_Q10_DP.VIRTUAL_WALL_UP})


class MapDpsTrait(MapDps, UpdatableTrait):
    """Private read model for map-related DPS values and decoded overlays."""

    _CONVERTER = DpsDataConverter.from_dataclass(MapDps)

    def __init__(self) -> None:
        MapDps.__init__(self)
        UpdatableTrait.__init__(self, command=None, logger=_LOGGER)
        self._overlays = Q10MapOverlays()

    @property
    def overlays(self) -> Q10MapOverlays:
        """Overlays decoded once from the latest relevant DPS update."""
        return self._overlays

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Decode overlay blobs when they arrive, then notify dependents."""
        if not self._CONVERTER.update_from_dps(self, decoded_dps):
            return
        self._overlays = Q10MapOverlays(
            zones=tuple(parse_zone_blob(self.restricted_zone_up)),
            virtual_walls=tuple(parse_virtual_wall_blob(self.virtual_wall_up)),
        )
        self._notify_update()


class MapContentTrait(TraitUpdateListener):
    """High-level composed Q10 map view.

    The latest map and trace packets are combined with the injected map DPS and
    status traits whenever any source changes.
    """

    def __init__(
        self,
        map_dps: MapDpsTrait,
        status: StatusTrait | None = None,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._config = map_parser_config or B01Q10MapParserConfig()
        self._map_dps = map_dps
        self._status = status or StatusTrait()
        self._robot_at_dock = self._status.status in _DOCKED_STATES
        self._map_packet: Q10MapPacket | None = None
        self._trace_packet: Q10TracePacket | None = None
        self._image_content: bytes | None = None
        self._map_generation = 0
        self._trace_generation = 0
        self._source_update_depth = 0
        self._source_update_pending = False
        self._map_dps.add_update_listener(self._map_dps_updated)
        self._status.add_update_listener(self._status_updated)

    @property
    def image_content(self) -> bytes | None:
        """The composed map PNG, if the latest map rendered successfully."""
        return self._image_content

    @property
    def rooms(self) -> list[Q10Room]:
        """Rooms reported by the device."""
        return self._map_packet.rooms if self._map_packet else []

    @property
    def path(self) -> list[Q10Point]:
        """Full path for live status and callers drawing their own map overlay."""
        return self._trace_packet.points if self._trace_packet else []

    @property
    def robot_position(self) -> Q10Point | None:
        """Current position for live status and caller-rendered map overlays."""
        return self._trace_packet.robot_position if self._trace_packet else None

    @property
    def robot_heading(self) -> int | None:
        """Current heading for orienting a robot marker on a caller-rendered map."""
        return self._trace_packet.heading if self._trace_packet else None

    @property
    def map_generation(self) -> int:
        """Number of map packets received by this trait."""
        return self._map_generation

    @property
    def trace_generation(self) -> int:
        """Number of trace packets received by this trait."""
        return self._trace_generation

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Store a map-protocol update and render the latest sources."""
        self._map_packet = packet
        self._map_generation += 1
        self._render()
        self._notify_update()

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Store a trace-protocol update and render the latest sources."""
        # A late packet from the completed clean cannot move a robot that the
        # status stream already confirmed is docked.
        self._trace_packet = None if self._robot_at_dock else packet
        self._trace_generation += 1
        self._render()
        self._notify_update()

    def begin_source_update(self) -> None:
        """Defer dependent rendering while one DPS message is applied."""
        self._source_update_depth += 1

    def end_source_update(self) -> None:
        """Render once after all traits consumed the same DPS message."""
        self._source_update_depth -= 1
        if self._source_update_depth == 0 and self._source_update_pending:
            self._source_update_pending = False
            self._render_and_notify()

    def _source_updated(self, *, notify_without_map: bool = False) -> None:
        """Render now, or defer until the current DPS update is complete."""
        if self._map_packet is None and not notify_without_map:
            return
        if self._source_update_depth:
            self._source_update_pending = True
            return
        self._render_and_notify()

    def _render_and_notify(self) -> None:
        """Recompose the current map and publish one update."""
        self._render()
        self._notify_update()

    def _map_dps_updated(self) -> None:
        """Render after the low-level map DPS source changes."""
        self._source_updated()

    def _status_updated(self) -> None:
        """Render only when the status changes whether the robot is docked."""
        robot_at_dock = self._status.status in _DOCKED_STATES
        if robot_at_dock == self._robot_at_dock:
            return
        self._robot_at_dock = robot_at_dock
        trace_cleared = robot_at_dock and self._trace_packet is not None
        if robot_at_dock:
            self._trace_packet = None
        self._source_updated(notify_without_map=trace_cleared)

    def _render(self) -> None:
        """Render the required map with the latest optional trace and overlays."""
        if self._map_packet is None:
            return
        try:
            self._image_content = render_q10_map(
                self._map_packet,
                self._trace_packet,
                self._map_dps.overlays,
                config=self._config,
                robot_at_dock=self._robot_at_dock,
            )
        except RoborockException as ex:
            _LOGGER.debug("Failed to render Q10 map packet: %s", ex)
            self._image_content = None

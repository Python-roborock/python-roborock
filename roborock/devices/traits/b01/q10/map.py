"""Push-driven map traits for B01 Q10 devices.

Map-related state arrives on three independent streams:

* map packets are decoded from map-protocol responses;
* trace packets are decoded from trace-protocol responses;
* restricted zones, virtual walls and dock state arrive as ordinary DPS values.

``MapDpsTrait`` owns the low-level map-specific DPS read model.
``MapContentTrait`` requests a current-map push through ``REQUEST_DPS`` and
combines the latest map and trace packets with the map DPS state through the
pure functions in :mod:`roborock.map.b01_q10_render`. Saved-map list/detail
operations remain on ``MapsTrait``.
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
    Q10MapPacketKind,
    Q10Obstacle,
    Q10Point,
    Q10Room,
    Q10TracePacket,
)
from roborock.map.b01_q10_overlays import parse_virtual_wall_blob, parse_zone_blob
from roborock.map.b01_q10_render import Q10MapOverlays, render_q10_map, resolve_q10_current_room

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)
_DOCKED_STATES = {YXDeviceState.CHARGING, YXDeviceState.EMPTYING_THE_BIN}
_CURRENT_ROOM_STATES = {
    YXDeviceState.CLEANING,
    YXDeviceState.PAUSED,
    YXDeviceState.SWEEPING,
    YXDeviceState.MOPPING,
    YXDeviceState.SWEEP_AND_MOP,
    YXDeviceState.TRANSITIONING,
}


@dataclass
class MapDps(RoborockBase):
    """Low-level map values delivered in the Q10 DPS stream."""

    status: YXDeviceState | None = field(default=None, metadata={"dps": B01_Q10_DP.STATUS})
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

    @property
    def robot_at_dock(self) -> bool:
        """Whether status places the idle robot at the saved dock."""
        return self.status in _DOCKED_STATES

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Update one coherent snapshot of the DPS inputs used by the map."""
        if not self._CONVERTER.update_from_dps(self, decoded_dps):
            return
        self._overlays = Q10MapOverlays(
            zones=tuple(parse_zone_blob(self.restricted_zone_up)),
            virtual_walls=tuple(parse_virtual_wall_blob(self.virtual_wall_up)),
        )
        self._notify_update()


class MapContentTrait(TraitUpdateListener):
    """High-level composed Q10 map view.

    The latest map and trace packets are combined with the injected
    :class:`MapDpsTrait` whenever a source changes. Current-map acquisition is
    independent of the saved-map list.
    """

    def __init__(
        self,
        map_dps: MapDpsTrait,
        command: CommandTrait,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._config = map_parser_config or B01Q10MapParserConfig()
        self._map_dps = map_dps
        self._command = command
        self._map_packet: Q10MapPacket | None = None
        self._trace_packet: Q10TracePacket | None = None
        self._current_room_trace_fresh = False
        self._image_content: bytes | None = None
        self._map_revision = 0
        self._trace_revision = 0
        self._map_dps.add_update_listener(self._map_dps_updated)

    async def refresh(self) -> None:
        """Request a safe asynchronous current-map/status push.

        Some ss07 firmware treats ``dpMultiMap op:get`` as an active
        cleaning/relocation command. ``REQUEST_DPS`` is the device's read-only
        current-map request and does not depend on a saved-map ID.
        """
        await self._command.send(B01_Q10_DP.REQUEST_DPS, params={})

    @property
    def image_content(self) -> bytes | None:
        """The composed map PNG, if the latest map rendered successfully."""
        return self._image_content

    @property
    def map_revision(self) -> int:
        """Monotonic revision incremented only by current-map packets."""
        return self._map_revision

    @property
    def trace_revision(self) -> int:
        """Monotonic revision incremented only by live-trace state changes."""
        return self._trace_revision

    @property
    def rooms(self) -> list[Q10Room]:
        """Rooms reported by the device."""
        return self._map_packet.rooms if self._map_packet else []

    @property
    def path(self) -> list[Q10Point]:
        """Full path for live status and callers drawing their own map overlay."""
        return self._trace_packet.points if self._trace_packet else []

    @property
    def obstacles(self) -> list[Q10Obstacle]:
        """Position-only obstacle markers reported by the current map."""
        return list(self._map_packet.obstacles) if self._map_packet else []

    @property
    def robot_position(self) -> Q10Point | None:
        """Current position for live status and caller-rendered map overlays."""
        return self._trace_packet.robot_position if self._trace_packet else None

    @property
    def robot_heading(self) -> int | None:
        """Current heading for orienting a robot marker on a caller-rendered map."""
        return self._trace_packet.heading if self._trace_packet else None

    @property
    def current_room(self) -> Q10Room | None:
        """Room currently occupied during an active or paused cleaning task.

        No authoritative active-segment field has been identified or observed
        on ss07 firmware. This value is inferred conservatively from the latest
        live robot position and segmented occupancy grid, and is ``None``
        outside cleaning states or whenever the position cannot be mapped
        unambiguously.
        """
        if (
            self._map_dps.status not in _CURRENT_ROOM_STATES
            or self._map_packet is None
            or self._trace_packet is None
            or not self._current_room_trace_fresh
        ):
            return None
        return resolve_q10_current_room(self._map_packet, self._trace_packet)

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Store a map-protocol update and render the latest sources."""
        if packet.kind is not Q10MapPacketKind.CURRENT:
            raise ValueError(f"Expected a current Q10 map packet, got {packet.kind.value}")
        self._map_packet = packet
        self._map_revision += 1
        self._render()
        self._notify_update()

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Store a trace-protocol update and render the latest sources."""
        self._trace_packet = None if self._map_dps.robot_at_dock else packet
        # A trace can precede the first status push during startup, but a trace
        # received while an explicitly inactive state is known must never be
        # reused as the position for a later cleaning session.
        self._current_room_trace_fresh = self._trace_packet is not None and (
            self._map_dps.status is None or self._map_dps.status in _CURRENT_ROOM_STATES
        )
        self._trace_revision += 1
        self._render()
        self._notify_update()

    def _map_dps_updated(self) -> None:
        """Render after the low-level map DPS source changes."""
        if self._map_dps.status is not None and self._map_dps.status not in _CURRENT_ROOM_STATES:
            self._current_room_trace_fresh = False
        if self._map_dps.robot_at_dock and self._trace_packet is not None:
            # A completed cleaning trace is not the current robot position once
            # the device is docked. Clear the public live-path state even if the
            # firmware does not send its usual zero-point trace.
            self._trace_packet = None
            self._current_room_trace_fresh = False
            self._trace_revision += 1
        if self._map_packet is None:
            return
        self._render()
        self._notify_update()

    def _render(self) -> None:
        """Render the required map with the latest optional trace and overlays."""
        if self._map_packet is None:
            return
        try:
            self._image_content = render_q10_map(
                self._map_packet,
                self._trace_packet if not self._map_dps.robot_at_dock else None,
                self._map_dps.overlays,
                config=self._config,
                robot_at_dock=self._map_dps.robot_at_dock,
            )
        except RoborockException as ex:
            _LOGGER.debug("Failed to render Q10 map packet: %s", ex)
            self._image_content = None

    def as_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """Return the trait data as a dictionary, excluding large binary data."""
        exclude_set = exclude or set()
        current_room = self.current_room
        data = {
            "rooms": [room.as_dict() for room in self.rooms],
            "obstacles": [obstacle.as_dict() for obstacle in self.obstacles],
            "path": [point.as_dict() for point in self.path],
            "robotPosition": self.robot_position.as_dict() if self.robot_position is not None else None,
            "robotHeading": self.robot_heading,
            "currentRoom": current_room.as_dict() if current_room is not None else None,
        }
        for key in exclude_set:
            data.pop(key, None)
        return data

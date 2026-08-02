"""Push-driven map traits for B01 Q10 devices.

Map-related state arrives on three independent streams:

* map packets are decoded from map-protocol responses;
* trace packets are decoded from trace-protocol responses;
* restricted zones, virtual walls and dock state arrive as ordinary DPS values.

``MapDpsTrait`` owns the low-level map-specific DPS read model.
``MapContentTrait`` uses a stored ID from ``MapsTrait`` only when it requests
content. It combines the latest map and trace packets with the map DPS state
through the pure functions in :mod:`roborock.map.b01_q10_render`. Map-list
updates do not refresh content.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.callbacks import CallbackList
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

from .command import CommandTrait
from .common import UpdatableTrait
from .maps import MapsTrait

_LOGGER = logging.getLogger(__name__)
_DOCKED_STATES = {YXDeviceState.CHARGING, YXDeviceState.EMPTYING_THE_BIN}


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
    :class:`MapDpsTrait` whenever a source changes. The
    :class:`MapsTrait` supplies a stored ID only when this trait requests
    content.
    """

    def __init__(
        self,
        map_dps: MapDpsTrait,
        maps: MapsTrait,
        command: CommandTrait,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._config = map_parser_config or B01Q10MapParserConfig()
        self._map_dps = map_dps
        self._maps = maps
        self._command = command
        self._map_packet: Q10MapPacket | None = None
        self._trace_packet: Q10TracePacket | None = None
        self._image_content: bytes | None = None
        self._map_packet_callbacks: CallbackList[None] = CallbackList(_LOGGER)
        self._trace_packet_callbacks: CallbackList[None] = CallbackList(_LOGGER)
        self._map_dps.add_update_listener(self._map_dps_updated)

    async def refresh(self) -> None:
        """Request content for the first map in the latest saved-map list."""
        if (map_id := self._maps.current_map_id) is None:
            raise RoborockException("Cannot request Q10 map content before the map list is available")
        # Map lists and map content can change at different times. Reuse the
        # stored ID so a content refresh does not also refresh the list.
        await self._command.send(
            B01_Q10_DP.COMMON,
            {
                str(B01_Q10_DP.MULTI_MAP.code): {
                    "op": "get",
                    "id": map_id,
                }
            },
        )

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

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Store a map-protocol update and render the latest sources."""
        self._map_packet = packet
        self._render()
        self._notify_update()
        self._map_packet_callbacks(None)

    def update_from_trace_packet(self, packet: Q10TracePacket) -> None:
        """Store a trace-protocol update and render the latest sources."""
        self._trace_packet = packet
        self._render()
        self._notify_update()
        self._trace_packet_callbacks(None)

    def _add_map_packet_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register an internal callback for decoded map packets."""
        return self._map_packet_callbacks.add_callback(lambda _: callback())

    def _add_trace_packet_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register an internal callback for decoded trace packets."""
        return self._trace_packet_callbacks.add_callback(lambda _: callback())

    def _map_dps_updated(self) -> None:
        """Render after the low-level map DPS source changes."""
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

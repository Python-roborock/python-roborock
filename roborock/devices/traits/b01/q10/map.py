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
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.callbacks import CallbackList
from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import dpMultiMap
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

_LOGGER = logging.getLogger(__name__)


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


@dataclass
class MapListDps(RoborockBase):
    """Typed ``dpMultiMap`` state delivered through the Q10 DPS stream."""

    multi_map: dpMultiMap | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP})


class MapContentTrait(MapListDps, TraitUpdateListener):
    """High-level composed Q10 map view.

    The latest map and trace packets are combined with the injected
    :class:`MapDpsTrait` whenever any of those three sources changes.
    """

    _CONVERTER = DpsDataConverter.from_dataclass(MapListDps)

    def __init__(
        self,
        map_dps: MapDpsTrait,
        command: CommandTrait | None = None,
        *,
        map_parser_config: B01Q10MapParserConfig | None = None,
    ) -> None:
        MapListDps.__init__(self)
        TraitUpdateListener.__init__(self, logger=_LOGGER)
        self._config = map_parser_config or B01Q10MapParserConfig()
        self._map_dps = map_dps
        self._command = command
        self._map_packet: Q10MapPacket | None = None
        self._trace_packet: Q10TracePacket | None = None
        self._image_content: bytes | None = None
        self._map_packet_callbacks: CallbackList[None] = CallbackList(_LOGGER)
        self._trace_packet_callbacks: CallbackList[None] = CallbackList(_LOGGER)
        self._map_dps.add_update_listener(self._map_dps_updated)

    async def refresh(self) -> None:
        """Request the current saved map independently of general status."""
        if self._command is None:
            raise ValueError("Trait is read-only; no command channel was provided")
        await self._command.send(
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
        )

    async def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Request map content when a typed ``dpMultiMap`` list response arrives."""
        if not self._CONVERTER.update_from_dps(self, decoded_dps):
            return
        if self._command is None or self.multi_map is None or self.multi_map.op != "list" or self.multi_map.result != 1:
            return
        if (map_id := self.multi_map.current_map_id) is None:
            _LOGGER.debug("Q10 map list response did not contain a map ID")
            return
        try:
            await self._command.send(
                B01_Q10_DP.COMMON,
                {
                    str(B01_Q10_DP.MULTI_MAP.code): {
                        "op": "get",
                        "id": map_id,
                    }
                },
            )
        except RoborockException as ex:
            # A failed follow-up must not kill the persistent subscribe loop.
            _LOGGER.debug("Failed to request Q10 map content: %s", ex)

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
        """Render after the low-level DPS source changes."""
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
                self._trace_packet,
                self._map_dps.overlays,
                config=self._config,
            )
        except RoborockException as ex:
            _LOGGER.debug("Failed to render Q10 map packet: %s", ex)
            self._image_content = None

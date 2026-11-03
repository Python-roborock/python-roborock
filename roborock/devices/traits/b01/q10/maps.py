"""Trait for Q10 saved-map list data."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10MapInfo, dpMultiMap
from roborock.devices.traits.common import DpsDataConverter
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import B01Q10MapParserConfig, Q10MapPacket, Q10MapPacketKind
from roborock.map.b01_q10_render import Q10MapOverlays, render_q10_map

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


@dataclass
class Maps(RoborockBase):
    """Saved-map list data from the Q10 DPS stream."""

    multi_map: dpMultiMap | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP})

    detail_packet: Q10MapPacket | None = None
    """Most recently received saved-map preview."""
    detail_map_id: str | None = None
    """Map ID supplied by the preview packet itself."""
    detail_image_content: bytes | None = None
    """Rendered preview PNG, excluded from diagnostic serialization."""

    def as_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """Serialize metadata without binary map grids or PNG bytes."""
        excluded = exclude or set()
        data: dict[str, Any] = {}
        if self.multi_map is not None and "multi_map" not in excluded:
            data["multiMap"] = self.multi_map.as_dict()
        if self.detail_map_id is not None and "detail_map_id" not in excluded:
            data["detailMapId"] = self.detail_map_id
        return data

    @property
    def current_map_id(self) -> str | None:
        """Return the first saved-map ID for a content request, if available."""
        if self.multi_map is None or self.multi_map.op != "list" or self.multi_map.result != 1:
            return None
        return self.multi_map.current_map_id

    @property
    def map_list(self) -> list[Q10MapInfo]:
        """Return a copy of the successfully reported saved-map list."""
        if self.multi_map is None or self.multi_map.op != "list" or self.multi_map.result != 1:
            return []
        return list(self.multi_map.data)


class MapsTrait(Maps, UpdatableTrait):
    """Request and store the Q10 saved-map list."""

    _CONVERTER = DpsDataConverter.from_dataclass(Maps)
    _command: CommandTrait

    def __init__(
        self,
        command: CommandTrait,
        *,
        map_parser_config: B01Q10MapParserConfig,
    ) -> None:
        """Initialize the saved-map list trait."""
        Maps.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)
        self._command = command
        self._map_parser_config = map_parser_config
        self._detail_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Request a new saved-map list from the device."""
        await self._command.send(
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
        )

    async def refresh_detail(self, map_id: str | None = None) -> None:
        """Request a read-only preview for one saved map.

        Returns after publishing. Subscribe with ``add_update_listener`` to
        receive previews separately from the live map. ``detail_map_id`` is
        read from each pushed packet; it is not a request correlation ID.
        """
        if map_id is None:
            map_id = self.current_map_id
        if map_id is None:
            raise RoborockException("Cannot request Q10 saved-map detail before the map list is available")
        if map_id not in {map_info.id for map_info in self.map_list}:
            raise RoborockException(f"Unknown Q10 saved-map ID: {map_id}")
        async with self._detail_lock:
            await self._command.send(
                B01_Q10_DP.COMMON,
                {str(B01_Q10_DP.MULTI_MAP.code): {"op": "select", "id": map_id}},
            )

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Store a successful saved-map list response."""
        response = decoded_dps.get(B01_Q10_DP.MULTI_MAP)
        # DP 61 also carries map-content acknowledgements. Ignore them so they
        # cannot replace a usable map list with an unrelated response.
        if not isinstance(response, dict) or response.get("op") != "list" or response.get("result") != 1:
            return
        super().update_from_dps(decoded_dps)

    def update_from_map_packet(self, packet: Q10MapPacket) -> None:
        """Store and render a pushed saved-map detail packet."""
        if packet.kind is not Q10MapPacketKind.SAVED_MAP_DETAIL:
            raise ValueError(f"Expected a Q10 saved-map detail packet, got {packet.kind.value}")
        self.detail_map_id = str(packet.map_id)
        self.detail_packet = packet
        try:
            self.detail_image_content = render_q10_map(
                packet,
                None,
                Q10MapOverlays(),
                config=self._map_parser_config,
            )
        except RoborockException:
            _LOGGER.debug("Failed to render Q10 saved-map detail", exc_info=True)
            self.detail_image_content = None
        self._notify_update()

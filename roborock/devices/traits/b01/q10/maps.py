"""Trait for Q10 saved-map list data."""

import logging
from dataclasses import dataclass, field
from typing import Any

from roborock.data import RoborockBase
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import dpMultiMap
from roborock.devices.traits.common import DpsDataConverter

from .command import CommandTrait
from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


@dataclass
class Maps(RoborockBase):
    """Saved-map list data from the Q10 DPS stream."""

    multi_map: dpMultiMap | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP})

    @property
    def current_map_id(self) -> str | None:
        """Return the first saved-map ID for a content request, if available."""
        if self.multi_map is None or self.multi_map.op != "list" or self.multi_map.result != 1:
            return None
        return self.multi_map.current_map_id


class MapsTrait(Maps, UpdatableTrait):
    """Request and store the Q10 saved-map list."""

    _CONVERTER = DpsDataConverter.from_dataclass(Maps)
    _command: CommandTrait

    def __init__(self, command: CommandTrait) -> None:
        """Initialize the saved-map list trait."""
        Maps.__init__(self)
        UpdatableTrait.__init__(self, command, _LOGGER)
        self._command = command

    async def refresh(self) -> None:
        """Request a new saved-map list from the device."""
        await self._command.send(
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
        )

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Store a successful saved-map list response."""
        response = decoded_dps.get(B01_Q10_DP.MULTI_MAP)
        # DP 61 also carries map-content acknowledgements. Ignore them so they
        # cannot replace a usable map list with an unrelated response.
        if not isinstance(response, dict) or response.get("op") != "list" or response.get("result") != 1:
            return
        super().update_from_dps(decoded_dps)

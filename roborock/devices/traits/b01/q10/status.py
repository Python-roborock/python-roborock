"""Status trait for Q10 B01 devices."""

import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10Status

from .common import DpsDataConverter, TraitUpdateListener

_LOGGER = logging.getLogger(__name__)

_CONVERTER = DpsDataConverter.from_dataclass(Q10Status)


class StatusTrait(Q10Status, TraitUpdateListener):
    """Trait for managing the status of Q10 Roborock devices.

    This is a thin wrapper around Q10Status that provides the Trait interface.
    The current values reflect the most recently received data from the device.
    New values can be requested through the `Q10PropertiesApi`'s `refresh` method.
    """

    def __init__(self) -> None:
        """Initialize the status trait."""
        super().__init__()
        TraitUpdateListener.__init__(self, logger=_LOGGER)

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Update the trait from raw DPS data."""
        if _CONVERTER.update_from_dps(self, decoded_dps):
            self._notify_update()

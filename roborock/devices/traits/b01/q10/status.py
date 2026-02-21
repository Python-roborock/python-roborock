"""Status trait for Q10 B01 devices."""

import logging
from collections.abc import Callable
from typing import Any

from roborock.callbacks import CallbackList
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_containers import Q10Status

from .common import DpsDataConverter

_LOGGER = logging.getLogger(__name__)

_CONVERTER = DpsDataConverter.from_dataclass(Q10Status)


class StatusTrait(Q10Status):
    """Trait for managing the status of Q10 Roborock devices.

    This is a thin wrapper around Q10Status that provides the Trait interface.
    The current values reflect the most recently received data from the device.
    New values can be requested through the `Q10PropertiesApi`'s `refresh` method.
    """

    def __init__(self) -> None:
        """Initialize the status trait."""
        super().__init__()
        self._update_callbacks: CallbackList[dict[B01_Q10_DP, Any]] = CallbackList(logger=_LOGGER)

    def add_update_listener(self, callback: Callable[[dict[B01_Q10_DP, Any]], None]) -> Callable[[], None]:
        """Register a callback for decoded DPS updates.

        Returns a callable to remove the listener.
        """
        return self._update_callbacks.add_callback(callback)

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Update the trait from raw DPS data."""
        _CONVERTER.update_from_dps(self, decoded_dps)
        self._update_callbacks(decoded_dps)

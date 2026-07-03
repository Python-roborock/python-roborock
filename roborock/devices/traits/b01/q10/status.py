"""Status trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_containers import Q10Status
from roborock.devices.traits.common import DpsDataConverter

from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class StatusTrait(Q10Status, UpdatableTrait):
    """Trait for managing the core status of Q10 Roborock devices.

    This is a thin wrapper around Q10Status that provides the Trait interface.
    The current values reflect the most recently received data from the device.
    New values can be requested through the `Q10PropertiesApi`'s `refresh` method.
    """

    _CONVERTER = DpsDataConverter.from_dataclass(Q10Status)

    def __init__(self) -> None:
        """Initialize the status trait."""
        Q10Status.__init__(self)
        UpdatableTrait.__init__(self, command=None, logger=_LOGGER)

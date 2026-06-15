"""Network information trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_containers import NetworkInfo
from roborock.devices.traits.common import DpsDataConverter

from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class NetworkInfoTrait(NetworkInfo, UpdatableTrait):
    """Trait exposing the device's network information (read-only)."""

    _CONVERTER = DpsDataConverter.from_dataclass(NetworkInfo)

    def __init__(self) -> None:
        """Initialize the network info trait."""
        NetworkInfo.__init__(self)
        UpdatableTrait.__init__(self, command=None, logger=_LOGGER)

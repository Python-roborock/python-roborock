"""Consumable / accessory life trait for Q10 B01 devices."""

import logging

from roborock.data.b01_q10.b01_q10_containers import Consumable
from roborock.devices.traits.common import DpsDataConverter

from .common import UpdatableTrait

_LOGGER = logging.getLogger(__name__)


class ConsumableTrait(Consumable, UpdatableTrait):
    """Trait exposing remaining life of consumables (brushes, filter, sensors)."""

    _CONVERTER = DpsDataConverter.from_dataclass(Consumable)

    def __init__(self) -> None:
        """Initialize the consumable trait."""
        Consumable.__init__(self)
        UpdatableTrait.__init__(self, command=None, logger=_LOGGER)

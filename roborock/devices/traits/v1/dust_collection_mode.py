"""Trait for dust collection mode."""

from roborock.data import DustCollectionMode
from roborock.device_features import is_valid_dock
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DustCollectionModeTrait(DustCollectionMode, common.V1TraitMixin):
    """Trait for dust collection mode."""

    command = RoborockCommand.GET_DUST_COLLECTION_MODE
    requires_dock_type = is_valid_dock

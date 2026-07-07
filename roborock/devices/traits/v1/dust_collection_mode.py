"""Trait for dust collection mode."""

from roborock.data import DustCollectionMode
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


def _supports_dust_collection_mode(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_collectable


class DustCollectionModeTrait(DustCollectionMode, common.V1TraitMixin):
    """Trait for dust collection mode."""

    command = RoborockCommand.GET_DUST_COLLECTION_MODE
    converter = common.DefaultConverter(DustCollectionMode)
    requires_dock_features = _supports_dust_collection_mode

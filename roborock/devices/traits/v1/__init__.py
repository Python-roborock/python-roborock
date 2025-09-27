"""Create traits for V1 devices."""

from dataclasses import dataclass, field, fields

from roborock.containers import HomeData, HomeDataProduct
from roborock.devices.traits import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel

from .clean_summary import CleanSummaryTrait
from .common import V1TraitMixin
from .do_not_disturb import DoNotDisturbTrait
from .maps import MapsTrait
from .status import StatusTrait
from .volume import SoundVolumeTrait

__all__ = [
    "create",
    "PropertiesApi",
    "StatusTrait",
    "DoNotDisturbTrait",
    "CleanSummaryTrait",
    "SoundVolumeTrait",
    "MapsTrait",
]


@dataclass
class PropertiesApi(Trait):
    """Common properties for V1 devices.

    This class holds all the traits that are common across all V1 devices.
    """

    # All v1 devices have these traits
    status: StatusTrait
    dnd: DoNotDisturbTrait
    clean_summary: CleanSummaryTrait
    sound_volume: SoundVolumeTrait
    maps: MapsTrait

    # In the future optional fields can be added below based on supported features

    def __init__(self, product: HomeDataProduct, rpc_channel: V1RpcChannel) -> None:
        """Initialize the V1TraitProps with None values."""
        self.status = StatusTrait(product)
        self.maps = MapsTrait(self.status)

        # This is a hack to allow setting the rpc_channel on all traits. This is
        # used so we can preserve the dataclass behavior when the values in the
        # traits are updated, but still want to allow them to have a reference
        # to the rpc channel for sending commands.
        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is None:
                trait = item.type()
                setattr(self, item.name, trait)
            trait._rpc_channel = rpc_channel


def create(product: HomeDataProduct, rpc_channel: V1RpcChannel) -> PropertiesApi:
    """Create traits for V1 devices."""
    return PropertiesApi(product, rpc_channel)

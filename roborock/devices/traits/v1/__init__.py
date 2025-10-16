"""Create traits for V1 devices."""

import logging
from dataclasses import dataclass, field, fields

from roborock.containers import HomeData, HomeDataProduct
from roborock.devices.cache import Cache
from roborock.devices.traits import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.map.map_parser import MapParserConfig

from .clean_summary import CleanSummaryTrait
from .common import V1TraitMixin
from .consumeable import ConsumableTrait
from .device_features import DeviceFeaturesTrait
from .do_not_disturb import DoNotDisturbTrait
from .home import HomeTrait
from .map_content import MapContentTrait
from .maps import MapsTrait
from .rooms import RoomsTrait
from .status import StatusTrait
from .volume import SoundVolumeTrait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "create",
    "PropertiesApi",
    "StatusTrait",
    "DoNotDisturbTrait",
    "CleanSummaryTrait",
    "SoundVolumeTrait",
    "MapsTrait",
    "MapContentTrait",
    "ConsumableTrait",
    "HomeTrait",
    "DeviceFeaturesTrait",
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
    rooms: RoomsTrait
    maps: MapsTrait
    map_content: MapContentTrait
    consumables: ConsumableTrait
    home: HomeTrait
    device_features: DeviceFeaturesTrait

    # In the future optional fields can be added below based on supported features

    def __init__(
        self,
        product: HomeDataProduct,
        home_data: HomeData,
        rpc_channel: V1RpcChannel,
        mqtt_rpc_channel: V1RpcChannel,
        map_rpc_channel: V1RpcChannel,
        cache: Cache,
        map_parser_config: MapParserConfig | None = None,
    ) -> None:
        """Initialize the V1TraitProps."""
        self.status = StatusTrait(product)
        self.rooms = RoomsTrait(home_data)
        self.maps = MapsTrait(self.status)
        self.map_content = MapContentTrait(map_parser_config)
        self.home = HomeTrait(self.status, self.maps, self.rooms, cache)
        self.device_features = DeviceFeaturesTrait(product.product_nickname)
        # This is a hack to allow setting the rpc_channel on all traits. This is
        # used so we can preserve the dataclass behavior when the values in the
        # traits are updated, but still want to allow them to have a reference
        # to the rpc channel for sending commands.
        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is None:
                trait = item.type()
                setattr(self, item.name, trait)
            # The decorator `@common.mqtt_rpc_channel` means that the trait needs
            # to use the mqtt_rpc_channel (cloud only) instead of the rpc_channel (adaptive)
            if hasattr(trait, "mqtt_rpc_channel"):
                trait._rpc_channel = mqtt_rpc_channel
            elif hasattr(trait, "map_rpc_channel"):
                trait._rpc_channel = map_rpc_channel
            else:
                trait._rpc_channel = rpc_channel


def create(
    product: HomeDataProduct,
    home_data: HomeData,
    rpc_channel: V1RpcChannel,
    mqtt_rpc_channel: V1RpcChannel,
    map_rpc_channel: V1RpcChannel,
    cache: Cache,
    map_parser_config: MapParserConfig | None = None,
) -> PropertiesApi:
    """Create traits for V1 devices."""
    return PropertiesApi(product, home_data, rpc_channel, mqtt_rpc_channel, map_rpc_channel, cache, map_parser_config)

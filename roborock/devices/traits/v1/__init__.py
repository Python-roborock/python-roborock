"""Create traits for V1 devices."""

import logging
from dataclasses import dataclass, field, fields
from typing import get_args

from roborock.containers import HomeData, HomeDataProduct
from roborock.devices.cache import Cache
from roborock.devices.traits import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.map.map_parser import MapParserConfig

from .child_lock import ChildLockTrait
from .clean_summary import CleanSummaryTrait
from .command import CommandTrait
from .common import V1TraitMixin
from .consumeable import ConsumableTrait
from .device_features import DeviceFeaturesTrait
from .do_not_disturb import DoNotDisturbTrait
from .flow_led_status import FlowLedStatusTrait
from .home import HomeTrait
from .led_status import LedStatusTrait
from .map_content import MapContentTrait
from .maps import MapsTrait
from .rooms import RoomsTrait
from .status import StatusTrait
from .valley_electricity_timer import ValleyElectricityTimerTrait
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
    "CommandTrait",
    "ChildLockTrait",
    "FlowLedStatusTrait",
    "LedStatusTrait",
    "ValleyElectricityTimerTrait",
]


@dataclass
class PropertiesApi(Trait):
    """Common properties for V1 devices.

    This class holds all the traits that are common across all V1 devices.
    """

    # All v1 devices have these traits
    status: StatusTrait
    command: CommandTrait
    dnd: DoNotDisturbTrait
    clean_summary: CleanSummaryTrait
    sound_volume: SoundVolumeTrait
    rooms: RoomsTrait
    maps: MapsTrait
    map_content: MapContentTrait
    consumables: ConsumableTrait
    home: HomeTrait
    device_features: DeviceFeaturesTrait

    # Optional features that may not be supported on all devices
    child_lock: ChildLockTrait | None = None
    led_status: LedStatusTrait | None = None
    flow_led_status: FlowLedStatusTrait | None = None
    valley_electricity_timer: ValleyElectricityTimerTrait | None = None

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
        self._rpc_channel = rpc_channel
        self._mqtt_rpc_channel = mqtt_rpc_channel
        self._map_rpc_channel = map_rpc_channel

        self.status = StatusTrait(product)
        self.rooms = RoomsTrait(home_data)
        self.maps = MapsTrait(self.status)
        self.map_content = MapContentTrait(map_parser_config)
        self.home = HomeTrait(self.status, self.maps, self.rooms, cache)
        self.device_features = DeviceFeaturesTrait(product.product_nickname, cache)

        # Dynamically create any traits that need to be populated
        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is None:
                # We exclude optional features and them via discover_features
                if (union_args := get_args(item.type)) is None or len(union_args) > 0:
                    continue
                _LOGGER.debug("Initializing trait %s", item.name)
                trait = item.type()
                setattr(self, item.name, trait)
            # This is a hack to allow setting the rpc_channel on all traits. This is
            # used so we can preserve the dataclass behavior when the values in the
            # traits are updated, but still want to allow them to have a reference
            # to the rpc channel for sending commands.
            trait._rpc_channel = self._get_rpc_channel(trait)

    def _get_rpc_channel(self, trait: V1TraitMixin) -> V1RpcChannel:
        # The decorator `@common.mqtt_rpc_channel` means that the trait needs
        # to use the mqtt_rpc_channel (cloud only) instead of the rpc_channel (adaptive)
        if hasattr(trait, "mqtt_rpc_channel"):
            return self._mqtt_rpc_channel
        elif hasattr(trait, "map_rpc_channel"):
            return self._map_rpc_channel
        else:
            return self._rpc_channel

    async def discover_features(self) -> None:
        """Populate any supported traits that were not initialized in __init__."""
        await self.device_features.refresh()

        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is not None:
                continue
            if (union_args := get_args(item.type)) is None:
                raise ValueError(f"Unexpected non-union type for trait {item.name}: {item.type}")
            if len(union_args) != 2 or type(None) not in union_args:
                raise ValueError(f"Unexpected non-optional type for trait {item.name}: {item.type}")

            # Union args may not be in declared order
            item_type = union_args[0] if union_args[1] is type(None) else union_args[1]
            trait = item_type()
            if not hasattr(trait, "requires_feature"):
                _LOGGER.debug("Trait missing required feature %s", item.name)
                continue
            _LOGGER.debug("Checking for feature %s", trait.requires_feature)
            is_supported = getattr(self.device_features, trait.requires_feature)
            # _LOGGER.debug("Device features: %s", self.device_features)
            if is_supported is None:
                raise ValueError(f"Device feature '{trait.requires_feature}' on trait '{item.name}' is unknown")
            if not is_supported:
                _LOGGER.debug("Disabling optional feature trait %s", item.name)
                continue
            _LOGGER.debug("Enabling optional feature trait %s", item.name)
            setattr(self, item.name, trait)
            trait._rpc_channel = self._get_rpc_channel(trait)


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

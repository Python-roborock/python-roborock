"""Trait for the dock's automatic and manual dust collection."""

from functools import cached_property

from roborock.data import DustCollectionFrequency, RoborockDockDustCollectionFrequencyCode
from roborock.device_features import DeviceFeatures, RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand


def _supports_dust_collection(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_collectable


def get_dust_collection_frequencies(features: DeviceFeatures) -> list[RoborockDockDustCollectionFrequencyCode]:
    """Return the auto-empty settings a device offers.

    Without ``is_auto_collection_2_supported`` (new feature string bit 53) the dock only
    has an on/off switch: ``off`` and ``balanced``, which then means on.
    """
    options = [RoborockDockDustCollectionFrequencyCode.off, RoborockDockDustCollectionFrequencyCode.balanced]
    if features.is_auto_collection_2_supported:
        options.append(RoborockDockDustCollectionFrequencyCode.high)
    return options


class DustCollectionTrait(DustCollectionFrequency, common.V1TraitMixin):
    """Automatic and manual dust collection of a collecting dock.

    The auto-empty setting is also reported as ``auto_dust_collection`` on the device
    status, which only picks up a change made here on its next refresh.

    Verified on the Saros 10R; other collecting docks are assumed to answer the
    same commands.
    """

    command = RoborockCommand.GET_DUST_COLLECTION_SWITCH_STATUS
    converter = common.DefaultConverter(DustCollectionFrequency)
    requires_dock_features = _supports_dust_collection

    def __init__(self, device_feature_trait: DeviceFeaturesTrait) -> None:
        super().__init__()
        self.device_feature_trait = device_feature_trait

    @cached_property
    def frequency_options(self) -> list[RoborockDockDustCollectionFrequencyCode]:
        """Return the auto-empty settings this device offers."""
        return get_dust_collection_frequencies(self.device_feature_trait)

    async def set_frequency(self, frequency: RoborockDockDustCollectionFrequencyCode) -> None:
        """Set the automatic dust collection frequency."""
        if frequency not in self.frequency_options:
            raise RoborockUnsupportedFeature(f"Dust collection frequency {frequency.name} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_DUST_COLLECTION_SWITCH_STATUS, params={"status": frequency.value}
        )
        # Optimistic update to avoid an extra refresh
        self.status = frequency

    async def start_dust_collection(self) -> None:
        """Start a manual dust collection."""
        await self.rpc_channel.send_command(RoborockCommand.APP_START_COLLECT_DUST)

    async def stop_dust_collection(self) -> None:
        """Stop the running dust collection."""
        await self.rpc_channel.send_command(RoborockCommand.APP_STOP_COLLECT_DUST)

"""Trait for the automatic dust collection frequency."""

from roborock.data import DustCollectionFrequency, RoborockDockDustCollectionFrequencyCode
from roborock.device_features import DeviceFeatures, RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_FREQUENCY_OPTIONS = [
    RoborockDockDustCollectionFrequencyCode.off,
    RoborockDockDustCollectionFrequencyCode.balanced,
    RoborockDockDustCollectionFrequencyCode.high,
]


def supports_dust_collection_frequency(device_features: DeviceFeatures, dock_features: RoborockDockFeatures) -> bool:
    """Return whether the app shows the auto-empty frequency for this device.

    The app shows the dock's dust collection page only for a collecting dock on a
    product that supports it (``isCollectDustModeSupported``, not Pearl).
    """
    return dock_features.is_collectable and device_features.is_collect_dust_mode_supported


class DustCollectionFrequencyTrait(DustCollectionFrequency, common.V1TraitMixin):
    """Automatic dust collection frequency of the dock (app: auto-empty frequency).

    The same value is reported as ``auto_dust_collection`` on the device status,
    which only picks up a change made here on its next refresh. Verified on the
    Saros 10R; other collecting docks are assumed to answer the same command.

    Created by ``PropertiesApi`` when ``supports_dust_collection_frequency`` is true.
    """

    command = RoborockCommand.GET_DUST_COLLECTION_SWITCH_STATUS
    converter = common.DefaultConverter(DustCollectionFrequency)

    @property
    def frequency_options(self) -> list[RoborockDockDustCollectionFrequencyCode]:
        """Return the auto-empty frequencies offered by the app."""
        return list(_FREQUENCY_OPTIONS)

    async def set_frequency(self, frequency: RoborockDockDustCollectionFrequencyCode) -> None:
        """Set the automatic dust collection frequency."""
        if frequency not in self.frequency_options:
            raise RoborockUnsupportedFeature(f"Dust collection frequency {frequency.name} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_DUST_COLLECTION_SWITCH_STATUS, params={"status": frequency.value}
        )
        # Optimistic update to avoid an extra refresh
        self.status = frequency

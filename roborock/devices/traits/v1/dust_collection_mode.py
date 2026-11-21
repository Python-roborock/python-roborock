"""Trait for dust collection mode."""

from roborock.data import DustCollectionMode, RoborockDockDustCollectionModeCode
from roborock.device_features import DeviceFeatures, RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_DUST_COLLECTION_MODE_OPTIONS = [
    RoborockDockDustCollectionModeCode.smart,
    RoborockDockDustCollectionModeCode.light,
    RoborockDockDustCollectionModeCode.balanced,
    RoborockDockDustCollectionModeCode.max,
]


def supports_dust_collection_mode(device_features: DeviceFeatures, dock_features: RoborockDockFeatures) -> bool:
    """Return whether the app shows the dust collection mode for this device.

    The app shows the dock's dust collection page only for a collecting dock on a
    product that supports it (``isCollectDustModeSupported``, not Pearl), and loads
    the mode only with ``isDustCollectionSettingSupported``.
    """
    return (
        dock_features.is_collectable
        and device_features.is_collect_dust_mode_supported
        and device_features.is_dust_collection_setting_supported
    )


class DustCollectionModeTrait(DustCollectionMode, common.V1TraitMixin):
    """Trait for the dock dust collection mode.

    ``set_dust_collection_mode`` changes how strongly the dock empties the
    dustbin. Manual dust collection is on ``DustCollectionTrait``, which
    every collecting dock has.

    Created by ``PropertiesApi`` when ``supports_dust_collection_mode`` is true.
    """

    command = RoborockCommand.GET_DUST_COLLECTION_MODE
    converter = common.DefaultConverter(DustCollectionMode)

    @property
    def dust_collection_mode_options(self) -> list[RoborockDockDustCollectionModeCode]:
        """Return the dust collection modes offered by the app."""
        return list(_DUST_COLLECTION_MODE_OPTIONS)

    async def set_dust_collection_mode(self, mode: RoborockDockDustCollectionModeCode) -> None:
        """Set the dust collection mode."""
        if mode not in self.dust_collection_mode_options:
            raise RoborockUnsupportedFeature(f"Dust collection mode {mode.name} is not supported")
        await self.rpc_channel.send_command(RoborockCommand.SET_DUST_COLLECTION_MODE, params={"mode": mode.value})
        # Optimistic update to avoid an extra refresh
        self.mode = mode

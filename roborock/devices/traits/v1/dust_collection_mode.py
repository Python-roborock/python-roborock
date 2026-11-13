"""Trait for dust collection mode."""

from roborock.data import DustCollectionMode, RoborockDockDustCollectionModeCode
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_DUST_COLLECTION_MODE_OPTIONS = [
    RoborockDockDustCollectionModeCode.smart,
    RoborockDockDustCollectionModeCode.light,
    RoborockDockDustCollectionModeCode.balanced,
    RoborockDockDustCollectionModeCode.max,
]


def _supports_dust_collection_mode(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_collectable


class DustCollectionModeTrait(DustCollectionMode, common.V1TraitMixin):
    """Trait for the dock dust collection mode.

    ``set_dust_collection_mode`` changes how strongly the dock empties the
    dustbin. ``start_dust_collection`` and ``stop_dust_collection`` control a
    manual dust collection directly.
    """

    command = RoborockCommand.GET_DUST_COLLECTION_MODE
    converter = common.DefaultConverter(DustCollectionMode)
    requires_dock_features = _supports_dust_collection_mode

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

    async def start_dust_collection(self) -> None:
        """Start a manual dust collection."""
        await self.rpc_channel.send_command(RoborockCommand.APP_START_COLLECT_DUST)

    async def stop_dust_collection(self) -> None:
        """Stop the running dust collection."""
        await self.rpc_channel.send_command(RoborockCommand.APP_STOP_COLLECT_DUST)

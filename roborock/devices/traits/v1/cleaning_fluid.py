"""Trait for the cleaning fluid auto-delivery of the dock."""

from roborock.data import CleaningFluidDelivery, RoborockDockCleaningFluidCode
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_CLEANING_FLUID_OPTIONS = [
    RoborockDockCleaningFluidCode.off,
    RoborockDockCleaningFluidCode.standard,
    RoborockDockCleaningFluidCode.large,
]


def _supports_cleaning_fluid(dock_features: RoborockDockFeatures) -> bool:
    return dock_features.is_clean_fluid_auto_delivery_supported


class CleaningFluidTrait(CleaningFluidDelivery, common.V1TraitMixin):
    """Amount of cleaning fluid the dock adds automatically (app: cleaning fluid auto-delivery).

    The large amount is wire code 3; code 2 is not used by the app.
    """

    command = RoborockCommand.GET_AUTO_DELIVERY_CLEANING_FLUID
    converter = common.DefaultConverter(CleaningFluidDelivery)
    requires_dock_features = _supports_cleaning_fluid

    @property
    def cleaning_fluid_options(self) -> list[RoborockDockCleaningFluidCode]:
        """Return the cleaning fluid amounts offered by the app."""
        return list(_CLEANING_FLUID_OPTIONS)

    async def set_cleaning_fluid(self, mode: RoborockDockCleaningFluidCode) -> None:
        """Set the cleaning fluid auto-delivery amount."""
        if mode not in self.cleaning_fluid_options:
            raise RoborockUnsupportedFeature(f"Cleaning fluid amount {mode.name} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_AUTO_DELIVERY_CLEANING_FLUID, params={"status": mode.value}
        )
        # Optimistic update to avoid an extra refresh
        self.status = mode

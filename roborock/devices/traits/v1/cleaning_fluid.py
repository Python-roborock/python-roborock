"""Trait for the cleaning fluid auto-delivery of the dock."""

from roborock.data import CleanFluidStatus, CleaningFluidDelivery, RoborockDockCleaningFluidCode, RoborockDockTypeCode
from roborock.device_features import RoborockDockFeatures
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand


def supports_cleaning_fluid(
    fluid_delivery_supported: bool,
    dock_features: RoborockDockFeatures,
    fluid_status: CleanFluidStatus | None,
) -> bool:
    """Return whether the cleaning fluid setting is offered.

    The robot must report a cleaning fluid container, and either the robot supports cleaning
    fluid delivery (``is_clean_fluid_delivery_supported``) or the dock does auto-delivery.
    Shell 4S docks have several cleaning fluids and their own controls.
    """
    if fluid_status is None:
        return False
    if dock_features.dock_type == RoborockDockTypeCode.shell_4s_dock:
        return False
    return fluid_delivery_supported or dock_features.is_clean_fluid_auto_delivery_supported


class CleaningFluidTrait(CleaningFluidDelivery, common.V1TraitMixin):
    """Amount of cleaning fluid the dock adds automatically (app: cleaning fluid auto-delivery).

    Robots with cleaning fluid delivery offer off, standard and large (wire code 3); others
    only switch it on (standard) or off. Wire code 2 is not used.
    """

    command = RoborockCommand.GET_AUTO_DELIVERY_CLEANING_FLUID
    converter = common.DefaultConverter(CleaningFluidDelivery)

    def __init__(self, device_feature_trait: DeviceFeaturesTrait) -> None:
        super().__init__()
        self.device_feature_trait = device_feature_trait

    @property
    def cleaning_fluid_options(self) -> list[RoborockDockCleaningFluidCode]:
        """Return the cleaning fluid amounts the robot offers."""
        options = [RoborockDockCleaningFluidCode.off, RoborockDockCleaningFluidCode.standard]
        if self.device_feature_trait.is_clean_fluid_delivery_supported:
            options.append(RoborockDockCleaningFluidCode.large)
        return options

    async def set_cleaning_fluid(self, mode: RoborockDockCleaningFluidCode) -> None:
        """Set the cleaning fluid auto-delivery amount."""
        if mode not in self.cleaning_fluid_options:
            raise RoborockUnsupportedFeature(f"Cleaning fluid amount {mode.name} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_AUTO_DELIVERY_CLEANING_FLUID, params={"status": mode.value}
        )
        # Optimistic update to avoid an extra refresh
        self.status = mode

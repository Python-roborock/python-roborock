"""Trait for the carpet behaviour of V1 vacuums."""

import logging
from dataclasses import dataclass

from roborock.data import RoborockBase
from roborock.data.v1 import CarpetCleanMode, CarpetMode, SwitchStatus
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockException, RoborockParsingException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)


@dataclass
class CarpetCleanModeState(RoborockBase):
    """Carpet state read from the robot."""

    carpet_clean_mode: CarpetCleanMode = CarpetCleanMode.unknown
    carpet_first: bool = False
    cross_carpet: bool = False


class CarpetCleanModeTrait(CarpetCleanModeState, common.V1TraitMixin):
    """Trait for reading and setting the carpet clean mode."""

    command = RoborockCommand.GET_CARPET_CLEAN_MODE
    requires_feature = "is_carpet_clean_mode_supported"

    def __init__(self, device_features: DeviceFeaturesTrait) -> None:
        super().__init__()
        common.V1TraitMixin.__init__(self)
        self._device_features = device_features

    @property
    def mode(self) -> CarpetMode | None:
        """The carpet mode, or None when the robot reports an unknown one."""
        if self.cross_carpet:
            return CarpetMode.CROSS
        return {
            CarpetCleanMode.avoid: CarpetMode.AVOID,
            CarpetCleanMode.self_adaption: CarpetMode.VACUUM_ONLY,
            CarpetCleanMode.vac_and_mop: CarpetMode.VAC_AND_MOP,
            CarpetCleanMode.dynamic_adaption: CarpetMode.VACUUM_ONLY,
        }.get(self.carpet_clean_mode)

    @property
    def options(self) -> list[CarpetMode]:
        """The carpet modes this robot supports."""
        features = self._device_features
        options = [CarpetMode.AVOID, CarpetMode.VAC_AND_MOP]
        if features.is_self_adaption_carpet_supported or features.is_dynamic_adaption_carpet_supported:
            options.append(CarpetMode.VACUUM_ONLY)
        if features.is_carpet_custom_clean_supported:
            options.append(CarpetMode.CROSS)
        return options

    @property
    def vacuum_only_settings_available(self) -> bool:
        """True in Vacuum Only, the only mode where the robot accepts carpet first and side brush lift."""
        return self.mode is CarpetMode.VACUUM_ONLY

    async def refresh(self) -> None:
        """Read the clean mode, then the carpet first and cross flags from the status."""
        response = await self.rpc_channel.send_command(self.command)
        try:
            clean_mode = CarpetCleanMode(response[0]["carpet_clean_mode"])
        except (IndexError, KeyError, TypeError, ValueError) as err:
            raise RoborockParsingException(
                trait_name=type(self).__name__, command=self.command, payload=response, inner_error=err
            ) from err
        self.carpet_clean_mode = clean_mode
        try:
            status = await self.rpc_channel.send_command(RoborockCommand.GET_PROP, params=["get_status"])
            switch_status = SwitchStatus.from_dict(status[0])
        except (RoborockException, IndexError, KeyError, TypeError, ValueError) as err:
            _LOGGER.debug("Could not read the carpet switch status: %s", err)
            return
        self.carpet_first = switch_status.carpet_first
        self.cross_carpet = switch_status.cross_carpet

    async def set_mode(self, mode: CarpetMode) -> None:
        """Set the carpet mode and refresh the state.

        Only the mode and the cross flag are written; carpet boost and deep clean are left as they are.
        Raises RoborockUnsupportedFeature if the robot does not offer the mode.
        """
        if mode not in self.options:
            raise RoborockUnsupportedFeature(f"Carpet mode {mode} is not supported by this device")
        features = self._device_features
        if mode is CarpetMode.CROSS:
            await self._set_cross(True)
        elif mode is CarpetMode.VACUUM_ONLY:
            adaption = (
                CarpetCleanMode.dynamic_adaption
                if features.is_dynamic_adaption_carpet_supported
                else CarpetCleanMode.self_adaption
            )
            await self._set_clean_mode(adaption)
            # Mode 3 leaves cross on (Saros 10R), so clear it.
            if features.is_carpet_custom_clean_supported:
                await self._set_cross(False)
        else:
            clean_mode = CarpetCleanMode.avoid if mode is CarpetMode.AVOID else CarpetCleanMode.vac_and_mop
            await self._set_clean_mode(clean_mode)
        await self.refresh()

    async def _set_clean_mode(self, clean_mode: CarpetCleanMode) -> None:
        await self.rpc_channel.send_command(
            RoborockCommand.SET_CARPET_CLEAN_MODE, params={"carpet_clean_mode": clean_mode.value}
        )

    async def _set_cross(self, enabled: bool) -> None:
        await self.rpc_channel.send_command(
            RoborockCommand.APP_SET_CROSS_CARPET_CLEANING_STATUS, params={"status": int(enabled)}
        )

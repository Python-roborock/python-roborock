"""Trait for the carpet behaviour of V1 vacuums."""

import logging
from dataclasses import dataclass

from roborock.data import RoborockBase
from roborock.data.v1 import CarpetCleanMode, CarpetMode, SwitchStatus
from roborock.devices.traits.v1 import common
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.exceptions import RoborockException, RoborockParsingException
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)


@dataclass
class CarpetCleanModeState(RoborockBase):
    """Carpet state read from the robot."""

    carpet_clean_mode: CarpetCleanMode = CarpetCleanMode.unknown
    carpet_first: bool = False
    cross_carpet: bool = False


class CarpetCleanModeTrait(CarpetCleanModeState, common.V1TraitMixin):
    """Trait for reading how the robot treats carpets."""

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

"""Trait for the carpet boost setting."""

from dataclasses import asdict, replace

from roborock.data import CarpetBoost, CarpetBoostSettings
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand


class CarpetBoostConverter(common.V1TraitDataConverter):
    """Converter for CarpetBoostSettings."""

    def convert(self, response: common.V1ResponseData) -> CarpetBoostSettings:
        """Parse the response from the device into a CarpetBoostSettings."""
        if isinstance(response, list):
            if not response:
                raise ValueError("Empty CarpetBoostSettings response")
            response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"Unexpected CarpetBoostSettings response format: {response!r}")
        settings = CarpetBoostSettings.from_dict(response)
        if None in asdict(settings).values():
            raise ValueError(f"Incomplete CarpetBoostSettings response: {response!r}")
        return settings


_CONVERTER = CarpetBoostConverter()


class CarpetBoostTrait(CarpetBoost, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for turning carpet boost on or off.

    The device expects its motor tuning values with every write, so they are
    kept privately from the last read and sent back unchanged.
    """

    command = RoborockCommand.GET_CARPET_MODE
    converter = _CONVERTER
    requires_feature = "is_carpet_supported"

    def __init__(self) -> None:
        super().__init__()
        common.V1TraitMixin.__init__(self)
        self._settings: CarpetBoostSettings | None = None

    @property
    def is_on(self) -> bool:
        """Return whether carpet boost is enabled."""
        return self.enabled == 1

    async def refresh(self) -> None:
        """Refresh the boost state and the tuning values needed for writes."""
        settings = await self._read_settings()
        self._settings = settings
        self.enabled = settings.enable

    async def enable(self) -> None:
        """Enable carpet boost."""
        await self._set_enable(1)

    async def disable(self) -> None:
        """Disable carpet boost."""
        await self._set_enable(0)

    async def _read_settings(self) -> CarpetBoostSettings:
        response = await self.rpc_channel.send_command(self.command)
        try:
            return _CONVERTER.convert(response)
        except (TypeError, ValueError) as err:
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=self.command,
                payload=response,
                inner_error=err,
            ) from err

    async def _set_enable(self, enable: int) -> None:
        current = self._settings if self._settings is not None else await self._read_settings()
        settings = replace(current, enable=enable)
        await self.rpc_channel.send_command(RoborockCommand.SET_CARPET_MODE, params=[asdict(settings)])
        # Optimistic update to avoid an extra refresh
        self._settings = settings
        self.enabled = enable

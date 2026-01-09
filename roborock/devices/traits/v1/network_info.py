"""Trait for device network information."""

from __future__ import annotations

import logging
from dataclasses import fields

from roborock.data import NetworkInfo
from roborock.devices.cache import DeviceCache
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)


class NetworkInfoTrait(NetworkInfo, common.V1TraitMixin):
    """Trait for device network information.

    This trait will always prefer reading from the cache if available. This
    information is usually already fetched when creating the device local
    connection, so reading from the cache avoids an unnecessary RPC call.
    However, we have the fallback to reading from the device if the cache is
    not populated for some reason.
    """

    command = RoborockCommand.GET_NETWORK_INFO

    def __init__(self, device_uid: str, device_cache: DeviceCache) -> None:  # pylint: disable=super-init-not-called
        """Initialize the trait."""
        self._device_uid = device_uid
        self._device_cache = device_cache
        self.ip = ""

    async def refresh(self) -> None:
        """Refresh the network info from the cache."""

        device_cache_data = await self._device_cache.get()
        if device_cache_data.network_info:
            _LOGGER.debug("Using cached network info for device %s", self._device_uid)
            self._update_trait_values(device_cache_data.network_info)
            return

        # Load from device if not in cache
        _LOGGER.debug("No cached network info for device %s, fetching from device", self._device_uid)
        await super().refresh()

        # Update the cache with the new network info
        device_cache_data = await self._device_cache.get()
        # Create a pure NetworkInfo instance without runtime objects
        network_info_data = NetworkInfo(ip="")
        for field in fields(NetworkInfo):
            setattr(network_info_data, field.name, getattr(self, field.name))
        device_cache_data.network_info = network_info_data
        await self._device_cache.set(device_cache_data)

    def _parse_response(self, response: common.V1ResponseData) -> NetworkInfo:
        """Parse the response from the device into a NetworkInfo."""
        if not isinstance(response, dict):
            raise ValueError(f"Unexpected NetworkInfoTrait response format: {response!r}")
        return NetworkInfo.from_dict(response)

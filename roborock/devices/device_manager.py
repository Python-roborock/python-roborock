"""Module for discovering Roborock devices."""

import logging
from collections.abc import Awaitable, Callable

from roborock.containers import (
    HomeData,
    HomeDataDevice,
    HomeDataProduct,
    UserData,
)
from roborock.devices.device import RoborockDevice
from roborock.web_api import RoborockApiClient

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "create_device_manager",
    "create_home_data_api",
    "DeviceManager",
    "HomeDataApi",
    "DeviceCreator",
]


HomeDataApi = Callable[[], Awaitable[HomeData]]
DeviceCreator = Callable[[HomeDataDevice, HomeDataProduct], RoborockDevice]


class DeviceManager:
    """Central manager for Roborock device discovery and connections."""

    def __init__(
        self,
        home_data_api: HomeDataApi,
        device_creator: DeviceCreator,
    ) -> None:
        """Initialize the DeviceManager with user data and optional cache storage."""
        self._home_data_api = home_data_api
        self._device_creator = device_creator
        self._devices: dict[str, RoborockDevice] = {}

    async def discover_devices(self) -> list[RoborockDevice]:
        """Discover all devices for the logged-in user."""
        home_data = await self._home_data_api()
        device_products = home_data.device_products
        _LOGGER.debug("Discovered %d devices %s", len(device_products), home_data)

        self._devices = {
            duid: self._device_creator(device, product) for duid, (device, product) in device_products.items()
        }
        return list(self._devices.values())

    async def get_device(self, duid: str) -> RoborockDevice | None:
        """Get a specific device by DUID."""
        return self._devices.get(duid)

    async def get_devices(self) -> list[RoborockDevice]:
        """Get all discovered devices."""
        return list(self._devices.values())


def create_home_data_api(email: str, user_data: UserData) -> HomeDataApi:
    """Create a home data API wrapper.

    This function creates a wrapper around the Roborock API client to fetch
    home data for the user.
    """

    client = RoborockApiClient(email, user_data)

    async def home_data_api() -> HomeData:
        return await client.get_home_data(user_data)

    return home_data_api


async def create_device_manager(user_data: UserData, home_data_api: HomeDataApi) -> DeviceManager:
    """Convenience function to create and initialize a DeviceManager.

    The Home Data is fetched using the provided home_data_api callable which
    is exposed this way to allow for swapping out other implementations to
    include caching or other optimizations.
    """

    def device_creator(device: HomeDataDevice, product: HomeDataProduct) -> RoborockDevice:
        return RoborockDevice(user_data, device, product)

    manager = DeviceManager(home_data_api, device_creator)
    await manager.discover_devices()
    return manager

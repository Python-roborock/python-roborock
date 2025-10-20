"""Module for discovering Roborock devices."""

import asyncio
import enum
import logging
from collections.abc import Awaitable, Callable

import aiohttp

from roborock.data import (
    HomeData,
    HomeDataDevice,
    HomeDataProduct,
    UserData,
)
from roborock.devices.device import RoborockDevice
from roborock.map.map_parser import MapParserConfig
from roborock.mqtt.roborock_session import create_lazy_mqtt_session
from roborock.mqtt.session import MqttSession
from roborock.protocol import create_mqtt_params
from roborock.web_api import RoborockApiClient

from .cache import Cache, NoCache
from .channel import Channel
from .mqtt_channel import create_mqtt_channel
from .traits import Trait, a01, b01, v1
from .v1_channel import create_v1_channel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "create_device_manager",
    "create_home_data_api",
    "DeviceManager",
]


HomeDataApi = Callable[[], Awaitable[HomeData]]
DeviceCreator = Callable[[HomeData, HomeDataDevice, HomeDataProduct], RoborockDevice]


class DeviceVersion(enum.StrEnum):
    """Enum for device versions."""

    V1 = "1.0"
    A01 = "A01"
    B01 = "B01"
    UNKNOWN = "unknown"


class DeviceManager:
    """Central manager for Roborock device discovery and connections."""

    def __init__(
        self,
        home_data_api: HomeDataApi,
        device_creator: DeviceCreator,
        mqtt_session: MqttSession,
        cache: Cache,
    ) -> None:
        """Initialize the DeviceManager with user data and optional cache storage.

        This takes ownership of the MQTT session and will close it when the manager is closed.
        """
        self._home_data_api = home_data_api
        self._cache = cache
        self._device_creator = device_creator
        self._devices: dict[str, RoborockDevice] = {}
        self._mqtt_session = mqtt_session

    async def discover_devices(self) -> list[RoborockDevice]:
        """Discover all devices for the logged-in user."""
        cache_data = await self._cache.get()
        if not cache_data.home_data:
            _LOGGER.debug("No cached home data found, fetching from API")
            cache_data.home_data = await self._home_data_api()
            await self._cache.set(cache_data)
        home_data = cache_data.home_data

        device_products = home_data.device_products
        _LOGGER.debug("Discovered %d devices %s", len(device_products), home_data)

        # These are connected serially to avoid overwhelming the MQTT broker
        new_devices = {}
        for duid, (device, product) in device_products.items():
            if duid in self._devices:
                continue
            new_device = self._device_creator(home_data, device, product)
            await new_device.connect()
            new_devices[duid] = new_device

        self._devices.update(new_devices)
        return list(self._devices.values())

    async def get_device(self, duid: str) -> RoborockDevice | None:
        """Get a specific device by DUID."""
        return self._devices.get(duid)

    async def get_devices(self) -> list[RoborockDevice]:
        """Get all discovered devices."""
        return list(self._devices.values())

    async def close(self) -> None:
        """Close all MQTT connections and clean up resources."""
        tasks = [device.close() for device in self._devices.values()]
        self._devices.clear()
        tasks.append(self._mqtt_session.close())
        await asyncio.gather(*tasks)


def create_home_data_api(
    email: str, user_data: UserData, base_url: str | None = None, session: aiohttp.ClientSession | None = None
) -> HomeDataApi:
    """Create a home data API wrapper.

    This function creates a wrapper around the Roborock API client to fetch
    home data for the user.
    """
    # Note: This will auto discover the API base URL. This can be improved
    # by caching this next to `UserData` if needed to avoid unnecessary API calls.
    client = RoborockApiClient(username=email, base_url=base_url, session=session)

    return create_home_data_from_api_client(client, user_data)


def create_home_data_from_api_client(client: RoborockApiClient, user_data: UserData) -> HomeDataApi:
    """Create a home data API wrapper from an existing API client."""

    async def home_data_api() -> HomeData:
        return await client.get_home_data_v3(user_data)

    return home_data_api


async def create_device_manager(
    user_data: UserData,
    home_data_api: HomeDataApi,
    cache: Cache | None = None,
    map_parser_config: MapParserConfig | None = None,
) -> DeviceManager:
    """Convenience function to create and initialize a DeviceManager.

    The Home Data is fetched using the provided home_data_api callable which
    is exposed this way to allow for swapping out other implementations to
    include caching or other optimizations.
    """
    if cache is None:
        cache = NoCache()

    mqtt_params = create_mqtt_params(user_data.rriot)
    mqtt_session = await create_lazy_mqtt_session(mqtt_params)

    def device_creator(home_data: HomeData, device: HomeDataDevice, product: HomeDataProduct) -> RoborockDevice:
        channel: Channel
        trait: Trait
        match device.pv:
            case DeviceVersion.V1:
                channel = create_v1_channel(user_data, mqtt_params, mqtt_session, device, cache)
                trait = v1.create(
                    product,
                    home_data,
                    channel.rpc_channel,
                    channel.mqtt_rpc_channel,
                    channel.map_rpc_channel,
                    cache,
                    map_parser_config=map_parser_config,
                )
            case DeviceVersion.A01:
                channel = create_mqtt_channel(user_data, mqtt_params, mqtt_session, device)
                trait = a01.create(product, channel)
            case DeviceVersion.B01:
                channel = create_mqtt_channel(user_data, mqtt_params, mqtt_session, device)
                trait = b01.create(channel)
            case _:
                raise NotImplementedError(f"Device {device.name} has unsupported version {device.pv}")
        return RoborockDevice(device, product, channel, trait)

    manager = DeviceManager(home_data_api, device_creator, mqtt_session=mqtt_session, cache=cache)
    await manager.discover_devices()
    return manager

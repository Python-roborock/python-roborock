"""Module for discovering Roborock devices."""

import asyncio
import enum
import logging
from collections.abc import Callable
from dataclasses import dataclass

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
from roborock.web_api import RoborockApiClient, UserWebApiClient

from .cache import Cache, DeviceCache, NoCache
from .channel import Channel
from .mqtt_channel import create_mqtt_channel
from .traits import Trait, a01, b01, v1
from .v1_channel import create_v1_channel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "create_device_manager",
    "UserParams",
    "DeviceManager",
]


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
        web_api: UserWebApiClient,
        device_creator: DeviceCreator,
        mqtt_session: MqttSession,
        cache: Cache,
    ) -> None:
        """Initialize the DeviceManager with user data and optional cache storage.

        This takes ownership of the MQTT session and will close it when the manager is closed.
        """
        self._web_api = web_api
        self._cache = cache
        self._device_creator = device_creator
        self._devices: dict[str, RoborockDevice] = {}
        self._mqtt_session = mqtt_session

    async def discover_devices(self) -> list[RoborockDevice]:
        """Discover all devices for the logged-in user."""
        cache_data = await self._cache.get()
        if not cache_data.home_data:
            _LOGGER.debug("No cached home data found, fetching from API")
            cache_data.home_data = await self._web_api.get_home_data()
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
            new_device.start_connect()
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


@dataclass
class UserParams:
    """Parameters for creating a new session with Roborock devices.

    These parameters include the username, user data for authentication,
    and an optional base URL for the Roborock API. The `user_data` and `base_url`
    parameters are obtained from `RoborockApiClient` during the login process.
    """

    username: str
    """The username (email) used for logging in."""

    user_data: UserData
    """This is the user data containing authentication information."""

    base_url: str | None = None
    """Optional base URL for the Roborock API.

    This is used to speed up connection times by avoiding the need to
    discover the API base URL each time. If not provided, the API client
    will attempt to discover it automatically which may take multiple requests.
    """


def create_web_api_wrapper(
    user_params: UserParams,
    *,
    cache: Cache | None = None,
    session: aiohttp.ClientSession | None = None,
) -> UserWebApiClient:
    """Create a home data API wrapper from an existing API client."""

    # Note: This will auto discover the API base URL. This can be improved
    # by caching this next to `UserData` if needed to avoid unnecessary API calls.
    client = RoborockApiClient(username=user_params.username, base_url=user_params.base_url, session=session)

    return UserWebApiClient(client, user_params.user_data)


async def create_device_manager(
    user_params: UserParams,
    *,
    cache: Cache | None = None,
    map_parser_config: MapParserConfig | None = None,
    session: aiohttp.ClientSession | None = None,
) -> DeviceManager:
    """Convenience function to create and initialize a DeviceManager.

    Args:
        user_params: Parameters for creating the user session.
        cache: Optional cache implementation to use for caching device data.
        map_parser_config: Optional configuration for parsing maps.
        session: Optional aiohttp ClientSession to use for HTTP requests.

    Returns:
        An initialized DeviceManager with discovered devices.
    """
    if cache is None:
        cache = NoCache()

    web_api = create_web_api_wrapper(user_params, session=session, cache=cache)
    user_data = user_params.user_data

    mqtt_params = create_mqtt_params(user_data.rriot)
    mqtt_session = await create_lazy_mqtt_session(mqtt_params)

    def device_creator(home_data: HomeData, device: HomeDataDevice, product: HomeDataProduct) -> RoborockDevice:
        channel: Channel
        trait: Trait
        device_cache: DeviceCache = DeviceCache(device.duid, cache)
        match device.pv:
            case DeviceVersion.V1:
                channel = create_v1_channel(user_data, mqtt_params, mqtt_session, device, device_cache)
                trait = v1.create(
                    device.duid,
                    product,
                    home_data,
                    channel.rpc_channel,
                    channel.mqtt_rpc_channel,
                    channel.map_rpc_channel,
                    web_api,
                    device_cache=device_cache,
                    map_parser_config=map_parser_config,
                )
            case DeviceVersion.A01:
                channel = create_mqtt_channel(user_data, mqtt_params, mqtt_session, device)
                trait = a01.create(product, channel)
            case DeviceVersion.B01:
                channel = create_mqtt_channel(user_data, mqtt_params, mqtt_session, device)
                if "ss" in product.model.split(".")[-1]:
                    raise NotImplementedError(
                        f"Device {device.name} has unsupported version B01_{product.model.strip('.')[-1]}"
                    )
                elif "sc" in product.model.split(".")[-1]:
                    # Q7 devices start with 'sc' in their model naming.
                    trait = b01.q7.create(channel)
                else:
                    raise NotImplementedError(f"Device {device.name} has unsupported B01 model: {product.model}")
            case _:
                raise NotImplementedError(f"Device {device.name} has unsupported version {device.pv}")
        return RoborockDevice(device, product, channel, trait)

    manager = DeviceManager(web_api, device_creator, mqtt_session=mqtt_session, cache=cache)
    await manager.discover_devices()
    return manager

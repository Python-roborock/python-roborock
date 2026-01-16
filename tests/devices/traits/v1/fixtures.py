"""Fixtures for V1 trait tests."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from roborock.data import HomeData, HomeDataDevice, HomeDataProduct, RoborockDockTypeCode, S7MaxVStatus, UserData
from roborock.devices.cache import Cache, DeviceCache, InMemoryCache
from roborock.devices.device import RoborockDevice
from roborock.devices.traits import v1
from tests import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
STATUS = S7MaxVStatus.from_dict(mock_data.STATUS)


@pytest.fixture(autouse=True, name="channel")
def device_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mock_rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mock_mqtt_rpc_channel")
def mqtt_rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mock_map_rpc_channel")
def map_rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="web_api_client")
def web_api_client_fixture() -> AsyncMock:
    """Fixture to set up the web API client for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="roborock_cache")
def roborock_cache_fixture() -> Cache:
    """Fixture to provide a NoCache instance for tests."""
    return InMemoryCache()


@pytest.fixture(autouse=True, name="device_cache")
def device_cache_fixture(roborock_cache: Cache) -> DeviceCache:
    """Fixture to provide a DeviceCache instance for tests."""
    return DeviceCache(HOME_DATA.devices[0].duid, roborock_cache)


@pytest.fixture(name="device_info")
def device_info_fixture() -> HomeDataDevice:
    """Fixture to provide a DeviceInfo instance for tests."""
    return HOME_DATA.devices[0]


@pytest.fixture(name="products")
def products_fixture() -> list[HomeDataProduct]:
    """Fixture to provide a Product instance for tests."""
    return [HomeDataProduct.from_dict(product) for product in mock_data.PRODUCTS.values()]


@pytest.fixture(autouse=True, name="device")
def device_fixture(
    channel: AsyncMock,
    mock_rpc_channel: AsyncMock,
    mock_mqtt_rpc_channel: AsyncMock,
    mock_map_rpc_channel: AsyncMock,
    web_api_client: AsyncMock,
    device_cache: DeviceCache,
    device_info: HomeDataDevice,
    products: list[HomeDataProduct],
) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    product = next(filter(lambda product: product.id == device_info.product_id, products))
    return RoborockDevice(
        device_info=device_info,
        product=product,
        channel=channel,
        trait=v1.create(
            device_info.duid,
            product,
            HOME_DATA,
            mock_rpc_channel,
            mock_mqtt_rpc_channel,
            mock_map_rpc_channel,
            web_api_client,
            device_cache=device_cache,
        ),
    )


@pytest.fixture(name="dock_type_code", autouse=True)
def dock_type_code_fixture(request: pytest.FixtureRequest) -> RoborockDockTypeCode | None:
    """Fixture to provide the dock type code for parameterized tests."""
    return RoborockDockTypeCode.s7_max_ultra_dock


@pytest.fixture(name="mock_app_get_init_status")
def mock_app_get_init_status_fixture(device_info: HomeDataDevice, products: list[HomeDataProduct]) -> dict[str, Any]:
    """Fixture to provide a DeviceFeaturesInfo instance for tests."""
    product = next(filter(lambda product: product.id == device_info.product_id, products))
    if not product:
        raise ValueError(f"Product {device_info.product_id} not found")
    return mock_data.APP_GET_INIT_STATUS


@pytest.fixture(autouse=True)
async def discover_features_fixture(
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
    mock_app_get_init_status: dict[str, Any],
    dock_type_code: RoborockDockTypeCode | None,
) -> None:
    """Fixture to handle device feature discovery."""
    assert device.v1_properties
    mock_rpc_channel.send_command.side_effect = [
        [mock_app_get_init_status],
        {
            **mock_data.STATUS,
            "dock_type": dock_type_code,
        },
    ]
    # Connecting triggers device discovery
    await device.connect()
    assert device.v1_properties.status.dock_type == dock_type_code
    mock_rpc_channel.send_command.reset_mock()

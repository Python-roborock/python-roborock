"""Tests for the DeviceManager class."""

import asyncio
from collections.abc import Generator
from dataclasses import replace
from typing import Any
from unittest.mock import Mock, patch

import pytest
import syrupy

from roborock.data import HomeData, UserData
from roborock.data.containers import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.devices.cache import InMemoryCache
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import UserParams, create_device_manager, create_web_api_wrapper
from roborock.exceptions import RoborockException, RoborockInvalidCredentials
from roborock.testing import FakeRoborockCloud, Q10VacuumSimulator, V1VacuumSimulator
from tests import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
USER_PARAMS = UserParams(username="test_user", user_data=USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
NETWORK_INFO = mock_data.NETWORK_INFO


@pytest.fixture(name="cloud")
def cloud_fixture() -> FakeRoborockCloud:
    """Fixture to set up FakeRoborockCloud."""
    return FakeRoborockCloud(user_data=USER_DATA)


@pytest.fixture(name="fake_device")
def fake_device_fixture(cloud: FakeRoborockCloud) -> V1VacuumSimulator:
    """Fixture to set up a stateful V1VacuumSimulator registered to the cloud."""
    device = V1VacuumSimulator(
        duid="abc123",
        device_info=HOME_DATA.devices[0],
        product=HOME_DATA.products[0],
    )
    cloud.add_device(device)
    return device


@pytest.fixture(name="patch_device_manager")
def patch_device_manager_fixture(cloud: FakeRoborockCloud) -> Generator[None, None, None]:
    """Fixture to patch the device manager and HTTP client."""
    with cloud.patch_device_manager():
        yield


async def test_no_devices(cloud: FakeRoborockCloud, patch_device_manager: None) -> None:
    """Test the DeviceManager created with no devices returned from the API."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert devices == []


async def test_with_q10_device(cloud: FakeRoborockCloud, patch_device_manager: None) -> None:
    """Test DeviceManager with a Q10 device simulator registered."""
    product = HomeDataProduct(
        id="product-id-q10",
        name="Roborock Q10",
        model="roborock.vacuum.ss07",
        category=RoborockCategory.VACUUM,
    )
    device_info = HomeDataDevice(
        duid="q10_duid",
        name="My Q10",
        local_key="key123key123key1",
        product_id=product.id,
        sn="q10_serial",
        pv="B01",
    )

    home_data = cloud.web_api.get_default_home_data()
    home_data.devices.append(device_info)
    home_data.products.append(product)
    cloud.web_api.set_homes_response(home_data)

    q10_sim = Q10VacuumSimulator(
        duid="q10_duid",
        device_info=device_info,
        product=product,
    )
    cloud.add_device(q10_sim)

    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()

    # The setup includes fake_device (V1) by default because of the fake_device fixture
    # which is not requested here (we only request cloud and patch_device_manager),
    # but the mock EAPI returns the full home_data layout containing our Q10 device.
    assert len(devices) == 1

    q10_device = await device_manager.get_device("q10_duid")
    assert q10_device is not None
    assert q10_device.name == "My Q10"
    assert q10_device.product.model == "roborock.vacuum.ss07"

    # Wait for background connect to establish
    for _ in range(20):
        if q10_device.is_connected:
            break
        await asyncio.sleep(0.05)
    assert q10_device.is_connected

    assert q10_device.b01_q10_properties is not None
    assert q10_device.b01_q10_properties.status.status is None

    await q10_device.b01_q10_properties.refresh()

    for _ in range(20):
        if q10_device.b01_q10_properties.status.battery == 100:
            break
        await asyncio.sleep(0.05)

    assert q10_device.b01_q10_properties.status.battery == 100
    from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceState

    assert q10_device.b01_q10_properties.status.status == YXDeviceState.CHARGING

    await q10_device.b01_q10_properties.vacuum.start_clean()

    for _ in range(20):
        if q10_device.b01_q10_properties.status.status == YXDeviceState.CLEANING:
            break
        await asyncio.sleep(0.05)

    assert q10_device.b01_q10_properties.status.status == YXDeviceState.CLEANING
    assert q10_sim.status[121] == 5

    await device_manager.close()


async def test_with_device(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test the DeviceManager created with devices returned from the API."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    assert devices[0].duid == "abc123"
    assert devices[0].name == "Roborock S7 MaxV"

    device = await device_manager.get_device("abc123")
    assert device is not None
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"

    await device_manager.close()


async def test_get_non_existent_device(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test getting a non-existent device."""
    device_manager = await create_device_manager(USER_PARAMS)
    device = await device_manager.get_device("non_existent_duid")
    assert device is None
    await device_manager.close()


async def test_create_home_data_api_exception() -> None:
    """Test that exceptions from the home data API are propagated through the wrapper."""
    with patch("roborock.devices.device_manager.RoborockApiClient.get_home_data_v3") as mock_get_home_data:
        mock_get_home_data.side_effect = RoborockException("Test exception")
        user_params = UserParams(username="test_user", user_data=USER_DATA)
        api = create_web_api_wrapper(user_params)

        with pytest.raises(RoborockException, match="Test exception"):
            await api.get_home_data()


async def test_device_manager_unauthorized_hook() -> None:
    """Test that unauthorized hook is called when RoborockInvalidCredentials is raised."""
    mock_hook = Mock()
    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=RoborockInvalidCredentials("Unauthorized"),
    ):
        with pytest.raises(RoborockInvalidCredentials, match="Unauthorized"):
            await create_device_manager(USER_PARAMS, mqtt_session_unauthorized_hook=mock_hook, prefer_cache=False)

        mock_hook.assert_called_once()


@pytest.mark.parametrize(("prefer_cache", "expected_call_count"), [(True, 1), (False, 2)])
async def test_cache_logic(
    cloud: FakeRoborockCloud,
    fake_device: V1VacuumSimulator,
    patch_device_manager: None,
    prefer_cache: bool,
    expected_call_count: int,
) -> None:
    """Test that the cache logic works correctly."""
    call_count = 0

    async def mock_home_data_with_counter(*args, **kwargs) -> HomeData:
        nonlocal call_count
        call_count += 1
        return HomeData.from_dict(mock_data.HOME_DATA_RAW)

    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=mock_home_data_with_counter,
    ):
        device_manager = await create_device_manager(USER_PARAMS, cache=InMemoryCache())
        # First call happens during create_device_manager initialization
        assert call_count == 1

        # Second call should use cache, not increment call_count if prefer_cache=True
        devices2 = await device_manager.discover_devices(prefer_cache=prefer_cache)
        assert call_count == expected_call_count
        assert len(devices2) == 1

        await device_manager.close()
        assert len(devices2) == 1

        # Ensure closing again works without error
        await device_manager.close()


async def test_home_data_api_fails_with_cache_fallback(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test that home data exceptions may still fall back to use the cache when available."""
    cache = InMemoryCache()
    cache_data = await cache.get()
    cache_data.home_data = HomeData.from_dict(mock_data.HOME_DATA_RAW)
    await cache.set(cache_data)

    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=RoborockException("Test exception"),
    ):
        # This call will skip the API and use the cache
        device_manager = await create_device_manager(USER_PARAMS, cache=cache)

        # This call will hit the API since we're not preferring the cache
        # but will fallback to the cache data on exception
        devices2 = await device_manager.discover_devices(prefer_cache=False)
        assert len(devices2) == 1

        await device_manager.close()


async def test_ready_callback(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test that the ready callback is invoked when a device connects."""
    ready_devices: list[RoborockDevice] = []
    device_manager = await create_device_manager(USER_PARAMS, ready_callback=ready_devices.append)
    await device_manager.get_devices()

    # Callback should be called for the discovered device
    assert len(ready_devices) == 1
    device = ready_devices[0]
    assert device.duid == "abc123"

    # Verify that adding a ready callback to an already connected device will
    # invoke the callback immediately.
    more_ready_device: list[RoborockDevice] = []
    device.add_ready_callback(more_ready_device.append)
    assert len(more_ready_device) == 1
    assert more_ready_device[0].duid == "abc123"

    await device_manager.close()


async def test_start_connect_failure(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test that start_connect retries when connection fails."""
    # Make connection fail initially
    channel_exception = RoborockException("Connection failed")
    fake_device.mqtt_channel.inject_error(channel_exception)
    assert fake_device.local_channel is not None
    fake_device.local_channel.inject_error(channel_exception)

    ready_devices: list[RoborockDevice] = []
    device_manager = await create_device_manager(USER_PARAMS, ready_callback=ready_devices.append)
    devices = await device_manager.get_devices()

    # Device should exist but not be connected
    assert len(devices) == 1
    assert not devices[0].is_connected
    assert not ready_devices

    # Clear error so connection succeeds on retry
    fake_device.mqtt_channel.clear_error()
    fake_device.local_channel.clear_error()

    # Wait for the device to attempt to connect again and succeed
    attempts = 0
    while not devices[0].is_connected:
        await asyncio.sleep(0.01)
        attempts += 1
        assert attempts < 10, "Device did not connect after multiple attempts"

    assert devices[0].is_connected
    assert ready_devices
    assert len(ready_devices) == 1

    await device_manager.close()


async def test_rediscover_devices(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test that we can discover devices multiple times and discover new devices."""
    raw_devices: list[dict[str, Any]] = mock_data.HOME_DATA_RAW["devices"]
    assert len(raw_devices) > 0
    raw_device_1 = raw_devices[0]

    home_data_responses = [
        HomeData.from_dict(mock_data.HOME_DATA_RAW),
        # New device added on second call.
        HomeData.from_dict(
            {
                **mock_data.HOME_DATA_RAW,
                "devices": [
                    raw_device_1,
                    {
                        **raw_device_1,
                        "duid": "new_device_duid",
                        "name": "New Device",
                        "model": "roborock.newmodel.v1",
                        "mac": "00:11:22:33:44:55",
                    },
                ],
            }
        ),
    ]

    async def mock_home_data_with_counter(*args, **kwargs) -> HomeData:
        nonlocal home_data_responses
        return home_data_responses.pop(0)

    # The new device is also a V1 vacuum simulator
    new_device_product = HomeDataProduct(
        id="product-id-123",
        name="New Device",
        model="roborock.newmodel.v1",
        category=RoborockCategory.VACUUM,
    )
    fake_device2 = V1VacuumSimulator(
        duid="new_device_duid",
        device_info=HomeDataDevice(
            duid="new_device_duid",
            name="New Device",
            local_key=mock_data.LOCAL_KEY,
            product_id="product-id-123",
            sn="fake_sn_new",
            pv="1.0",
        ),
        product=new_device_product,
    )
    cloud.add_device(fake_device2)

    with patch(
        "roborock.devices.device_manager.RoborockApiClient.get_home_data_v3",
        side_effect=mock_home_data_with_counter,
    ):
        device_manager = await create_device_manager(USER_PARAMS, cache=InMemoryCache())
        assert len(await device_manager.get_devices()) == 1

        # Second call should use cache and does not add new device
        await device_manager.discover_devices(prefer_cache=True)
        assert len(await device_manager.get_devices()) == 1

        # Third call should fetch new home data and add the new device
        await device_manager.discover_devices(prefer_cache=False)
        assert len(await device_manager.get_devices()) == 2

        # Verify the two devices exist with correct data
        device_1 = await device_manager.get_device("abc123")
        assert device_1 is not None
        assert device_1.name == "Roborock S7 MaxV"

        new_device = await device_manager.get_device("new_device_duid")
        assert new_device is not None
        assert new_device.name == "New Device"

        await device_manager.close()


async def test_start_connect_unexpected_error(
    cloud: FakeRoborockCloud, fake_device: V1VacuumSimulator, patch_device_manager: None
) -> None:
    """Test that some unexpected errors from start_connect are propagated."""
    # Raise generic Exception
    fake_device.mqtt_channel.inject_error(Exception("Unexpected error"))
    assert fake_device.local_channel is not None
    fake_device.local_channel.inject_error(Exception("Unexpected error"))

    with pytest.raises(Exception, match="Unexpected error"):
        await create_device_manager(USER_PARAMS)


async def test_diagnostics_collection(
    cloud: FakeRoborockCloud,
    fake_device: V1VacuumSimulator,
    patch_device_manager: None,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test that diagnostics are collected correctly in the DeviceManager."""
    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert len(devices) == 1

    diagnostics = device_manager.diagnostic_data()
    assert diagnostics is not None
    diagnostics_data = diagnostics.get("diagnostics")
    assert diagnostics_data
    assert diagnostics_data.get("discover_devices") == 1
    assert diagnostics_data.get("fetch_home_data") == 1

    assert snapshot == diagnostics

    await device_manager.close()


async def test_unsupported_protocol_version(cloud: FakeRoborockCloud, patch_device_manager: None) -> None:
    """Test the DeviceManager with some supported and unsupported product IDs."""
    fake_device = V1VacuumSimulator(
        duid="device-uid-1",
        device_info=HomeDataDevice(
            duid="device-uid-1",
            name="Device 1",
            local_key=mock_data.LOCAL_KEY,
            product_id="product-id-1",
            pv="1.0",
        ),
        product=HomeDataProduct(
            id="product-id-1",
            name="Roborock S7 MaxV",
            model="roborock.vacuum.a27",
            category=RoborockCategory.VACUUM,
        ),
    )
    cloud.add_device(fake_device)

    # Fetch default home data and modify it
    home_data = cloud.web_api.get_default_home_data()
    modified_home_data = replace(
        home_data,
        devices=list(home_data.devices)
        + [
            HomeDataDevice(
                duid="device-uid-2",
                name="Device 2",
                local_key=mock_data.LOCAL_KEY,
                product_id="product-id-2",
                pv="unknown-pv",
            ),
        ],
        products=list(home_data.products)
        + [
            HomeDataProduct(
                id="product-id-2",
                name="New Roborock Model",
                model="roborock.vacuum.newmodel",
                category=RoborockCategory.VACUUM,
            ),
        ],
    )
    cloud.web_api.set_homes_response(modified_home_data)

    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert [device.duid for device in devices] == ["device-uid-1"]

    diagnostics = device_manager.diagnostic_data()
    diagnostics_data = diagnostics.get("diagnostics")
    assert diagnostics_data
    assert diagnostics_data.get("supported_devices") == {"1.0": 1}
    assert diagnostics_data.get("unsupported_devices") == {"unknown-pv": 1}

    await device_manager.close()


async def test_unsupported_v1_category(cloud: FakeRoborockCloud, patch_device_manager: None) -> None:
    """Test that non-vacuum V1 devices are skipped as unsupported."""
    fake_device = V1VacuumSimulator(
        duid="device-uid-1",
        device_info=HomeDataDevice(
            duid="device-uid-1",
            name="Device 1",
            local_key=mock_data.LOCAL_KEY,
            product_id="product-id-1",
            pv="1.0",
        ),
        product=HomeDataProduct(
            id="product-id-1",
            name="Roborock S7 MaxV",
            model="roborock.vacuum.a27",
            category=RoborockCategory.VACUUM,
        ),
    )
    cloud.add_device(fake_device)

    # Fetch default home data and modify it
    home_data = cloud.web_api.get_default_home_data()
    modified_home_data = replace(
        home_data,
        devices=list(home_data.devices)
        + [
            HomeDataDevice(
                duid="device-uid-2",
                name="Device 2",
                local_key=mock_data.LOCAL_KEY,
                product_id="product-id-2",
                pv="1.0",
            ),
        ],
        products=list(home_data.products)
        + [
            HomeDataProduct(
                id="product-id-2",
                name="Roborock RockNeo",
                model="roborock.mower.q105",
                category=RoborockCategory.MOWER,
            ),
        ],
    )
    cloud.web_api.set_homes_response(modified_home_data)

    device_manager = await create_device_manager(USER_PARAMS)
    devices = await device_manager.get_devices()
    assert [device.duid for device in devices] == ["device-uid-1"]

    diagnostics = device_manager.diagnostic_data()
    diagnostics_data = diagnostics.get("diagnostics")
    assert diagnostics_data
    assert diagnostics_data.get("supported_devices") == {"1.0": 1}
    assert diagnostics_data.get("unsupported_devices") == {"1.0": 1}

    await device_manager.close()

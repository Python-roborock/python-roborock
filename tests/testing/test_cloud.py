from dataclasses import replace

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory, UserData
from roborock.data.v1 import RoborockStateCode
from roborock.devices.cache import InMemoryCache
from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.exceptions import RoborockException
from roborock.testing import DEFAULT_STATUS, FakeRoborockCloud, V1VacuumSimulator
from roborock.web_api import RoborockApiClient
from tests import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)


async def test_fake_roborock_cloud():
    """Verify that FakeRoborockCloud can discover devices via fake HTTP requests and connect them."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(
        duid="living_room_s7",
        status=replace(DEFAULT_STATUS, battery=99, state=RoborockStateCode.charging),
    )
    cloud.add_device(fake_device)

    with cloud.patch_device_manager():
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=USER_DATA),
            cache=InMemoryCache(),
        )
        devices = await manager.get_devices()

    assert len(devices) == 1
    device = devices[0]
    assert device.duid == "living_room_s7"
    assert device.is_connected

    assert device.v1_properties is not None
    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.battery == 99


async def test_cloud_unsupported_protocol():
    """Verify that FakeRoborockCloud raises NotImplementedError for A01 or B01 devices."""
    cloud = FakeRoborockCloud()
    fake_b01_server = V1VacuumSimulator(
        duid="b01_vacuum",
        product=HomeDataProduct(
            id="product_b01",
            name="Q7 Vacuum",
            model="roborock.vacuum.sc",
            category=RoborockCategory.VACUUM,
        ),
        device_info=HomeDataDevice(
            duid="b01_vacuum",
            name="Q7 Vacuum",
            local_key="fake_localkey_16bytes",
            product_id="product_b01",
            pv="B01",
        ),
    )
    cloud.add_device(fake_b01_server)

    with cloud.patch_device_manager():
        with pytest.raises(NotImplementedError, match="Simulating protocol B01 is not yet supported"):
            await create_device_manager(
                user_params=UserParams(username="test_user", user_data=USER_DATA),
                cache=InMemoryCache(),
            )


async def test_cloud_login_error_override():
    """Verify that we can override login status and payloads to test authentication failure handling."""
    cloud = FakeRoborockCloud()
    cloud.web_api.login_status = 401
    cloud.web_api.login_payload = {"code": 1002, "msg": "Invalid credentials"}

    with cloud.patch_device_manager():
        client = RoborockApiClient(username="test_user@gmail.com")
        with pytest.raises(RoborockException, match="Invalid credentials - response code: 1002"):
            await client.pass_login("wrong_password")


async def test_cloud_dynamic_device_addition():
    """Verify that adding a device dynamically after patching works due to the callback API."""
    cloud = FakeRoborockCloud()

    with cloud.patch_device_manager():
        fake_device = V1VacuumSimulator(
            duid="dynamic_s7",
            status=replace(DEFAULT_STATUS, battery=42),
        )
        cloud.add_device(fake_device)

        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=USER_DATA),
            cache=InMemoryCache(),
        )
        devices = await manager.get_devices()

    assert len(devices) == 1
    assert devices[0].duid == "dynamic_s7"

    assert devices[0].v1_properties is not None
    await devices[0].v1_properties.status.refresh()
    assert devices[0].v1_properties.status.battery == 42

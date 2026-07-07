from dataclasses import replace

import pytest

from roborock.data import UserData
from roborock.data.v1 import RoborockStateCode
from roborock.data.v1.v1_code_mappings import RoborockChargeStatus, RoborockDockTypeCode, RoborockInCleaning
from roborock.devices.cache import InMemoryCache
from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.devices.traits.v1.consumeable import ConsumableAttribute
from roborock.exceptions import RoborockException
from roborock.testing import (
    DEFAULT_NETWORK_INFO,
    DEFAULT_STATUS,
    FakeRoborockCloud,
    V1VacuumSimulator,
)
from tests import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)


async def _create_connected_device(cloud, fake_device):
    """Helper to create a connected device from a cloud and simulator."""
    cloud.add_device(fake_device)
    with cloud.patch_device_manager():
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=USER_DATA),
            cache=InMemoryCache(),
        )
        devices = await manager.get_devices()
    assert len(devices) == 1
    return devices[0]


async def test_trait_consumable_refresh():
    """Verify that the consumable trait can be refreshed from the simulator."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_consumable")
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.consumables.refresh()
    assert device.v1_properties.consumables.main_brush_work_time == 74382
    assert device.v1_properties.consumables.side_brush_work_time == 74383
    assert device.v1_properties.consumables.filter_work_time == 74384


async def test_trait_consumable_reset():
    """Verify that resetting a consumable updates both the simulator and trait."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_reset")
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.consumables.refresh()
    assert device.v1_properties.consumables.filter_work_time == 74384

    # Reset the filter consumable through the trait API
    await device.v1_properties.consumables.reset_consumable(ConsumableAttribute.FILTER_WORK_TIME)

    # The simulator state should be updated
    assert fake_device.consumables.filter_work_time == 0
    # The trait auto-refreshes after reset, so the client should reflect the change
    assert device.v1_properties.consumables.filter_work_time == 0


async def test_trait_dnd_refresh():
    """Verify that the DND timer trait can be refreshed from the simulator."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_dnd")
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.dnd.refresh()
    assert device.v1_properties.dnd.start_hour == 22
    assert device.v1_properties.dnd.end_hour == 7
    assert device.v1_properties.dnd.enabled == 1


async def test_trait_fan_speed_change():
    """Verify that sending set_custom_mode updates the simulator fan speed and the trait reflects it."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_fan", status=replace(DEFAULT_STATUS, fan_power=102))
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.fan_power == 102

    # Change fan speed through the command trait
    await device.v1_properties.command.send("set_custom_mode", [105])
    assert fake_device.status.fan_power == 105

    # Refresh status to pick up the changed value
    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.fan_power == 105


async def test_trait_clean_summary_refresh():
    """Verify that the clean summary trait can be refreshed from the simulator."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_summary")
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.clean_summary.refresh()
    assert device.v1_properties.clean_summary.clean_count == 31
    assert device.v1_properties.clean_summary.dust_collection_count == 25


async def test_trait_multiple_state_transitions():
    """Verify a sequence of state transitions through trait commands."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_transitions")
    device = await _create_connected_device(cloud, fake_device)

    # Start cleaning
    await device.v1_properties.command.send("app_start")
    assert fake_device.status.state == RoborockStateCode.cleaning

    # Stop (pauses the vacuum)
    await device.v1_properties.command.send("app_stop")
    assert fake_device.status.state == RoborockStateCode.paused

    # Send it back to the dock
    await device.v1_properties.command.send("app_charge")
    assert fake_device.status.state == RoborockStateCode.returning_home

    # Verify the client sees the final state after refresh
    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.state == RoborockStateCode.returning_home


async def test_trait_push_update_propagation():
    """Verify that unsolicited push updates propagate to client traits without refresh."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(
        duid="s7_push",
        status=replace(DEFAULT_STATUS, battery=99, state=RoborockStateCode.charging),
    )
    device = await _create_connected_device(cloud, fake_device)

    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.battery == 99

    # Mutate the simulator state and push an update
    fake_device.status.battery = 45
    fake_device.status.state = RoborockStateCode.returning_home
    fake_device.trigger_push_update()

    # The client status properties should be updated immediately without a manual refresh
    assert device.v1_properties.status.battery == 45
    assert device.v1_properties.status.state == RoborockStateCode.returning_home


async def test_trait_custom_handler_override():
    """Verify that custom_handlers override default behavior for specific commands."""

    def custom_get_status(params):
        return [{"state": RoborockStateCode.cleaning, "battery": 77, "fan_power": 999}]

    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(
        duid="s7_custom",
        custom_handlers={"get_status": custom_get_status},
    )
    device = await _create_connected_device(cloud, fake_device)

    # The custom handler returns different values than the simulator's defaults
    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.battery == 77
    assert device.v1_properties.status.fan_power == 999


async def test_trait_properties_and_dss_config():
    """Verify that properties, dss config, and dock_type config are correctly exposed on the simulator."""
    fake_device = V1VacuumSimulator(
        duid="s7_properties",
        status=replace(
            DEFAULT_STATUS,
            state=RoborockStateCode.cleaning,
            dss=42,
            dock_type=RoborockDockTypeCode(5),
        ),
    )
    assert fake_device.in_cleaning == RoborockInCleaning.global_clean_not_complete
    assert fake_device.in_returning == 0
    assert fake_device.charge_status == RoborockChargeStatus.charge_waiting
    assert fake_device.status.dss == 42
    assert fake_device.status.dock_type == RoborockDockTypeCode(5)

    fake_device.status.state = RoborockStateCode.returning_home
    assert fake_device.in_cleaning == RoborockInCleaning.complete
    assert fake_device.in_returning == 1
    assert fake_device.charge_status == RoborockChargeStatus.charge_waiting

    fake_device.status.state = RoborockStateCode.charging
    assert fake_device.in_cleaning == RoborockInCleaning.complete
    assert fake_device.in_returning == 0
    assert fake_device.charge_status == RoborockChargeStatus.charging


async def test_trait_publish_failure_injection():
    """Verify that publish_side_effect on simulator channels correctly raises errors."""
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="s7_failing_publish")
    device = await _create_connected_device(cloud, fake_device)

    # Make local publish fail
    assert fake_device.local_channel is not None
    fake_device.local_channel.publish_side_effect = RoborockException("Local network error")

    # The client status refresh should still succeed by falling back to MQTT!
    await device.v1_properties.status.refresh()

    # If MQTT also fails, the refresh must fail
    fake_device.mqtt_channel.publish_side_effect = RoborockException("MQTT network error")
    with pytest.raises(RoborockException, match="MQTT network error"):
        await device.v1_properties.status.refresh()


async def test_multiple_devices_network_info_override():
    """Verify that multiple devices can coexist and their individual custom network

    info properties are correctly fetched.
    """
    cloud = FakeRoborockCloud()

    fake_device1 = V1VacuumSimulator(duid="device_1")
    fake_device2 = V1VacuumSimulator(
        duid="device_2",
        network_info=replace(DEFAULT_NETWORK_INFO, ip="192.168.1.50", ssid="custom_wifi"),
    )

    cloud.add_device(fake_device1)
    cloud.add_device(fake_device2)

    with cloud.patch_device_manager():
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=USER_DATA),
            cache=InMemoryCache(),
        )
        devices = await manager.get_devices()

    assert len(devices) == 2

    # Sort them by duid to ensure order
    devices.sort(key=lambda d: d.duid)

    device1 = devices[0]
    device2 = devices[1]

    assert device1.duid == "device_1"
    assert device2.duid == "device_2"

    # Refresh and verify network info on device1 (should have defaults)
    assert device1.v1_properties is not None
    assert device1.v1_properties.network_info is not None
    await device1.v1_properties.network_info.refresh()
    assert device1.v1_properties.network_info.ip == "1.1.1.1"
    assert device1.v1_properties.network_info.ssid == "test_wifi"

    # Refresh and verify network info on device2 (should have overridden values)
    assert device2.v1_properties is not None
    assert device2.v1_properties.network_info is not None
    await device2.v1_properties.network_info.refresh()
    assert device2.v1_properties.network_info.ip == "192.168.1.50"
    assert device2.v1_properties.network_info.ssid == "custom_wifi"

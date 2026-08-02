"""Unit and integration tests for DyadSimulator and ZeoSimulator (A01 protocol)."""

import pytest

from roborock.data.containers import UserData
from roborock.data.dyad.dyad_code_mappings import (
    DyadCleanMode,
    DyadError,
    DyadSuction,
    DyadWaterLevel,
    RoborockDyadStateCode,
)
from roborock.data.zeo.zeo_code_mappings import (
    ZeoDryingMode,
    ZeoError,
    ZeoMode,
    ZeoProgram,
    ZeoRinse,
    ZeoSpin,
    ZeoState,
    ZeoTemperature,
)
from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol
from roborock.testing import (
    DEFAULT_DYAD_STATUS,
    DEFAULT_ZEO_STATUS,
    DyadSimulator,
    FakeRoborockCloud,
    ZeoSimulator,
)
from tests.mock_data import USER_DATA


@pytest.fixture(name="dyad_sim")
def dyad_sim_fixture() -> DyadSimulator:
    """Fixture for DyadSimulator."""
    return DyadSimulator(duid="test_dyad_duid")


@pytest.fixture(name="zeo_sim")
def zeo_sim_fixture() -> ZeoSimulator:
    """Fixture for ZeoSimulator."""
    return ZeoSimulator(duid="test_zeo_duid")


def test_dyad_default_status(dyad_sim: DyadSimulator) -> None:
    """Test default initial status dictionary for Dyad simulator."""
    assert dyad_sim.status == DEFAULT_DYAD_STATUS
    assert dyad_sim.status[int(RoborockDyadDataProtocol.STATUS)] == RoborockDyadStateCode.charging.value
    assert dyad_sim.status[int(RoborockDyadDataProtocol.SUCTION)] == DyadSuction.l1.value


def test_zeo_default_status(zeo_sim: ZeoSimulator) -> None:
    """Test default initial status dictionary for Zeo simulator."""
    assert zeo_sim.status == DEFAULT_ZEO_STATUS
    assert zeo_sim.status[int(RoborockZeoProtocol.STATE)] == ZeoState.standby.value
    assert zeo_sim.status[int(RoborockZeoProtocol.MODE)] == ZeoMode.wash_and_dry.value


def test_dyad_set_protocol_value_and_named_setters(dyad_sim: DyadSimulator) -> None:
    """Test setting Dyad values via enum-aware set_protocol_value and explicit helper methods."""
    dyad_sim.set_suction(DyadSuction.l2)
    assert dyad_sim.status[int(RoborockDyadDataProtocol.SUCTION)] == DyadSuction.l2.value

    dyad_sim.set_water_level(DyadWaterLevel.l3)
    assert dyad_sim.status[int(RoborockDyadDataProtocol.WATER_LEVEL)] == DyadWaterLevel.l3.value

    dyad_sim.set_state(RoborockDyadStateCode.washing)
    assert dyad_sim.status[int(RoborockDyadDataProtocol.STATUS)] == RoborockDyadStateCode.washing.value

    dyad_sim.set_error(DyadError.dirty_tank_full)
    assert dyad_sim.status[int(RoborockDyadDataProtocol.ERROR)] == DyadError.dirty_tank_full.value


def test_zeo_set_protocol_value_and_named_setters(zeo_sim: ZeoSimulator) -> None:
    """Test setting Zeo values via enum-aware set_protocol_value and explicit helper methods."""
    zeo_sim.set_state(ZeoState.washing)
    assert zeo_sim.status[int(RoborockZeoProtocol.STATE)] == ZeoState.washing.value

    zeo_sim.set_mode(ZeoMode.wash)
    assert zeo_sim.status[int(RoborockZeoProtocol.MODE)] == ZeoMode.wash.value

    zeo_sim.set_program(ZeoProgram.wool)
    assert zeo_sim.status[int(RoborockZeoProtocol.PROGRAM)] == ZeoProgram.wool.value

    zeo_sim.set_temperature(ZeoTemperature.high)
    assert zeo_sim.status[int(RoborockZeoProtocol.TEMP)] == ZeoTemperature.high.value

    zeo_sim.set_detergent_empty(True)
    assert zeo_sim.status[int(RoborockZeoProtocol.DETERGENT_EMPTY)] is True


async def test_dyad_query_values(dyad_sim: DyadSimulator) -> None:
    """Test querying Dyad protocols via DyadApi with a simulated A01 channel."""
    api = DyadApi(dyad_sim.mqtt_channel)  # type: ignore[arg-type]

    query_protocols = [
        RoborockDyadDataProtocol.STATUS,
        RoborockDyadDataProtocol.POWER,
        RoborockDyadDataProtocol.SUCTION,
        RoborockDyadDataProtocol.WATER_LEVEL,
        RoborockDyadDataProtocol.CLEAN_MODE,
        RoborockDyadDataProtocol.AUTO_DRY,
        RoborockDyadDataProtocol.VOLUME_SET,
        RoborockDyadDataProtocol.ERROR,
        RoborockDyadDataProtocol.TOTAL_RUN_TIME,
    ]

    res = await api.query_values(query_protocols)

    assert res[RoborockDyadDataProtocol.STATUS] == RoborockDyadStateCode.charging.name
    assert res[RoborockDyadDataProtocol.POWER] == 100
    assert res[RoborockDyadDataProtocol.SUCTION] == DyadSuction.l1.name
    assert res[RoborockDyadDataProtocol.WATER_LEVEL] == DyadWaterLevel.l1.name
    assert res[RoborockDyadDataProtocol.CLEAN_MODE] == DyadCleanMode.auto.name
    assert res[RoborockDyadDataProtocol.AUTO_DRY] is True
    assert res[RoborockDyadDataProtocol.VOLUME_SET] == 80
    assert res[RoborockDyadDataProtocol.ERROR] == DyadError.none.name
    assert res[RoborockDyadDataProtocol.TOTAL_RUN_TIME] == 120


async def test_zeo_query_values(zeo_sim: ZeoSimulator) -> None:
    """Test querying Zeo protocols via ZeoApi with a simulated A01 channel."""
    api = ZeoApi(zeo_sim.mqtt_channel)  # type: ignore[arg-type]

    query_protocols = [
        RoborockZeoProtocol.STATE,
        RoborockZeoProtocol.MODE,
        RoborockZeoProtocol.PROGRAM,
        RoborockZeoProtocol.TEMP,
        RoborockZeoProtocol.RINSE_TIMES,
        RoborockZeoProtocol.SPIN_LEVEL,
        RoborockZeoProtocol.DRYING_MODE,
        RoborockZeoProtocol.DETERGENT_EMPTY,
        RoborockZeoProtocol.SOFTENER_EMPTY,
        RoborockZeoProtocol.SOUND_SET,
        RoborockZeoProtocol.ERROR,
    ]

    res = await api.query_values(query_protocols)

    assert res[RoborockZeoProtocol.STATE] == ZeoState.standby.name
    assert res[RoborockZeoProtocol.MODE] == ZeoMode.wash_and_dry.name
    assert res[RoborockZeoProtocol.PROGRAM] == ZeoProgram.standard.name
    assert res[RoborockZeoProtocol.TEMP] == ZeoTemperature.medium.name
    assert res[RoborockZeoProtocol.RINSE_TIMES] == ZeoRinse.low.name
    assert res[RoborockZeoProtocol.SPIN_LEVEL] == ZeoSpin.high.name
    assert res[RoborockZeoProtocol.DRYING_MODE] == ZeoDryingMode.store.name
    assert res[RoborockZeoProtocol.DETERGENT_EMPTY] is False
    assert res[RoborockZeoProtocol.SOFTENER_EMPTY] is False
    assert res[RoborockZeoProtocol.SOUND_SET] is True
    assert res[RoborockZeoProtocol.ERROR] == ZeoError.none.name


async def test_dyad_set_value(dyad_sim: DyadSimulator) -> None:
    """Test sending set_value commands through DyadApi to update simulator state."""
    dyad_api = DyadApi(dyad_sim.mqtt_channel)  # type: ignore[arg-type]
    await dyad_api.set_value(RoborockDyadDataProtocol.VOLUME_SET, 45)
    assert dyad_sim.status[int(RoborockDyadDataProtocol.VOLUME_SET)] == 45


async def test_zeo_set_value(zeo_sim: ZeoSimulator) -> None:
    """Test sending set_value commands through ZeoApi to update simulator state."""
    zeo_api = ZeoApi(zeo_sim.mqtt_channel)  # type: ignore[arg-type]
    await zeo_api.set_value(RoborockZeoProtocol.PROGRAM, ZeoProgram.wool.value)
    assert zeo_sim.status[int(RoborockZeoProtocol.PROGRAM)] == ZeoProgram.wool.value


async def test_a01_device_manager_integration() -> None:
    """Test full DeviceManager discovery and connection to simulated Dyad and Zeo devices."""
    cloud = FakeRoborockCloud()
    dyad_sim = DyadSimulator(duid="dyad_e2e")
    zeo_sim = ZeoSimulator(duid="zeo_e2e")

    cloud.add_device(dyad_sim)
    cloud.add_device(zeo_sim)

    with cloud.patch_device_manager():
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=UserData.from_dict(USER_DATA)),
        )
        devices = await manager.get_devices()

    assert len(devices) == 2
    devices.sort(key=lambda d: d.duid)

    dyad_device = devices[0]
    zeo_device = devices[1]

    assert dyad_device.duid == "dyad_e2e"
    assert dyad_device.dyad is not None

    assert zeo_device.duid == "zeo_e2e"
    assert zeo_device.zeo is not None

    # Query values on discovered Dyad device
    dyad_status = await dyad_device.dyad.query_values([RoborockDyadDataProtocol.STATUS])
    assert dyad_status[RoborockDyadDataProtocol.STATUS] == RoborockDyadStateCode.charging.name

    # Query values on discovered Zeo device
    zeo_status = await zeo_device.zeo.query_values([RoborockZeoProtocol.STATE])
    assert zeo_status[RoborockZeoProtocol.STATE] == ZeoState.standby.name

    await manager.close()

"""Tests for the Q10 B01 status trait."""

import asyncio
import pathlib
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import Mock

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXAreaUnit,
    YXCarpetCleanType,
    YXCleanLine,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceDustCollectionFrequency,
    YXDeviceState,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import dpNetInfo, dpNotDisturbExpand, dpTimeZone
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.protocols.b01_q10_protocol import Q10Message, decode_message
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .conftest import FakeB01Q10Channel

TEST_DATA_DIR = pathlib.Path("tests/protocols/testdata/b01_q10_protocol")

TESTDATA_DP_STATUS_DP_CLEAN_TASK_TYPE = (TEST_DATA_DIR / "dpStatus-dpCleanTaskType.json").read_bytes()
TESTDATA_DP_REQUEST_DPS = (TEST_DATA_DIR / "dpRequetdps.json").read_bytes()


@pytest.fixture(name="message_queue")
def message_queue_fixture() -> asyncio.Queue[Q10Message]:
    """Fixture for a message queue used by the mock stream."""
    return asyncio.Queue()


@pytest.fixture(name="mock_channel")
def mock_channel_fixture(message_queue: asyncio.Queue[Q10Message]) -> FakeB01Q10Channel:
    """Fixture to mock the subscribe_stream method to yield from a queue."""
    channel = FakeB01Q10Channel()

    async def mock_stream() -> AsyncGenerator[Q10Message, None]:
        while True:
            yield await message_queue.get()

    setattr(channel, "subscribe_stream", Mock(side_effect=mock_stream))
    return channel


@pytest.fixture(name="q10_api")
async def q10_api_fixture(mock_channel: FakeB01Q10Channel) -> AsyncGenerator[Q10PropertiesApi, None]:
    """Fixture to create and manage the Q10PropertiesApi."""
    api = create(mock_channel)
    await api.start()
    yield api
    await api.close()


def build_q10_message(payload: bytes) -> Q10Message:
    """Helper to build a Q10Message for testing."""
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        version=b"B01",
    )
    result = decode_message(msg)
    assert result is not None
    return result


async def wait_for_attribute_value(obj: Any, attribute: str, value: Any, timeout: float = 2.0) -> None:
    """Wait for an attribute on an object to reach a specific value."""
    for _ in range(int(timeout / 0.1)):
        if getattr(obj, attribute) == value:
            return
        await asyncio.sleep(0.1)
    pytest.fail(f"Timeout waiting for {attribute} to become {value} on {obj}")


async def test_status_trait_streaming(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """Test that the StatusTrait updates its state from streaming messages."""
    # status (121) = 8 (CHARGING_STATE)
    # clean_task_type (138) = 0 (IDLE)
    message = build_q10_message(TESTDATA_DP_STATUS_DP_CLEAN_TASK_TYPE)

    assert q10_api.status.status is None
    assert q10_api.status.clean_task_type is None

    # Push the message into the queue
    message_queue.put_nowait(message)

    # Wait for the update
    await wait_for_attribute_value(q10_api.status, "status", YXDeviceState.CHARGING)

    # Verify trait attributes are updated
    assert q10_api.status.status == YXDeviceState.CHARGING
    assert q10_api.status.clean_task_type == YXDeviceCleanTask.IDLE


async def test_status_trait_refresh(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """Test that the StatusTrait sends a refresh command and updates state."""
    assert q10_api.status.battery is None
    assert q10_api.status.status is None
    assert q10_api.status.fan_level is None
    assert q10_api.status.total_clean_count is None
    assert q10_api.consumable.main_brush_life is None
    assert q10_api.status.cleaning_progress is None
    assert q10_api.status.fault is None

    # Mock the response to refresh
    # battery (122) = 100
    # status (121) = 8 (CHARGING_STATE)
    # fan_level (123) = 2 (BALANCED)
    message = build_q10_message(TESTDATA_DP_REQUEST_DPS)

    # Send a refresh command
    await q10_api.refresh()
    assert len(mock_channel.published_commands) == 1
    command, params = mock_channel.published_commands[0]
    assert command == B01_Q10_DP.REQUEST_DPS
    assert params == {}

    # Push the response message into the queue
    message_queue.put_nowait(message)

    # Wait for the update
    await wait_for_attribute_value(q10_api.status, "battery", 100)

    # Verify trait attributes are updated
    assert q10_api.status.battery == 100
    assert q10_api.status.status == YXDeviceState.CHARGING
    assert q10_api.status.fan_level == YXFanLevel.BALANCED
    assert q10_api.status.total_clean_area == 0
    assert q10_api.status.total_clean_count == 0
    assert q10_api.status.total_clean_time == 0
    assert q10_api.consumable.main_brush_life == 0
    assert q10_api.consumable.side_brush_life == 0
    assert q10_api.consumable.filter_life == 0
    assert q10_api.consumable.sensor_life == 0
    assert q10_api.status.cleaning_progress == 100
    assert q10_api.status.fault == 0
    assert q10_api.status.clean_mode == YXCleanType.VAC_AND_MOP
    assert q10_api.status.water_level == YXWaterLevel.LOW

    # Settings with dedicated traits are read from those traits.
    assert q10_api.volume.volume == 74
    assert q10_api.do_not_disturb.not_disturb is True
    assert q10_api.do_not_disturb.is_on is True
    assert q10_api.child_lock.child_lock is False
    assert q10_api.child_lock.is_on is False
    assert q10_api.dust_collection.dust_switch is True
    assert q10_api.dust_collection.is_on is True
    assert q10_api.dust_collection.dust_setting == YXDeviceDustCollectionFrequency.REGULAR

    # Additional state captured on the Status trait.
    assert q10_api.status.mop_state is True
    assert q10_api.status.ground_clean is False
    assert q10_api.status.carpet_clean_type == YXCarpetCleanType.RISE
    assert q10_api.status.area_unit == YXAreaUnit.SQUARE_METER
    assert q10_api.status.auto_boost is False
    assert q10_api.status.map_save_switch is True
    assert q10_api.status.recent_clean_record is False
    assert q10_api.status.valley_point_charging is False
    assert q10_api.status.clean_line == YXCleanLine.FAST
    assert q10_api.status.line_laser_obstacle_avoidance is True
    assert q10_api.status.robot_country_code == "us"
    assert q10_api.status.robot_type == 1
    assert q10_api.status.time_zone == dpTimeZone(time_zone_city="America/Los_Angeles", time_zone_sec=-28800)

    # Nested containers are parsed into their dataclasses on their own traits.
    assert q10_api.do_not_disturb.not_disturb_expand == dpNotDisturbExpand(
        disturb_dust_enable=1, disturb_light=1, disturb_resume_clean=1, disturb_voice=1
    )
    assert q10_api.network_info.net_info == dpNetInfo(
        wifi_name="wifi-network-name", ip_adress="1.1.1.2", mac="99:AA:88:BB:77:CC", signal=-50
    )


async def test_status_trait_vacuum_only_refresh(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """Test decoding a full status dump from a vacuum-only (no mop) Q10."""
    payload = (TEST_DATA_DIR / "dpRequestDps_vacuum_only.json").read_bytes()
    message_queue.put_nowait(build_q10_message(payload))

    await wait_for_attribute_value(q10_api.status, "battery", 75)

    assert q10_api.status.fan_level == YXFanLevel.MAX_PLUS
    assert q10_api.status.water_level == YXWaterLevel.MEDIUM
    assert q10_api.status.clean_mode == YXCleanType.VACUUM
    assert q10_api.status.recent_clean_record is True
    assert q10_api.status.total_clean_count == 7


def test_status_trait_update_listener(q10_api: Q10PropertiesApi) -> None:
    """Test that status listeners receive updates and can unsubscribe."""
    event = asyncio.Event()

    unsubscribe = q10_api.status.add_update_listener(event.set)

    first_update = {B01_Q10_DP.BATTERY: 88}
    q10_api.status.update_from_dps(first_update)

    assert event.is_set()
    event.clear()

    unsubscribe()

    second_update = {B01_Q10_DP.BATTERY: 87}
    q10_api.status.update_from_dps(second_update)

    assert not event.is_set()


def test_status_trait_update_listener_ignores_value(q10_api: Q10PropertiesApi) -> None:
    """Test that status listeners are not notified for unrelated updates."""
    event = asyncio.Event()

    unsubscribe = q10_api.status.add_update_listener(event.set)

    first_update = {B01_Q10_DP.HEARTBEAT: 1}  # Not a value in `Status` dataclass
    q10_api.status.update_from_dps(first_update)

    assert not event.is_set()

    unsubscribe()

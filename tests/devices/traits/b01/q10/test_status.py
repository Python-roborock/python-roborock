"""Tests for the Q10 B01 status trait."""

import asyncio
import json
import pathlib
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXDeviceCleanTask,
    YXDeviceState,
    YXFanLevel,
)
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TEST_DATA_DIR = pathlib.Path("tests/protocols/testdata/b01_q10_protocol")

TESTDATA_DP_STATUS_DP_CLEAN_TASK_TYPE = (TEST_DATA_DIR / "dpStatus-dpCleanTaskType.json").read_bytes()
TESTDATA_DP_REQUEST_DPS = (TEST_DATA_DIR / "dpRequetdps.json").read_bytes()


@pytest.fixture
def mock_channel():
    """Fixture for a mocked MQTT channel."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def message_queue() -> asyncio.Queue[RoborockMessage]:
    """Fixture for a message queue used by the mock stream."""
    return asyncio.Queue()


@pytest.fixture
def mock_subscribe_stream(mock_channel: AsyncMock, message_queue: asyncio.Queue[RoborockMessage]) -> Mock:
    """Fixture to mock the subscribe_stream method to yield from a queue."""

    async def mock_stream() -> AsyncGenerator[RoborockMessage, None]:
        while True:
            yield await message_queue.get()

    mock = Mock(return_value=mock_stream())
    mock_channel.subscribe_stream = mock
    return mock


@pytest.fixture
async def q10_api(mock_channel: AsyncMock, mock_subscribe_stream: Mock) -> AsyncGenerator[Q10PropertiesApi, None]:
    """Fixture to create and manage the Q10PropertiesApi."""
    api = create(mock_channel)
    await api.start()
    yield api
    await api.close()


def build_message(payload: bytes) -> RoborockMessage:
    """Helper to build a RoborockMessage for testing."""
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        version=b"B01",
    )


async def wait_for_attribute_value(obj: Any, attribute: str, value: Any, timeout: float = 2.0) -> None:
    """Wait for an attribute on an object to reach a specific value.

    This is a temporary polling solution until listeners are implemented.
    """
    for _ in range(int(timeout / 0.1)):
        if getattr(obj, attribute) == value:
            return
        await asyncio.sleep(0.1)
    pytest.fail(f"Timeout waiting for {attribute} to become {value} on {obj}")


async def test_status_trait_streaming(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    """Test that the StatusTrait updates its state from streaming messages."""
    # status (121) = 8 (CHARGING_STATE)
    # clean_task_type (138) = 0 (IDLE)
    message = build_message(TESTDATA_DP_STATUS_DP_CLEAN_TASK_TYPE)

    assert q10_api.status.status is None
    assert q10_api.status.clean_task_type is None

    # Push the message into the queue
    message_queue.put_nowait(message)

    # Wait for the update
    await wait_for_attribute_value(q10_api.status, "status", YXDeviceState.CHARGING_STATE)

    # Verify trait attributes are updated
    assert q10_api.status.status == YXDeviceState.CHARGING_STATE
    assert q10_api.status.clean_task_type == YXDeviceCleanTask.IDLE


async def test_status_trait_refresh(
    q10_api: Q10PropertiesApi,
    mock_channel: AsyncMock,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    """Test that the StatusTrait sends a refresh command and updates state."""
    assert q10_api.status.battery is None
    assert q10_api.status.status is None
    assert q10_api.status.fan_level is None

    # Mock the response to refresh
    # battery (122) = 100
    # status (121) = 8 (CHARGING_STATE)
    # fun_level (123) = 2 (NORMAL)
    message = build_message(TESTDATA_DP_REQUEST_DPS)

    # Send a refresh command
    await q10_api.refresh()
    mock_channel.publish.assert_called_once()
    sent_message = mock_channel.publish.call_args[0][0]
    assert sent_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    # Verify refresh payload
    data = json.loads(sent_message.payload)
    assert data
    assert data.get("dps")
    assert data.get("dps").get("102") == {}  # REQUEST_DPS code is 102

    # Push the response message into the queue
    message_queue.put_nowait(message)

    # Wait for the update
    await wait_for_attribute_value(q10_api.status, "battery", 100)

    # Verify trait attributes are updated
    assert q10_api.status.battery == 100
    assert q10_api.status.status == YXDeviceState.CHARGING_STATE
    assert q10_api.status.fan_level == YXFanLevel.NORMAL


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

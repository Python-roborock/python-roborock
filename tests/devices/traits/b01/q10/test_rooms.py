"""Tests for the Q10 B01 rooms trait."""

import asyncio
import base64
import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


def _build_customer_clean_payload() -> str:
    room_block = bytearray(26)
    room_block[0:2] = (42).to_bytes(2, "big")
    room_block[2] = 7
    room_block[3:5] = (3).to_bytes(2, "big")
    room_block[5:7] = (2).to_bytes(2, "big")
    room_block[7] = 1
    room_block[8] = 4
    room_block[9] = 2
    room_block[10] = 0
    room_block[11] = 1

    room_name = bytearray(20)
    encoded_name = b"rr_living_room"
    room_name[0] = len(encoded_name)
    room_name[1 : 1 + len(encoded_name)] = encoded_name

    vertices = bytearray()
    vertices.append(2)
    vertices.extend((100).to_bytes(2, "big"))
    vertices.extend((250).to_bytes(2, "big"))
    vertices.extend((300).to_bytes(2, "big"))
    vertices.extend((450).to_bytes(2, "big"))

    raw = bytes([1]) + bytes(room_block) + bytes(room_name) + bytes(vertices)
    return base64.b64encode(raw).decode("ascii")


def _build_message_with_customer_clean(payload_b64: str) -> RoborockMessage:
    payload = {"dps": {str(B01_Q10_DP.COMMON.code): {str(B01_Q10_DP.CUSTOMER_CLEAN.code): payload_b64}}}
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=json.dumps(payload).encode("utf-8"),
        version=b"B01",
    )


@pytest.fixture
def mock_channel() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def message_queue() -> asyncio.Queue[RoborockMessage]:
    return asyncio.Queue()


@pytest.fixture
def mock_subscribe_stream(mock_channel: AsyncMock, message_queue: asyncio.Queue[RoborockMessage]) -> Mock:
    async def mock_stream() -> AsyncGenerator[RoborockMessage, None]:
        try:
            while True:
                yield await message_queue.get()
        except asyncio.CancelledError:
            return

    mock = Mock(return_value=mock_stream())
    mock_channel.subscribe_stream = mock
    return mock


@pytest_asyncio.fixture
async def q10_api(mock_channel: AsyncMock, mock_subscribe_stream: Mock) -> AsyncGenerator[Q10PropertiesApi, None]:
    api = create(mock_channel)
    await api.start()
    yield api
    await api.close()


async def wait_for_room_count(api: Q10PropertiesApi, value: int, timeout: float = 2.0) -> None:
    for _ in range(int(timeout / 0.1)):
        if api.rooms.parsed_count == value:
            return
        await asyncio.sleep(0.1)
    pytest.fail(f"Timeout waiting for parsed_count={value}")


async def test_rooms_trait_streaming(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    payload_b64 = _build_customer_clean_payload()

    assert q10_api.rooms.parsed_count == 0

    message_queue.put_nowait(_build_message_with_customer_clean(payload_b64))

    await wait_for_room_count(q10_api, 1)

    assert q10_api.rooms.declared_count == 1
    assert q10_api.rooms.raw_length > 0
    room = q10_api.rooms.room_map[42]
    assert room.room_name == "Living Room"
    assert room.room_type == 7
    assert room.clean_order == 3
    assert room.clean_count == 2
    assert room.clean_type == 1
    assert room.fan_level == 4
    assert room.water_level == 2
    assert room.clean_line == 1
    assert room.vertices_num == 2
    assert room.vertices[0].x == pytest.approx(10.0)
    assert room.vertices[0].y == pytest.approx(25.0)
    assert room.vertices[1].x == pytest.approx(30.0)
    assert room.vertices[1].y == pytest.approx(45.0)


def test_rooms_trait_update_listener(q10_api: Q10PropertiesApi) -> None:
    event = asyncio.Event()

    unsubscribe = q10_api.rooms.add_update_listener(event.set)
    q10_api.rooms.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _build_customer_clean_payload()})

    assert event.is_set()
    event.clear()

    unsubscribe()
    q10_api.rooms.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _build_customer_clean_payload()})

    assert not event.is_set()


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="direct_q10_api")
def direct_q10_api_fixture(fake_channel: FakeChannel) -> Q10PropertiesApi:
    return Q10PropertiesApi(fake_channel)  # type: ignore[arg-type]


async def test_rooms_trait_refresh_requests_customer_clean(
    direct_q10_api: Q10PropertiesApi,
    fake_channel: FakeChannel,
) -> None:
    await direct_q10_api.rooms.refresh()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload
    assert json.loads(message.payload.decode()) == {
        "dps": {
            str(B01_Q10_DP.COMMON.code): {
                str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0,
            }
        }
    }


async def test_rooms_api_helpers_reflect_current_room_state(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    message_queue.put_nowait(_build_message_with_customer_clean(_build_customer_clean_payload()))

    await wait_for_room_count(q10_api, 1)

    assert q10_api.rooms.room_names == {42: "Living Room"}
    assert q10_api.rooms.room_map[42].room_name == "Living Room"
    assert q10_api.rooms.get_room(42) is not None
    assert q10_api.rooms.get_room_name(42) == "Living Room"
    assert q10_api.rooms.get_room_name(999, default="unknown") == "unknown"

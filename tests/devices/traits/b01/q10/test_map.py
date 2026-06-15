"""Tests for the Q10 B01 map content trait.

The Q10 map API is push-driven: the device publishes ``MAP_RESPONSE`` messages
and the trait updates its cached state from them via ``update_from_map_response``
(there is no synchronous get-map request).
"""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.map import MapContentTrait
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = Path("tests/map/testdata/b01_q10_trace.bin")


def _map_message(
    payload: bytes, protocol: RoborockMessageProtocol = RoborockMessageProtocol.MAP_RESPONSE
) -> RoborockMessage:
    return RoborockMessage(protocol=protocol, payload=payload, version=b"B01")


def test_update_from_map_response_populates_image_and_rooms() -> None:
    """A pushed 01 01 map packet populates the image, rooms and map data."""
    payload = FIXTURE.read_bytes()
    trait = MapContentTrait()
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))

    assert trait.update_from_map_response(_map_message(payload)) is True

    assert trait.raw_api_response == payload
    assert trait.image_content is not None
    assert trait.image_content[:8] == b"\x89PNG\r\n\x1a\n"
    assert {room.id: room.name for room in trait.rooms} == {2: "Living Room", 3: "Bedroom"}
    assert trait.map_data is not None
    assert len(updates) == 1


def test_update_from_map_response_populates_path_and_position() -> None:
    """A pushed 02 01 trace packet populates the path and robot position."""
    trait = MapContentTrait()
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))

    assert trait.update_from_map_response(_map_message(TRACE_FIXTURE.read_bytes())) is True

    assert [(p.x, p.y) for p in trait.path] == [(169, 0)]
    assert trait.robot_position is not None
    assert (trait.robot_position.x, trait.robot_position.y) == (169, 0)
    assert len(updates) == 1


def test_update_from_map_response_ignores_non_map_messages() -> None:
    """Non-MAP_RESPONSE messages are left for the status path to handle."""
    trait = MapContentTrait()
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))

    rpc = _map_message(b"\x01\x01whatever", protocol=RoborockMessageProtocol.RPC_RESPONSE)
    assert trait.update_from_map_response(rpc) is False

    # An unrecognized MAP_RESPONSE marker is also not consumed.
    assert trait.update_from_map_response(_map_message(b"\x09\x09junk")) is False

    assert trait.image_content is None
    assert not trait.path
    assert not updates


def test_parse_without_data_raises() -> None:
    trait = MapContentTrait()
    with pytest.raises(RoborockException, match="No map payload available"):
        trait.parse_map_content()


# --- Integration through the Q10PropertiesApi subscribe loop -----------------


@pytest.fixture
def message_queue() -> asyncio.Queue[RoborockMessage]:
    return asyncio.Queue()


@pytest.fixture
def mock_channel(message_queue: asyncio.Queue[RoborockMessage]) -> AsyncMock:
    async def mock_stream() -> AsyncGenerator[RoborockMessage, None]:
        while True:
            yield await message_queue.get()

    channel = AsyncMock()
    channel.subscribe_stream = Mock(return_value=mock_stream())
    return channel


@pytest.fixture
async def q10_api(mock_channel: AsyncMock) -> AsyncGenerator[Q10PropertiesApi, None]:
    api = create(mock_channel)
    await api.start()
    yield api
    await api.close()


async def _wait_for(predicate, timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


async def test_subscribe_loop_routes_map_push(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    """A map pushed onto the stream is routed to the map trait by the loop."""
    assert q10_api.map.image_content is None

    message_queue.put_nowait(_map_message(FIXTURE.read_bytes()))

    await _wait_for(lambda: q10_api.map.image_content is not None)
    assert {room.id: room.name for room in q10_api.map.rooms} == {2: "Living Room", 3: "Bedroom"}


async def test_subscribe_loop_routes_trace_push(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[RoborockMessage],
) -> None:
    """A trace pushed onto the stream is routed to the map trait by the loop."""
    assert not q10_api.map.path

    message_queue.put_nowait(_map_message(TRACE_FIXTURE.read_bytes()))

    await _wait_for(lambda: bool(q10_api.map.path))
    assert q10_api.map.robot_position is not None

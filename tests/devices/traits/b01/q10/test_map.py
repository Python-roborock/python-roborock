"""Tests for the Q10 B01 map content trait.

The Q10 map API is push-driven: the device publishes ``MAP_RESPONSE`` messages
and the trait updates its cached state from them via ``update_from_map_response``
(there is no synchronous get-map request).
"""

import asyncio
import io
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from PIL import Image

from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.map import MapContentTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import Q10Point
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


# --- Layers / calibration / rendering ----------------------------------------


def _trait_with_map() -> MapContentTrait:
    """A trait with a map already pushed into it."""
    trait = MapContentTrait()
    trait.update_from_map_response(_map_message(FIXTURE.read_bytes()))
    return trait


def test_map_push_populates_layers() -> None:
    """A pushed map is also decomposed into separable layers."""
    trait = _trait_with_map()
    assert trait.layers is not None
    assert trait.layers.class_counts.get("floor") == 26
    assert {room.id for room in trait.layers.rooms} == {2, 3}


def test_solve_calibration_needs_map_and_dense_path() -> None:
    """No map or too-short a path -> no calibration."""
    trait = MapContentTrait()
    trait.path = [Q10Point(i, 0) for i in range(30)]
    assert trait.solve_calibration() is None  # no layers yet


def test_render_path_on_map_requires_map() -> None:
    trait = MapContentTrait()
    with pytest.raises(RoborockException, match="No map available"):
        trait.render_path_on_map()


def test_render_path_on_map_draws_position() -> None:
    """With a calibration set, the robot position is drawn at the mapped pixel."""
    trait = _trait_with_map()
    # identity-ish calibration: world (x,y) -> pixel (x, 5 - y) in the 8x6 grid.
    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = [Q10Point(1, 2), Q10Point(3, 2)]
    trait.robot_position = Q10Point(3, 2)  # -> pixel (3, 3) -> image (12, 8) at scale 4
    png = trait.render_path_on_map(position_color=(255, 211, 0, 255))
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    assert img.size == (8 * 4, 6 * 4)
    assert img.getpixel((12, 8)) == (255, 211, 0, 255)


def test_load_overlays_places_zones_with_calibration() -> None:
    """Decoded no-go / no-mop zones become pixel-space MapData areas."""
    trait = _trait_with_map()
    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = [Q10Point(1, 1)]  # path origin -> charger

    def rect(zone_type: int, corners: list[tuple[int, int]]) -> bytes:
        out = bytes([zone_type, len(corners)])
        for x, y in corners:
            out += int.to_bytes(x & 0xFFFF, 2, "big") + int.to_bytes(y & 0xFFFF, 2, "big")
        return out.ljust(18, b"\x00")

    blob = bytes([1, 2]) + rect(0, [(0, 0), (4, 0), (4, 4), (0, 4)]) + rect(3, [(1, 1), (2, 1), (2, 2), (1, 2)])
    trait.load_overlays(restricted_zone_up=blob)

    assert len(trait.zones) == 2
    assert trait.map_data is not None
    assert len(trait.map_data.no_go_areas or []) == 1
    assert len(trait.map_data.no_mopping_areas or []) == 1
    # charger = path origin in pixels: (1, 5-1) = (1, 4)
    assert trait.map_data.charger is not None
    assert (trait.map_data.charger.x, trait.map_data.charger.y) == (1.0, 4.0)

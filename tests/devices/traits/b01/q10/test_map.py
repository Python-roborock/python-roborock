"""Tests for the Q10 B01 map content trait.

The Q10 map API is push-driven: the device publishes ``MAP_RESPONSE`` messages
which the protocol layer decodes into typed map/trace packets; the trait updates
its cached state from them via ``update_from_map_packet`` /
``update_from_trace_packet`` (there is no synchronous get-map request). These
tests cover that state management; the pixel/geometry work it drives is tested in
``tests/map/test_b01_q10_render.py``.
"""

import asyncio
import base64
from collections.abc import AsyncGenerator
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from roborock.cli import _await_q10_map_push, cli
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.map import MapContentTrait, MapDpsTrait
from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import (
    Q10HeaderCalibration,
    Q10MapPacket,
    Q10Point,
    Q10TracePacket,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.protocols.b01_q10_protocol import Q10Message

from .conftest import FakeB01Q10Channel

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_SESSION_FIXTURE = Path("tests/map/testdata/b01_q10_trace_session.bin")

# A header calibration whose pixel origin (0, 5) is usable (not a keepalive
# frame), so a short path can calibrate the fixture map.
_USABLE_HEADER = Q10HeaderCalibration(origin_x=0, origin_y=50, resolution=5, charger_x=0, charger_y=0, charger_phi=0)


def _trait_with_map() -> MapContentTrait:
    """A trait with the fixture map already pushed into it."""
    trait = MapContentTrait()
    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    return trait


def _floor_world_points(packet: Q10MapPacket, cal: GridCalibration, count: int) -> list[Q10Point]:
    """``count`` world points lying on the map's floor under ``cal``."""
    layers = packet.layers
    floor = [
        (px, py)
        for py in range(layers.height)
        for px in range(layers.width)
        if layers.cell_class(layers.grid[py * layers.width + px]) == "floor"
    ]
    return [Q10Point(*(int(v) for v in cal.pixel_to_world(px, py))) for px, py in floor[:count]]


def test_update_from_map_packet_populates_image_and_rooms() -> None:
    """A pushed 01 01 map packet populates the image, rooms and map data."""
    packet = parse_map_packet(FIXTURE.read_bytes())
    trait = MapContentTrait()
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))

    trait.update_from_map_packet(packet)

    assert trait.image_content is not None
    assert trait.image_content[:8] == b"\x89PNG\r\n\x1a\n"
    assert {room.id: room.name for room in trait.rooms} == {2: "Living Room", 3: "Bedroom"}
    assert len(updates) == 1


def test_update_from_trace_packet_populates_path_and_position() -> None:
    """A pushed 02 01 trace packet populates the path, position and heading."""
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    trait = MapContentTrait()
    updates: list[None] = []
    trait.add_update_listener(lambda: updates.append(None))

    trait.update_from_trace_packet(trace)

    assert len(trait.path) == 14
    assert (trait.path[0].x, trait.path[0].y) == (41, 64)
    assert trait.robot_position is not None
    assert (trait.robot_position.x, trait.robot_position.y) == (276, -1)
    assert trait.robot_heading == -34
    assert len(updates) == 1


def test_q10_position_is_available_as_top_level_cli_command() -> None:
    assert "q10-position" in cli.commands


# --- CLI push waiting --------------------------------------------------------


class _FakeQ10Properties:
    def __init__(self) -> None:
        self.map = MapContentTrait()
        self.refresh_count = 0

    async def refresh(self) -> None:
        self.refresh_count += 1


class _FakeQ10PropertiesWithTrace(_FakeQ10Properties):
    async def refresh(self) -> None:
        await super().refresh()
        self.map.update_from_trace_packet(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))


async def test_await_q10_map_push_waits_for_fresh_update() -> None:
    """A cached trace alone is not treated as a successful new map push."""
    properties = _FakeQ10Properties()
    properties.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1, 2)]))

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties), lambda: bool(properties.map.path), timeout=0.01
    )

    assert got_trace is False
    assert properties.refresh_count == 1


async def test_await_q10_map_push_returns_true_after_update() -> None:
    properties = _FakeQ10PropertiesWithTrace()

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties), lambda: bool(properties.map.path), timeout=0.01
    )

    assert got_trace is True
    assert len(properties.map.path) == 14


async def test_await_q10_map_push_can_fall_back_to_cached_map_on_timeout() -> None:
    properties = _FakeQ10Properties()
    properties.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    got_map = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: properties.map.image_content is not None,
        timeout=0.01,
        allow_cached_on_timeout=True,
    )

    assert got_map is True
    assert properties.refresh_count == 1


# --- Integration through the Q10PropertiesApi subscribe loop -----------------


@pytest.fixture(name="message_queue")
def message_queue_fixture() -> asyncio.Queue[Q10Message]:
    return asyncio.Queue()


@pytest.fixture(name="mock_channel")
def mock_channel_fixture(message_queue: asyncio.Queue[Q10Message]) -> FakeB01Q10Channel:
    channel = FakeB01Q10Channel()

    async def mock_stream() -> AsyncGenerator[Q10Message, None]:
        while True:
            yield await message_queue.get()

    setattr(channel, "subscribe_stream", Mock(side_effect=mock_stream))
    return channel


@pytest.fixture(name="q10_api")
async def q10_api_fixture(mock_channel: FakeB01Q10Channel) -> AsyncGenerator[Q10PropertiesApi, None]:
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
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """A map pushed onto the stream is routed to the map trait by the loop."""
    assert q10_api.map.image_content is None

    message_queue.put_nowait(parse_map_packet(FIXTURE.read_bytes()))

    await _wait_for(lambda: q10_api.map.image_content is not None)
    assert {room.id: room.name for room in q10_api.map.rooms} == {2: "Living Room", 3: "Bedroom"}


async def test_subscribe_loop_routes_trace_push(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """A trace pushed onto the stream is routed to the map trait by the loop."""
    assert not q10_api.map.path

    message_queue.put_nowait(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

    await _wait_for(lambda: bool(q10_api.map.path))
    assert q10_api.map.robot_position is not None


# --- Source composition + rendering ------------------------------------------


def test_trace_without_map_is_retained_without_rendering() -> None:
    """A trace is retained even when no map is available to render yet."""
    trait = MapContentTrait()
    trait.update_from_trace_packet(Q10TracePacket(points=[Q10Point(i, 0) for i in range(30)]))
    assert len(trait.path) == 30
    assert trait.image_content is None


def test_trace_update_projects_short_path_using_header() -> None:
    """A map header and short trace are sufficient to render a path."""
    trait = MapContentTrait()
    packet = replace(parse_map_packet(FIXTURE.read_bytes()), header_calibration=_USABLE_HEADER)
    trait.update_from_map_packet(packet)
    base = trait.image_content
    assert base is not None
    true = GridCalibration(resolution=20.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.update_from_trace_packet(Q10TracePacket(points=_floor_world_points(packet, true, 6)))
    assert len(trait.path) < 20  # far too short for the full origin+resolution fit

    assert trait.image_content is not None
    assert trait.image_content != base


def test_short_trace_without_header_cannot_be_projected() -> None:
    """Without a header origin a short trace cannot be placed on the map."""
    packet = parse_map_packet(FIXTURE.read_bytes())
    trait = MapContentTrait()
    trait.update_from_map_packet(packet)  # the fixture header is a keepalive frame
    base = trait.image_content
    true = GridCalibration(resolution=10.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.update_from_trace_packet(Q10TracePacket(points=_floor_world_points(packet, true, 6)))
    assert trait.image_content == base


# --- Overlays ----------------------------------------------------------------


def test_load_overlays_places_zones_after_calibration() -> None:
    """Decoded no-go / no-mop zones are drawn once the sources calibrate."""
    map_dps = MapDpsTrait()
    trait = MapContentTrait(map_dps)
    packet = replace(parse_map_packet(FIXTURE.read_bytes()), header_calibration=_USABLE_HEADER)
    trait.update_from_map_packet(packet)
    true = GridCalibration(resolution=20.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.update_from_trace_packet(Q10TracePacket(points=_floor_world_points(packet, true, 6)))
    before = trait.image_content
    assert before is not None

    def rect(zone_type: int, corners: list[tuple[int, int]]) -> bytes:
        out = bytes([zone_type, len(corners)])
        for x, y in corners:
            out += int.to_bytes(x & 0xFFFF, 2, "big") + int.to_bytes(y & 0xFFFF, 2, "big")
        return out.ljust(18, b"\x00")

    blob = bytes([1, 1]) + rect(0, [(0, 0), (40, 0), (40, 40), (0, 40)])
    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: base64.b64encode(blob).decode()})

    assert len(map_dps.zones) == 1
    assert trait.image_content != before


def test_load_overlays_partial_update_keeps_existing_zones() -> None:
    """A status push without the zone DP (None) must not wipe loaded zones."""
    map_dps = MapDpsTrait()
    blob = (
        bytes([1, 1])
        + bytes([0, 4])
        + b"".join(int.to_bytes(v & 0xFFFF, 2, "big") for xy in [(0, 0), (4, 0), (4, 4), (0, 4)] for v in xy)
    )
    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: base64.b64encode(blob).decode()})
    assert len(map_dps.zones) == 1
    # A later partial update carrying only the (empty) virtual-wall DP.
    map_dps.update_from_dps({B01_Q10_DP.VIRTUAL_WALL_UP: "AA=="})
    assert len(map_dps.zones) == 1  # zones preserved
    assert map_dps.virtual_walls == []


def test_map_dps_trait_updates_high_level_map_content() -> None:
    """The low-level DPS trait notifies the dependent high-level map trait."""
    map_dps = MapDpsTrait()
    trait = MapContentTrait(map_dps)
    blob = (
        bytes([1, 1])
        + bytes([0, 4])
        + b"".join(int.to_bytes(v & 0xFFFF, 2, "big") for xy in [(0, 0), (4, 0), (4, 4), (0, 4)] for v in xy)
    )
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: base64.b64encode(blob).decode()})

    assert len(map_dps.zones) == 1
    assert notified  # listeners learn the overlays changed


def test_map_dps_push_without_overlay_data_points_is_noop() -> None:
    """A DPS push carrying neither overlay DP leaves both traits untouched."""
    map_dps = MapDpsTrait()
    trait = MapContentTrait(map_dps)
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    map_dps.update_from_dps({B01_Q10_DP.BATTERY: 50})

    assert map_dps.zones == []
    assert map_dps.virtual_walls == []
    assert not notified

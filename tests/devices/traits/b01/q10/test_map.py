"""Tests for the Q10 B01 map content trait.

Map list data and map content have independent refresh schedules. Content
requests use a stored map ID, and the device sends the data later in a
``MAP_RESPONSE`` packet. These tests cover that state management. The render
details are tested in ``tests/map/test_b01_q10_render.py``.
"""

import asyncio
import base64
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest

from roborock.cli import _await_q10_map_push, cli
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXDeviceState
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.command import CommandTrait
from roborock.devices.traits.b01.q10.map import MapContentTrait, MapDpsTrait
from roborock.devices.traits.b01.q10.maps import MapsTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    Q10Point,
    Q10TracePacket,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.map.b01_q10_render import Q10MapOverlays
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate, Q10Message

from .conftest import FakeB01Q10Channel

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_SESSION_FIXTURE = Path("tests/map/testdata/b01_q10_trace_session.bin")


def _map_trait(map_dps: MapDpsTrait | None = None) -> MapContentTrait:
    """Create map content with a stored map ID for tests that do not perform I/O."""
    command = cast(CommandTrait, Mock(spec=CommandTrait))
    maps = MapsTrait(command)
    maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    return MapContentTrait(map_dps or MapDpsTrait(), maps, command)


def _zone_blob() -> str:
    """Return one base64-encoded restricted-zone DPS value."""
    vertices = [(0, 0), (40, 0), (40, 40), (0, 40)]
    record = bytes([0, len(vertices)]) + b"".join(
        int.to_bytes(value & 0xFFFF, 2, "big") for point in vertices for value in point
    )
    return base64.b64encode(bytes([1, 1]) + record).decode()


@pytest.fixture(name="render_map")
def render_map_fixture() -> Generator[Mock, None, None]:
    with patch("roborock.devices.traits.b01.q10.map.render_q10_map") as render:
        yield render


def test_update_from_map_packet_populates_image_and_rooms() -> None:
    """A pushed 01 01 map packet populates the image and rooms."""
    packet = parse_map_packet(FIXTURE.read_bytes())
    trait = _map_trait()
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
    trait = _map_trait()
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
        command = cast(CommandTrait, Mock(spec=CommandTrait))
        self.maps = MapsTrait(command)
        self.maps.update_from_dps(
            {
                B01_Q10_DP.MULTI_MAP: {
                    "data": [{"id": "12345"}],
                    "op": "list",
                    "result": 1,
                }
            }
        )
        self.map = MapContentTrait(MapDpsTrait(), self.maps, command)
        self.refresh_count = 0

        async def refresh_map() -> None:
            self.refresh_count += 1

        self.map.refresh = refresh_map  # type: ignore[method-assign]


class _FakeQ10PropertiesWithTrace(_FakeQ10Properties):
    def __init__(self) -> None:
        super().__init__()

        async def refresh_map() -> None:
            self.refresh_count += 1
            self.map.update_from_trace_packet(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

        self.map.refresh = refresh_map  # type: ignore[method-assign]


class _FakeQ10PropertiesWithoutMapId:
    def __init__(self) -> None:
        command = cast(CommandTrait, Mock(spec=CommandTrait))
        self.maps = MapsTrait(command)
        self.map = MapContentTrait(MapDpsTrait(), self.maps, command)
        self.maps_refresh_count = 0
        self.map_refresh_count = 0

        async def refresh_maps() -> None:
            self.maps_refresh_count += 1
            self.maps.update_from_dps(
                {
                    B01_Q10_DP.MULTI_MAP: {
                        "data": [{"id": "12345"}],
                        "op": "list",
                        "result": 1,
                    }
                }
            )

        async def refresh_map() -> None:
            self.map_refresh_count += 1
            self.map.update_from_trace_packet(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

        self.maps.refresh = refresh_maps  # type: ignore[method-assign]
        self.map.refresh = refresh_map  # type: ignore[method-assign]


async def test_await_q10_map_push_waits_for_fresh_update() -> None:
    """A cached trace alone is not treated as a successful new map push."""
    properties = _FakeQ10Properties()
    properties.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1, 2)]))

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: bool(properties.map.path),
        timeout=0.01,
    )

    assert got_trace is False
    assert properties.refresh_count == 1


async def test_await_q10_map_push_returns_true_after_update() -> None:
    properties = _FakeQ10PropertiesWithTrace()

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: bool(properties.map.path),
        timeout=0.01,
    )

    assert got_trace is True
    assert len(properties.map.path) == 14


async def test_await_q10_map_push_requests_map_list_only_on_first_use() -> None:
    """Content gets the list first only when no stored map ID is available."""
    properties = _FakeQ10PropertiesWithoutMapId()

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: bool(properties.map.path),
        timeout=0.01,
    )

    assert got_trace is True
    assert properties.maps_refresh_count == 1
    assert properties.map_refresh_count == 1


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


async def test_map_list_and_content_refresh_are_independent(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """A list update stores an ID but does not request map content."""
    await q10_api.maps.refresh()
    assert mock_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
        )
    ]

    message_queue.put_nowait(
        Q10DpsUpdate(
            dps={
                B01_Q10_DP.MULTI_MAP: {
                    "data": [
                        {"id": "12345", "name": "Current", "timestamp": 1},
                        {"id": "67890", "name": "Other", "timestamp": 2},
                    ],
                    "op": "list",
                    "result": 1,
                }
            }
        )
    )

    await _wait_for(lambda: q10_api.maps.current_map_id == "12345")
    assert len(mock_channel.published_commands) == 1

    await q10_api.map.refresh()

    assert mock_channel.published_commands[1] == (
        B01_Q10_DP.COMMON,
        {
            str(B01_Q10_DP.MULTI_MAP.code): {
                "op": "get",
                "id": "12345",
            }
        },
    )
    assert q10_api.maps.current_map_id == "12345"


async def test_empty_map_list_does_not_request_content(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """An empty list leaves map content unavailable."""
    message_queue.put_nowait(
        Q10DpsUpdate(
            dps={
                B01_Q10_DP.MULTI_MAP: {
                    "data": [],
                    "op": "list",
                    "result": 1,
                }
            }
        )
    )

    await asyncio.sleep(0.01)
    assert q10_api.maps.current_map_id is None
    assert mock_channel.published_commands == []


async def test_map_content_refresh_requires_stored_map_id(q10_api: Q10PropertiesApi) -> None:
    """Content cannot be requested until the map list supplies an ID."""
    with pytest.raises(RoborockException, match="map list is available"):
        await q10_api.map.refresh()


async def test_map_content_refresh_requests_are_not_rate_limited(q10_api: Q10PropertiesApi) -> None:
    """The caller controls content cadence; each refresh sends a get request."""
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    with patch.object(q10_api.command, "send") as send:
        await q10_api.map.refresh()
        await q10_api.map.refresh()

    assert send.await_count == 2


def test_map_get_ack_does_not_replace_saved_map_list(q10_api: Q10PropertiesApi) -> None:
    """A content acknowledgement cannot remove the stored map ID."""
    q10_api._handle_message(
        Q10DpsUpdate(
            dps={
                B01_Q10_DP.MULTI_MAP: {
                    "data": [{"id": "12345"}],
                    "op": "list",
                    "result": 1,
                }
            }
        )
    )

    q10_api._handle_message(
        Q10DpsUpdate(
            dps={
                B01_Q10_DP.MULTI_MAP: {
                    "data": [],
                    "op": "get",
                    "result": 1,
                }
            }
        )
    )

    assert q10_api.maps.current_map_id == "12345"


# --- Source composition + rendering ------------------------------------------


def test_trace_without_map_is_retained_without_rendering() -> None:
    """A trace is retained even when no map is available to render yet."""
    trait = _map_trait()
    trait.update_from_trace_packet(Q10TracePacket(points=[Q10Point(i, 0) for i in range(30)]))
    assert len(trait.path) == 30
    assert trait.image_content is None


def test_render_failure_clears_stale_image(render_map: Mock) -> None:
    """A failed composition cannot leave an image from older source data."""
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = Q10TracePacket(points=[Q10Point(1, 2)])
    trait = _map_trait()

    render_map.side_effect = [b"initial image", RoborockException("invalid map")]

    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    assert trait.path == trace.points
    assert trait.image_content is None


# --- Overlays ----------------------------------------------------------------


def test_map_dps_update_renders_decoded_overlays(render_map: Mock) -> None:
    """A DPS update recomposes an existing map with decoded overlays."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    notified: list[None] = []
    trait.add_update_listener(lambda: notified.append(None))

    render_map.side_effect = [b"base image", b"image with overlays"]

    trait.update_from_map_packet(packet)
    notified.clear()
    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob()})

    assert len(map_dps.overlays.zones) == 1
    assert trait.image_content == b"image with overlays"
    assert notified == [None]
    assert render_map.call_count == 2
    assert render_map.call_args.args[0] is packet
    assert render_map.call_args.args[1] is None
    assert render_map.call_args.args[2] is map_dps.overlays


def test_map_dps_blobs_are_decoded_only_when_dps_arrives() -> None:
    """Map and trace renders reuse the overlays decoded by the DPS trait."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)

    with (
        patch("roborock.devices.traits.b01.q10.map.parse_zone_blob", return_value=[]) as parse_zones,
        patch("roborock.devices.traits.b01.q10.map.parse_virtual_wall_blob", return_value=[]) as parse_walls,
    ):
        map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob()})
        trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
        trait.update_from_trace_packet(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

    parse_zones.assert_called_once_with(_zone_blob())
    parse_walls.assert_called_once_with(None)


def test_load_overlays_partial_update_keeps_existing_zones() -> None:
    """A status push without the zone DP (None) must not wipe loaded zones."""
    map_dps = MapDpsTrait()
    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob()})
    assert len(map_dps.overlays.zones) == 1
    # A later partial update carrying only the (empty) virtual-wall DP.
    map_dps.update_from_dps({B01_Q10_DP.VIRTUAL_WALL_UP: "AA=="})
    assert len(map_dps.overlays.zones) == 1  # zones preserved
    assert map_dps.overlays.virtual_walls == ()


def test_map_dps_update_without_map_does_not_notify_map_content() -> None:
    """A DPS update cannot change high-level content before a map arrives."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob()})

    assert len(map_dps.overlays.zones) == 1
    assert not notified


def test_map_dps_push_without_overlay_data_points_is_noop() -> None:
    """A DPS push carrying neither overlay DP leaves both traits untouched."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    map_dps.update_from_dps({B01_Q10_DP.BATTERY: 50})

    assert map_dps.overlays == Q10MapOverlays()
    assert not notified


async def test_charging_status_renders_robot_at_dock(render_map: Mock) -> None:
    """Charging status adds the idle robot marker without inventing a path."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    updated = asyncio.Event()
    trait.add_update_listener(updated.set)
    render_map.side_effect = [b"map with dock", b"map with docked robot"]

    trait.update_from_map_packet(packet)
    updated.clear()
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})
    map_dps.update_from_dps({B01_Q10_DP.BATTERY: 50})

    await asyncio.wait_for(updated.wait(), timeout=1)

    assert trait.image_content == b"map with docked robot"
    assert trait.path == []
    assert render_map.call_count == 2
    assert render_map.call_args.kwargs["robot_at_dock"] is True


def test_docked_state_hides_trace_only_from_rendering(render_map: Mock) -> None:
    """A docked render omits the valid trace without deleting source data."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = Q10TracePacket(points=[Q10Point(1, 2), Q10Point(3, 4)])
    render_map.return_value = b"map"

    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)
    assert render_map.call_args.args[1] is trace

    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})

    assert trait.path == trace.points
    assert render_map.call_args.args[1] is None
    assert render_map.call_args.kwargs["robot_at_dock"] is True


def test_late_trace_is_retained_but_hidden_while_docked(render_map: Mock) -> None:
    """A late trace stays available but is not part of a docked render."""
    map_dps = MapDpsTrait()
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})
    trait = _map_trait(map_dps)
    trace = Q10TracePacket(points=[Q10Point(1, 2)])
    render_map.return_value = b"map"

    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    trait.update_from_trace_packet(trace)

    assert trait.path == trace.points
    assert render_map.call_args.args[1] is None


def test_emptying_state_keeps_robot_at_dock(render_map: Mock) -> None:
    """Dock emptying must not briefly remove the docked robot marker."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())

    render_map.side_effect = [b"map with dock", b"map while emptying"]

    trait.update_from_map_packet(packet)
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.EMPTYING_THE_BIN.code})

    assert trait.image_content == b"map while emptying"
    assert render_map.call_args.kwargs["robot_at_dock"] is True


async def test_combined_status_and_overlay_update_renders_once(render_map: Mock) -> None:
    """One map DPS update publishes the complete new rendering state."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    updated = asyncio.Event()
    trait.add_update_listener(updated.set)
    render_map.side_effect = [b"base map", b"combined map"]

    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    updated.clear()
    map_dps.update_from_dps(
        {
            B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code,
            B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob(),
        }
    )

    await asyncio.wait_for(updated.wait(), timeout=1)

    assert render_map.call_count == 2
    assert len(render_map.call_args.args[2].zones) == 1
    assert render_map.call_args.kwargs["robot_at_dock"] is True
    assert trait.image_content == b"combined map"


def test_map_content_trait_as_dict_camelizes_child_keys() -> None:
    """MapContentTrait.as_dict() camelizes nested child keys (e.g. rawName, pixelValue)."""
    trait = _map_trait()
    packet = parse_map_packet(FIXTURE.read_bytes())
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(
        Q10TracePacket(
            points=[Q10Point(x=100, y=200), Q10Point(x=150, y=250)],
            sequence=0,
        )
    )

    data = trait.as_dict()
    assert len(data["rooms"]) == 2
    assert data["rooms"][0] == {
        "id": 2,
        "pixelCount": 9,
        "pixelValue": 8,
        "rawName": "rr_living_room",
    }
    assert data["path"] == [{"x": 100, "y": 200}, {"x": 150, "y": 250}]
    assert data["robotPosition"] == {"x": 150, "y": 250}

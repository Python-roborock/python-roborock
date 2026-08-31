"""Tests for the Q10 B01 map content trait.

Map list data and current-map content have independent refresh schedules. The
device sends map data later in a ``MAP_RESPONSE`` packet. These tests cover
that state management; rendering is tested separately.
"""

import asyncio
import base64
from collections.abc import AsyncGenerator, Generator
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest

from roborock.cli import _await_q10_map_push, cli
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXDeviceState
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.command import CommandTrait
from roborock.devices.traits.b01.q10.map import MapContentTrait, MapDpsTrait
from roborock.devices.traits.b01.q10.maps import MapsTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10MapPacketKind,
    Q10Obstacle,
    Q10Point,
    Q10TracePacket,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.map.b01_q10_overlays import (
    Q10RestrictedZone,
    Q10RestrictionType,
    Q10VirtualWall,
)
from roborock.map.b01_q10_render import Q10MapOverlays
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate, Q10Message

from .conftest import FakeB01Q10Channel

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_SESSION_FIXTURE = Path("tests/map/testdata/b01_q10_trace_session.bin")


def _map_trait(map_dps: MapDpsTrait | None = None) -> MapContentTrait:
    """Create map content for tests that do not perform I/O."""
    command = cast(CommandTrait, Mock(spec=CommandTrait))
    return MapContentTrait(map_dps or MapDpsTrait(), command)


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
    assert {room.id: room.name for room in trait.rooms} == {2: "Living Room", 3: "bedroom"}
    assert len(updates) == 1


def test_update_from_map_packet_exposes_obstacles() -> None:
    """Live callers receive the same decoded obstacles used by rendering."""
    packet = replace(
        parse_map_packet(FIXTURE.read_bytes()),
        obstacles=[Q10Obstacle(250, -300), Q10Obstacle(-50, 100)],
    )
    trait = _map_trait()

    trait.update_from_map_packet(packet)

    assert trait.obstacles == packet.obstacles
    assert trait.as_dict()["obstacles"] == [
        {"x": 250, "y": -300},
        {"x": -50, "y": 100},
    ]
    exposed = trait.obstacles
    exposed.clear()
    assert trait.obstacles == packet.obstacles


def test_live_map_trait_rejects_archived_packet() -> None:
    """Direct callers cannot bypass API routing and replace live map state."""
    payload = FIXTURE.read_bytes()
    archived = parse_map_packet(b"\x03\x01" + payload[2:])

    with pytest.raises(ValueError, match="Expected a current Q10 map packet"):
        _map_trait().update_from_map_packet(archived)


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


@pytest.mark.parametrize(
    "status",
    [
        YXDeviceState.CLEANING,
        YXDeviceState.SWEEPING,
        YXDeviceState.MOPPING,
        YXDeviceState.SWEEP_AND_MOP,
        YXDeviceState.PAUSED,
        YXDeviceState.TRANSITIONING,
    ],
)
def test_current_room_is_available_during_active_cleaning_states(status: YXDeviceState) -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    map_dps.update_from_dps({B01_Q10_DP.STATUS: status.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        return_value=packet.rooms[0],
    ) as resolve:
        assert trait.current_room == packet.rooms[0]
        resolve.assert_called_once_with(packet, trace)


@pytest.mark.parametrize(
    "status",
    [
        None,
        YXDeviceState.UNKNOWN,
        YXDeviceState.IDLE,
        YXDeviceState.RETURNING_HOME,
        YXDeviceState.RELOCATING,
        YXDeviceState.CHARGING,
        YXDeviceState.EMPTYING_THE_BIN,
    ],
)
def test_current_room_is_unavailable_outside_active_cleaning(
    status: YXDeviceState | None,
) -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    if status is not None:
        map_dps.update_from_dps({B01_Q10_DP.STATUS: status.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

    with patch("roborock.devices.traits.b01.q10.map.resolve_q10_current_room") as resolve:
        assert trait.current_room is None
        resolve.assert_not_called()


def test_current_room_handles_status_arriving_after_map_and_trace() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        side_effect=lambda *_: replace(packet.rooms[0]),
    ):
        assert trait.current_room is None
        map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
        assert trait.current_room == packet.rooms[0]


def test_current_room_handles_map_arriving_after_status_and_trace() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        side_effect=lambda *_: replace(packet.rooms[0]),
    ):
        assert trait.current_room is None
        trait.update_from_map_packet(packet)
        assert trait.current_room == packet.rooms[0]


@pytest.mark.parametrize(
    "ending_status",
    [YXDeviceState.UNKNOWN, YXDeviceState.IDLE, YXDeviceState.RETURNING_HOME],
)
def test_leaving_cleaning_clears_current_room_without_reusing_stale_trace(
    ending_status: YXDeviceState,
) -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        side_effect=lambda *_: replace(packet.rooms[0]),
    ) as resolve:
        assert trait.current_room == packet.rooms[0]
        map_dps.update_from_dps({B01_Q10_DP.STATUS: ending_status.code})
        assert trait.current_room is None
        assert trait.path == trace.points
        assert resolve.call_count == 1


def test_new_cleaning_session_waits_for_a_fresh_trace() -> None:
    """A status-first new session cannot reuse the prior session's position."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    old_trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    new_trace = replace(old_trace, heading=old_trace.heading + 1)
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(old_trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        side_effect=lambda *_: replace(packet.rooms[0]),
    ) as resolve:
        assert trait.current_room == packet.rooms[0]
        map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.IDLE.code})
        map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
        assert trait.current_room is None
        trait.update_from_trace_packet(new_trace)
        assert trait.current_room == packet.rooms[0]
        assert resolve.call_count == 2


def test_current_room_requires_both_map_and_trace() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})

    assert trait.current_room is None
    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    assert trait.current_room is None


def test_current_room_is_a_defensive_copy_and_serializes_for_consumers() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        side_effect=lambda *_: replace(packet.rooms[0]),
    ):
        exposed = trait.current_room
        assert exposed is not None
        assert exposed is not packet.rooms[0]
        exposed.raw_name = "mutated"
        assert trait.current_room is not None
        assert trait.current_room.raw_name == "rr_living_room"
        assert trait.current_room.name == "Living Room"
        assert trait.as_dict()["currentRoom"] == packet.rooms[0].as_dict()
        assert "currentRoom" not in trait.as_dict({"currentRoom"})


def test_current_room_serializes_none_when_unknown() -> None:
    assert _map_trait().as_dict()["currentRoom"] is None


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
        self.map = MapContentTrait(MapDpsTrait(), command)
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


async def test_await_q10_map_push_waits_for_fresh_update() -> None:
    """A cached trace alone is not treated as a successful new map push."""
    properties = _FakeQ10Properties()
    properties.map.update_from_trace_packet(Q10TracePacket(points=[Q10Point(1, 2)]))

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: bool(properties.map.path),
        lambda: properties.map.trace_revision,
        timeout=0.01,
    )

    assert got_trace is False
    assert properties.refresh_count == 1


async def test_await_q10_map_push_returns_true_after_update() -> None:
    properties = _FakeQ10PropertiesWithTrace()

    got_trace = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: bool(properties.map.path),
        lambda: properties.map.trace_revision,
        timeout=0.01,
    )

    assert got_trace is True
    assert len(properties.map.path) == 14


async def test_await_q10_map_push_can_fall_back_to_cached_map_on_timeout() -> None:
    properties = _FakeQ10Properties()
    properties.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    got_map = await _await_q10_map_push(
        cast(Q10PropertiesApi, properties),
        lambda: properties.map.image_content is not None,
        lambda: properties.map.map_revision,
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
    assert {room.id: room.name for room in q10_api.map.rooms} == {2: "Living Room", 3: "bedroom"}


async def test_archived_map_pushes_cannot_overwrite_live_map(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """03/04 detail packets are isolated from the current live-map trait."""
    current_bytes = FIXTURE.read_bytes()
    current = parse_map_packet(current_bytes)
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    clean_record = parse_map_packet(b"\x03\x01" + current_bytes[2:])
    saved_map = parse_map_packet(b"\x04\x01" + current_bytes[2:])

    message_queue.put_nowait(current)
    message_queue.put_nowait(trace)
    await _wait_for(lambda: q10_api.map.image_content is not None and bool(q10_api.map.path))
    live_image = q10_api.map.image_content
    live_rooms = list(q10_api.map.rooms)
    live_path = list(q10_api.map.path)
    live_position = q10_api.map.robot_position
    live_heading = q10_api.map.robot_heading
    live_updates: list[None] = []
    clean_record_updates: list[None] = []
    saved_map_updates: list[None] = []
    q10_api.map.add_update_listener(lambda: live_updates.append(None))
    q10_api.clean_history.add_update_listener(lambda: clean_record_updates.append(None))
    q10_api.maps.add_update_listener(lambda: saved_map_updates.append(None))

    message_queue.put_nowait(clean_record)
    message_queue.put_nowait(saved_map)
    await _wait_for(lambda: q10_api.maps.detail_packet is not None)

    assert q10_api.map.image_content == live_image
    assert q10_api.map.rooms == live_rooms
    assert q10_api.map.path == live_path
    assert q10_api.map.robot_position == live_position
    assert q10_api.map.robot_heading == live_heading
    assert live_updates == []
    assert q10_api.clean_history.detail_packet is not None
    assert q10_api.clean_history.detail_packet.kind is Q10MapPacketKind.CLEAN_RECORD_DETAIL
    assert q10_api.clean_history.detail_image_content is not None
    assert q10_api.maps.detail_packet is not None
    assert q10_api.maps.detail_packet.kind is Q10MapPacketKind.SAVED_MAP_DETAIL
    assert q10_api.maps.detail_image_content is not None
    assert clean_record_updates == [None]
    assert saved_map_updates == [None]


def test_archive_owners_reject_wrong_packet_kinds(q10_api: Q10PropertiesApi) -> None:
    """Semantic archive traits reject packets owned by another map stream."""
    current = parse_map_packet(FIXTURE.read_bytes())

    with pytest.raises(ValueError, match="clean-record detail"):
        q10_api.clean_history.update_from_map_packet(current)
    with pytest.raises(ValueError, match="saved-map detail"):
        q10_api.maps.update_from_map_packet(current)


def test_saved_map_detail_exposes_obstacles(q10_api: Q10PropertiesApi) -> None:
    payload = FIXTURE.read_bytes()
    packet = replace(
        parse_map_packet(b"\x04\x01" + payload[2:]),
        obstacles=[Q10Obstacle(100, -200)],
    )

    q10_api.maps.update_from_map_packet(packet)

    assert q10_api.maps.detail_obstacles == packet.obstacles
    exposed = q10_api.maps.detail_obstacles
    exposed.clear()
    assert q10_api.maps.detail_obstacles == packet.obstacles


def test_archived_map_details_do_not_expose_or_replace_current_room(q10_api: Q10PropertiesApi) -> None:
    payload = FIXTURE.read_bytes()
    current = parse_map_packet(payload)
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    q10_api._map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    q10_api.map.update_from_map_packet(current)
    q10_api.map.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        return_value=current.rooms[0],
    ):
        assert q10_api.map.current_room == current.rooms[0]
        q10_api._handle_message(parse_map_packet(b"\x03\x01" + payload[2:]))
        q10_api._handle_message(parse_map_packet(b"\x04\x01" + payload[2:]))
        assert q10_api.map.current_room == current.rooms[0]

    assert not hasattr(q10_api.clean_history, "current_room")
    assert not hasattr(q10_api.maps, "current_room")


def test_all_q10_map_views_share_the_injected_render_config(
    fake_channel: FakeB01Q10Channel,
) -> None:
    config = B01Q10MapParserConfig(map_scale=2)
    api = Q10PropertiesApi(fake_channel, map_parser_config=config)
    payload = FIXTURE.read_bytes()

    with (
        patch("roborock.devices.traits.b01.q10.map.render_q10_map", return_value=b"map") as live_render,
        patch(
            "roborock.devices.traits.b01.q10.clean_history.render_q10_map",
            return_value=b"history",
        ) as history_render,
        patch("roborock.devices.traits.b01.q10.maps.render_q10_map", return_value=b"saved") as saved_render,
    ):
        api._handle_message(parse_map_packet(payload))
        api._handle_message(parse_map_packet(b"\x03\x01" + payload[2:]))
        api._handle_message(parse_map_packet(b"\x04\x01" + payload[2:]))

    assert live_render.call_args.kwargs["config"] is config
    assert history_render.call_args.kwargs["config"] is config
    assert saved_render.call_args.kwargs["config"] is config


async def test_subscribe_loop_routes_trace_push(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """A trace pushed onto the stream is routed to the map trait by the loop."""
    assert not q10_api.map.path

    message_queue.put_nowait(parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes()))

    await _wait_for(lambda: bool(q10_api.map.path))
    assert q10_api.map.robot_position is not None


async def test_map_list_and_current_content_refresh_are_independent(
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

    assert mock_channel.published_commands[1] == (B01_Q10_DP.REQUEST_DPS, {})
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


async def test_map_content_refresh_does_not_require_stored_map_id(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
) -> None:
    """Current-map refresh is read-only and independent of saved-map state."""
    await q10_api.map.refresh()

    assert mock_channel.published_commands == [(B01_Q10_DP.REQUEST_DPS, {})]


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


async def test_saved_map_detail_refresh_uses_current_map_id(q10_api: Q10PropertiesApi) -> None:
    """Saved-map detail uses the independently validated select request."""
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
        await q10_api.maps.refresh_detail()

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.MULTI_MAP.code): {"op": "select", "id": "12345"}},
    )


async def test_saved_map_detail_refresh_accepts_any_listed_map_id(q10_api: Q10PropertiesApi) -> None:
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}, {"id": "67890"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    assert [map_info.id for map_info in q10_api.maps.map_list] == ["12345", "67890"]

    with patch.object(q10_api.command, "send") as send:
        await q10_api.maps.refresh_detail("67890")

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.MULTI_MAP.code): {"op": "select", "id": "67890"}},
    )


async def test_set_current_map_uses_apply_for_listed_string_id(q10_api: Q10PropertiesApi) -> None:
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}, {"id": "67890"}],
                "op": "list",
                "result": 1,
            }
        }
    )

    with patch.object(q10_api.command, "send") as send:
        await q10_api.maps.set_current_map("67890")

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.MULTI_MAP.code): {"op": "apply", "id": "67890"}},
    )
    assert q10_api.maps.current_map_id == "12345"


@pytest.mark.parametrize("map_id", ["999", 12345])
async def test_set_current_map_rejects_unknown_or_non_string_id(
    q10_api: Q10PropertiesApi,
    map_id: object,
) -> None:
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
        with pytest.raises(RoborockException, match="Unknown Q10 saved-map ID"):
            await q10_api.maps.set_current_map(map_id)  # type: ignore[arg-type]

    send.assert_not_awaited()


async def test_saved_map_detail_refresh_rejects_unknown_or_parallel_request(
    q10_api: Q10PropertiesApi,
) -> None:
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    with pytest.raises(RoborockException, match="Unknown Q10 saved-map ID"):
        await q10_api.maps.refresh_detail("67890")

    await q10_api.maps.refresh_detail("12345")
    with pytest.raises(RoborockException, match="already pending"):
        await q10_api.maps.refresh_detail("12345")


async def test_saved_map_detail_correlates_pending_map_id(q10_api: Q10PropertiesApi) -> None:
    requested_id = str(parse_map_packet(FIXTURE.read_bytes()).map_id)
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": requested_id}, {"id": "999"}],
                "op": "list",
                "result": 1,
            }
        }
    )

    await q10_api.maps.refresh_detail("999")
    packet = parse_map_packet(b"\x04\x01" + FIXTURE.read_bytes()[2:])
    q10_api.maps.update_from_map_packet(packet)
    assert q10_api.maps.detail_packet is None

    matching = MapsTrait(q10_api.command)
    matching.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": requested_id}],
                "op": "list",
                "result": 1,
            }
        }
    )
    await matching.refresh_detail(requested_id)
    matching.update_from_map_packet(packet)
    assert matching.detail_packet is packet
    assert matching.detail_map_id == requested_id


async def test_saved_map_detail_refresh_requires_stored_map_id(q10_api: Q10PropertiesApi) -> None:
    """Detail cannot be requested until the saved-map list supplies an ID."""
    with pytest.raises(RoborockException, match="map list is available"):
        await q10_api.maps.refresh_detail()


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


def test_map_content_exposes_restrictions_in_common_coordinates() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)

    map_dps.update_from_dps(
        {
            B01_Q10_DP.RESTRICTED_ZONE_UP: _zone_blob(),
            B01_Q10_DP.VIRTUAL_WALL_UP: "AQAAAAAACgAU",
        }
    )

    assert trait.restricted_zones == (
        Q10RestrictedZone(
            Q10RestrictionType.NO_GO,
            (
                Q10RoborockPoint(25500, 25500),
                Q10RoborockPoint(25700, 25500),
                Q10RoborockPoint(25700, 25700),
                Q10RoborockPoint(25500, 25700),
            ),
        ),
    )
    assert trait.virtual_walls == (
        Q10VirtualWall(
            start=Q10RoborockPoint(25500, 25500),
            end=Q10RoborockPoint(25550, 25600),
        ),
    )


def test_map_content_preserves_unknown_restriction_type() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    raw = bytearray(base64.b64decode(_zone_blob()))
    raw[2] = 42

    map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: base64.b64encode(raw).decode()})

    assert trait.restricted_zones[0].type == 42


async def test_set_restricted_zones_sends_atomic_common_write(q10_api: Q10PropertiesApi) -> None:
    q10_api._map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: "AQA="})
    zone = Q10RestrictedZone(
        Q10RestrictionType.NO_MOP,
        (
            Q10RoborockPoint(25500, 25500),
            Q10RoborockPoint(25550, 25500),
            Q10RoborockPoint(25550, 25550),
            Q10RoborockPoint(25500, 25550),
        ),
    )

    with patch.object(q10_api.command, "send") as send:
        await q10_api.map.set_restricted_zones([zone])

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.RESTRICTED_ZONE.code): "AQECBAAAAAAACgAAAAoACgAAAAoAAAAAAAAAAAAAAAAAAAAAAAAAAA=="},
    )
    assert q10_api.map.restricted_zones == ()


async def test_set_virtual_walls_sends_atomic_common_write(q10_api: Q10PropertiesApi) -> None:
    wall = Q10VirtualWall(
        start=Q10RoborockPoint(25450, 25500),
        end=Q10RoborockPoint(25550, 25600),
    )

    with patch.object(q10_api.command, "send") as send:
        await q10_api.map.set_virtual_walls((wall,))

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.VIRTUAL_WALL.code): "Af/2AAAACgAU"},
    )
    assert q10_api.map.virtual_walls == ()


async def test_invalid_map_control_does_not_publish(q10_api: Q10PropertiesApi) -> None:
    invalid = Q10VirtualWall(
        start=Q10RoborockPoint(25501, 25500),
        end=Q10RoborockPoint(25550, 25600),
    )

    with patch.object(q10_api.command, "send") as send:
        with pytest.raises(ValueError, match="5 mm grid"):
            await q10_api.map.set_virtual_walls([invalid])

    send.assert_not_awaited()


async def test_restriction_write_refuses_unrepresentable_device_polygon(q10_api: Q10PropertiesApi) -> None:
    vertices = ((0, 0), (10, 0), (15, 5), (10, 10), (0, 10))
    record = bytes((0, len(vertices))) + b"".join(
        value.to_bytes(2, "big", signed=True) for point in vertices for value in point
    )
    q10_api._map_dps.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: base64.b64encode(bytes((1, 1)) + record).decode()})

    with patch.object(q10_api.command, "send") as send:
        with pytest.raises(RoborockException, match="fully supported device snapshot"):
            await q10_api.map.set_restricted_zones([])

    send.assert_not_awaited()


async def test_restriction_write_requires_device_snapshot(q10_api: Q10PropertiesApi) -> None:
    with patch.object(q10_api.command, "send") as send:
        with pytest.raises(RoborockException, match="fully supported device snapshot"):
            await q10_api.map.set_restricted_zones([])

    send.assert_not_awaited()


async def test_set_room_name_sends_validated_common_write(q10_api: Q10PropertiesApi) -> None:
    q10_api.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    with patch.object(q10_api.command, "send") as send:
        await q10_api.map.set_room_name(2, "Study")

    send.assert_awaited_once_with(
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.RESET_ROOM_NAME.code): "AQIABVN0dWR5AAAAAAAAAAAAAAAAAAA="},
    )
    assert q10_api.map.rooms[0].raw_name == "rr_living_room"


async def test_set_room_name_rejects_unknown_room_before_publish(q10_api: Q10PropertiesApi) -> None:
    q10_api.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    with patch.object(q10_api.command, "send") as send:
        with pytest.raises(RoborockException, match="Unknown Q10 room ID"):
            await q10_api.map.set_room_name(99, "Study")

    send.assert_not_awaited()


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


def test_docked_state_clears_stale_live_trace(render_map: Mock) -> None:
    """A docked update removes a completed path from public live state."""
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = Q10TracePacket(points=[Q10Point(1, 2), Q10Point(3, 4)])
    render_map.return_value = b"map"

    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)
    assert render_map.call_args.args[1] is trace

    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})

    assert trait.path == []
    assert render_map.call_args.args[1] is None
    assert render_map.call_args.kwargs["robot_at_dock"] is True


def test_docked_state_clears_current_room_and_ignores_late_trace() -> None:
    map_dps = MapDpsTrait()
    trait = _map_trait(map_dps)
    packet = parse_map_packet(FIXTURE.read_bytes())
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CLEANING.code})
    trait.update_from_map_packet(packet)
    trait.update_from_trace_packet(trace)

    with patch(
        "roborock.devices.traits.b01.q10.map.resolve_q10_current_room",
        return_value=packet.rooms[0],
    ) as resolve:
        assert trait.current_room == packet.rooms[0]
        map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})
        assert trait.current_room is None
        trait.update_from_trace_packet(trace)
        assert trait.current_room is None
        assert trait.path == []
        assert resolve.call_count == 1


def test_late_trace_is_ignored_while_docked(render_map: Mock) -> None:
    """A delayed trace cannot repopulate public state while docked."""
    map_dps = MapDpsTrait()
    map_dps.update_from_dps({B01_Q10_DP.STATUS: YXDeviceState.CHARGING.code})
    trait = _map_trait(map_dps)
    trace = Q10TracePacket(points=[Q10Point(1, 2)])
    render_map.return_value = b"map"

    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    trait.update_from_trace_packet(trace)

    assert trait.path == []
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

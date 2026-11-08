"""Tests for the Q10 B01 map content trait.

Map list data and current map content have independent refresh schedules.
Saved-map previews use a stored map ID, while current content uses a read-only
status request. The device sends data later in a ``MAP_RESPONSE`` packet.
These tests cover state management. The render details are tested in ``tests/map/test_b01_q10_render.py``.
"""

import asyncio
import base64
import io
import json
from collections.abc import AsyncGenerator, Generator
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from vacuum_map_parser_base.config.drawable import Drawable

from roborock.cli import _await_q10_map_push, cli
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, Q10RestrictionType, YXDeviceState
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.command import CommandTrait
from roborock.devices.traits.b01.q10.map import MapContentTrait, MapDpsTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import (
    B01Q10MapParserConfig,
    Q10CleanRecordDetail,
    Q10HeaderCalibration,
    Q10MapPacketKind,
    Q10Obstacle,
    Q10Point,
    Q10TracePacket,
    parse_clean_record_detail,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.map.b01_q10_overlays import Q10RestrictedZone, Q10VirtualWall
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
    assert (trait.robot_position.x, trait.robot_position.y) == (26190, 25498)
    assert trait.trace_sequence == trace.sequence
    assert trait.robot_heading == -34
    assert len(updates) == 1


def test_q10_position_is_available_as_top_level_cli_command() -> None:
    assert "q10-position" in cli.commands


# --- CLI push waiting --------------------------------------------------------


class _FakeQ10Properties:
    def __init__(self) -> None:
        command = cast(CommandTrait, Mock(spec=CommandTrait))
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


async def test_map_content_refresh_requests_are_not_rate_limited(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    """The caller controls content cadence; each refresh sends a read-only request."""
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    await q10_api.map.refresh()
    await q10_api.map.refresh()

    assert mock_channel.published_commands == [(B01_Q10_DP.REQUEST_DPS, {}), (B01_Q10_DP.REQUEST_DPS, {})]


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
    assert data["robotPosition"] == {"x": 25875, "y": 26125}


async def test_create_forwards_obstacle_drawables_to_rendering(fake_channel: FakeB01Q10Channel) -> None:
    """The public Q10 factory config changes the rendered image."""
    enabled = create(fake_channel, map_parser_config=B01Q10MapParserConfig(drawables=[Drawable.OBSTACLES]))
    disabled = create(fake_channel, map_parser_config=B01Q10MapParserConfig(drawables=[]))
    packet = replace(
        parse_map_packet(FIXTURE.read_bytes()),
        header_calibration=Q10HeaderCalibration(0, 50, 5, -1, -1, 0),
        obstacles=[Q10Obstacle(150, 100)],
    )
    enabled.map.update_from_map_packet(packet)
    disabled.map.update_from_map_packet(packet)
    assert enabled.map.image_content != disabled.map.image_content


async def test_set_current_map_uses_apply_for_listed_string_id(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}, {"id": "67890"}],
                "op": "list",
                "result": 1,
            }
        }
    )

    await q10_api.maps.set_current_map("67890")

    assert mock_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "apply", "id": "67890"}},
        )
    ]
    assert q10_api.maps.current_map_id == "12345"


@pytest.mark.parametrize("map_id", ["999"])
async def test_set_current_map_rejects_unknown_or_non_string_id(
    q10_api: Q10PropertiesApi,
    map_id: str,
    mock_channel: FakeB01Q10Channel,
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
        await q10_api.maps.set_current_map(map_id)

    assert mock_channel.published_commands == []


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

    assert trait.restricted_zones[0].type is Q10RestrictionType.unknown


async def test_set_restricted_zones_sends_atomic_common_write(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    zone = Q10RestrictedZone(
        Q10RestrictionType.NO_MOP,
        (
            Q10RoborockPoint(25500, 25500),
            Q10RoborockPoint(25550, 25500),
            Q10RoborockPoint(25550, 25550),
            Q10RoborockPoint(25500, 25550),
        ),
    )

    await q10_api.map.set_restricted_zones([zone])

    assert mock_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.RESTRICTED_ZONE.code): "AQECBAAAAAAACgAAAAoACgAAAAoAAAAAAAAAAAAAAAAAAAAAAAAAAA=="},
        )
    ]
    assert q10_api.map.restricted_zones == ()


async def test_set_virtual_walls_sends_atomic_common_write(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    wall = Q10VirtualWall(
        start=Q10RoborockPoint(25450, 25500),
        end=Q10RoborockPoint(25550, 25600),
    )

    await q10_api.map.set_virtual_walls((wall,))

    assert mock_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.VIRTUAL_WALL.code): "Af/2AAAACgAU"},
        )
    ]
    assert q10_api.map.virtual_walls == ()


async def test_invalid_map_control_does_not_publish(q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel) -> None:
    invalid = Q10VirtualWall(
        start=Q10RoborockPoint(25501, 25500),
        end=Q10RoborockPoint(25550, 25600),
    )

    with pytest.raises(ValueError, match="5 mm grid"):
        await q10_api.map.set_virtual_walls([invalid])

    assert mock_channel.published_commands == []


async def test_set_room_name_sends_validated_common_write(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    q10_api.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    await q10_api.map.set_room_name(2, "Study")

    assert mock_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.RESET_ROOM_NAME.code): "AQIABVN0dWR5AAAAAAAAAAAAAAAAAAA="},
        )
    ]
    assert q10_api.map.rooms[0].raw_name == "rr_living_room"


async def test_set_room_name_rejects_unknown_room_before_publish(
    q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel
) -> None:
    q10_api.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))

    with pytest.raises(RoborockException, match="Unknown Q10 room ID"):
        await q10_api.map.set_room_name(99, "Study")

    assert mock_channel.published_commands == []


async def test_clear_restrictions_without_snapshot(q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel) -> None:
    await q10_api.map.set_restricted_zones([])
    assert mock_channel.published_commands == [(B01_Q10_DP.COMMON, {"54": "AQA="})]


async def test_archived_map_pushes_cannot_overwrite_live_map(
    q10_api: Q10PropertiesApi,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    """03/04 detail packets are isolated from the current live-map trait."""
    current_bytes = FIXTURE.read_bytes()
    current = parse_map_packet(current_bytes)
    trace = parse_trace_packet(TRACE_SESSION_FIXTURE.read_bytes())
    clean_record = parse_clean_record_detail(b"\x03\x01" + current_bytes[2:])
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
    assert q10_api.clean_history.detail is clean_record
    assert q10_api.clean_history.detail_packet is clean_record.map
    assert q10_api.clean_history.detail_packet.kind is Q10MapPacketKind.CLEAN_RECORD_DETAIL
    assert q10_api.maps.detail_packet is saved_map
    assert q10_api.maps.detail_packet.kind is Q10MapPacketKind.SAVED_MAP_DETAIL
    assert clean_record_updates == [None]
    assert saved_map_updates == [None]


def test_archive_owners_reject_wrong_packet_kinds(q10_api: Q10PropertiesApi) -> None:
    """Semantic archive traits reject packets owned by another map stream."""
    current = parse_map_packet(FIXTURE.read_bytes())

    with pytest.raises(ValueError, match="clean-record detail"):
        q10_api.clean_history.update_from_detail(Q10CleanRecordDetail(map=current))
    with pytest.raises(ValueError, match="saved-map detail"):
        q10_api.maps.update_from_map_packet(current)


@pytest.mark.parametrize("scale", [1, 2, 4])
async def test_live_q10_map_renders_at_requested_scale(scale: int, fake_channel: FakeB01Q10Channel) -> None:
    api = create(fake_channel, map_parser_config=B01Q10MapParserConfig(map_scale=scale))
    payload = FIXTURE.read_bytes()
    fake_channel.messages_to_stream = [
        parse_map_packet(payload),
    ]
    await api.start()
    try:
        await _wait_for(lambda: api.map.image_content is not None)
        assert api.map.image_content is not None
        with Image.open(io.BytesIO(api.map.image_content)) as image:
            assert image.size == (8 * scale, 6 * scale)
    finally:
        await api.close()


def test_q10_properties_constructor_uses_default_live_map_config(fake_channel: FakeB01Q10Channel) -> None:
    api = Q10PropertiesApi(fake_channel)
    api.map.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
    assert api.map.image_content is not None
    with Image.open(io.BytesIO(api.map.image_content)) as image:
        assert image.size == (32, 24)


@pytest.mark.parametrize("selected,expected", [(None, "12345"), ("67890", "67890")])
async def test_saved_map_detail_refresh_publishes_selection(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
    selected: str | None,
    expected: str,
) -> None:
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345"}, {"id": "67890"}],
                "op": "list",
                "result": 1,
            }
        }
    )
    await q10_api.maps.refresh_detail(selected)
    assert mock_channel.published_commands == [(B01_Q10_DP.COMMON, {"61": {"op": "select", "id": expected}})]
    assert q10_api.maps.detail_packet is None


async def test_saved_map_detail_rejects_unknown_id(q10_api: Q10PropertiesApi, mock_channel: FakeB01Q10Channel) -> None:
    q10_api.maps.update_from_dps({B01_Q10_DP.MULTI_MAP: {"data": [{"id": "12345"}], "op": "list", "result": 1}})
    with pytest.raises(RoborockException, match="Unknown Q10 saved-map ID"):
        await q10_api.maps.refresh_detail("67890")
    assert mock_channel.published_commands == []


async def test_saved_map_details_publish_packet_map_id_and_notify(
    q10_api: Q10PropertiesApi,
    mock_channel: FakeB01Q10Channel,
    message_queue: asyncio.Queue[Q10Message],
) -> None:
    updates = []
    q10_api.maps.add_update_listener(lambda: updates.append(q10_api.maps.detail_map_id))
    packet = parse_map_packet(b"\x04\x01" + FIXTURE.read_bytes()[2:])
    message_queue.put_nowait(packet)
    await _wait_for(lambda: bool(updates))
    assert updates == [str(packet.map_id)]
    assert q10_api.maps.detail_packet is packet
    message_queue.put_nowait(replace(packet, map_id=999))
    await _wait_for(lambda: len(updates) == 2)
    assert updates == [str(packet.map_id), "999"]
    assert q10_api.map.image_content is None


async def test_saved_map_detail_refresh_requires_stored_map_id(q10_api: Q10PropertiesApi) -> None:
    """Detail cannot be requested until the saved-map list supplies an ID."""
    with pytest.raises(RoborockException, match="map list is available"):
        await q10_api.maps.refresh_detail()


def test_saved_map_diagnostics_exclude_binary_content(q10_api: Q10PropertiesApi) -> None:
    packet = parse_map_packet(b"\x04\x01" + FIXTURE.read_bytes()[2:])
    q10_api.maps.update_from_map_packet(packet)
    data = q10_api.as_dict()["maps"]
    assert data == {"detailMapId": str(packet.map_id)}
    assert q10_api.maps.detail_packet is packet
    assert q10_api.maps.as_dict(exclude={"detail_map_id"}) == {}
    json.dumps(data)


async def test_cli_listener_is_removed_after_timeout(q10_api: Q10PropertiesApi) -> None:
    calls = []

    def predicate() -> bool:
        calls.append(True)
        return False

    assert not await _await_q10_map_push(q10_api, predicate, timeout=0.01)
    calls.clear()
    q10_api.map.update_from_trace_packet(Q10TracePacket())
    assert calls == []


def test_live_map_trait_rejects_archived_packet() -> None:
    trait = _map_trait()
    packet = parse_map_packet(b"\x04\x01" + FIXTURE.read_bytes()[2:])
    with pytest.raises(ValueError, match="current Q10 map packet"):
        trait.update_from_map_packet(packet)
    assert trait.image_content is None


async def test_cli_listener_is_removed_after_cancellation(q10_api: Q10PropertiesApi) -> None:
    calls = []

    def predicate() -> bool:
        calls.append(True)
        return False

    request = asyncio.create_task(_await_q10_map_push(q10_api, predicate, timeout=1))
    await asyncio.sleep(0)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    q10_api.map.update_from_trace_packet(Q10TracePacket())
    assert calls == []


@pytest.mark.parametrize("drawables,expected_base", [([], True), ([Drawable.CHARGER], False)])
async def test_live_q10_map_honors_drawable_selection(
    drawables: list[Drawable], expected_base: bool, fake_channel: FakeB01Q10Channel
) -> None:
    api = create(fake_channel, map_parser_config=B01Q10MapParserConfig(drawables=drawables))
    base_packet = parse_map_packet(FIXTURE.read_bytes())
    base = create(FakeB01Q10Channel())
    base.map.update_from_map_packet(base_packet)
    assert base.map.image_content is not None
    with Image.open(io.BytesIO(base.map.image_content)) as image:
        base_pixels = image.tobytes()
    packet = replace(
        base_packet,
        header_calibration=Q10HeaderCalibration(
            origin_x=0, origin_y=50, resolution=5, charger_x=30, charger_y=30, charger_phi=90
        ),
    )
    fake_channel.messages_to_stream = [
        packet,
    ]
    await api.start()
    try:
        await _wait_for(lambda: api.map.image_content is not None)
        assert api.map.image_content is not None
        with Image.open(io.BytesIO(api.map.image_content)) as image:
            assert (image.tobytes() == base_pixels) is expected_base
    finally:
        await api.close()

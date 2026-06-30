"""Tests for the Q10 B01 map content trait.

The Q10 map API is push-driven: the device publishes ``MAP_RESPONSE`` messages
which the protocol layer decodes into typed map/trace packets; the trait updates
its cached state from them via ``update_from_map_packet`` /
``update_from_trace_packet`` (there is no synchronous get-map request).
"""

import asyncio
import io
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from PIL import Image

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.map import _Q10_RESOLUTIONS, MapContentTrait
from roborock.exceptions import RoborockException
from roborock.map.b01_grid_layers import GridCalibration
from roborock.map.b01_q10_map_parser import (
    Q10EraseZone,
    Q10HeaderCalibration,
    Q10Point,
    parse_map_packet,
    parse_trace_packet,
)
from roborock.map.b01_q10_overlays import ZONE_TYPE_NO_GO, ZONE_TYPE_NO_MOP
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = Path("tests/map/testdata/b01_q10_trace.bin")
TRACE_SESSION_FIXTURE = Path("tests/map/testdata/b01_q10_trace_session.bin")


def _map_message(
    payload: bytes, protocol: RoborockMessageProtocol = RoborockMessageProtocol.MAP_RESPONSE
) -> RoborockMessage:
    return RoborockMessage(protocol=protocol, payload=payload, version=b"B01")


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
    assert trait.map_data is not None
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

    message_queue.put_nowait(_map_message(TRACE_SESSION_FIXTURE.read_bytes()))

    await _wait_for(lambda: bool(q10_api.map.path))
    assert q10_api.map.robot_position is not None


# --- Layers / calibration / rendering ----------------------------------------


def _trait_with_map() -> MapContentTrait:
    """A trait with a map already pushed into it."""
    trait = MapContentTrait()
    trait.update_from_map_packet(parse_map_packet(FIXTURE.read_bytes()))
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


def _floor_world_points(trait: MapContentTrait, cal: GridCalibration, count: int) -> list[Q10Point]:
    """``count`` world points lying on the map's floor under ``cal``."""
    assert trait.layers is not None
    layers = trait.layers
    floor = [
        (px, py)
        for py in range(layers.height)
        for px in range(layers.width)
        if layers.cell_class(layers.grid[py * layers.width + px]) == "floor"
    ]
    return [Q10Point(*(int(v) for v in cal.pixel_to_world(px, py))) for px, py in floor[:count]]


def test_solve_calibration_uses_header_origin_with_short_path() -> None:
    """A grid-frame header origin lets a short path calibrate (origin is exact)."""
    trait = _trait_with_map()
    # Header origin in 5 mm units -> pixel origin (0, 5); not a keepalive frame.
    trait.header_calibration = Q10HeaderCalibration(
        origin_x=0, origin_y=50, resolution=5, charger_x=0, charger_y=0, charger_phi=0
    )
    true = GridCalibration(resolution=20.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = _floor_world_points(trait, true, 6)
    assert len(trait.path) < 20  # far too short for the full origin+resolution fit
    cal = trait.solve_calibration()
    assert cal is not None
    # Origin comes straight from the header (exact); only the resolution is fit,
    # so it lands on one of the candidates (the exact pick is grid-quantized).
    assert (cal.origin_x, cal.origin_y) == (0.0, 5.0)
    assert cal.resolution in _Q10_RESOLUTIONS
    assert trait.calibration is cal


def test_solve_calibration_short_path_without_header_returns_none() -> None:
    """Without a header origin a short path is still too sparse for the full fit."""
    trait = _trait_with_map()  # the fixture header is a keepalive frame
    assert trait.header_calibration is not None and trait.header_calibration.is_keepalive
    true = GridCalibration(resolution=10.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = _floor_world_points(trait, true, 6)
    assert trait.solve_calibration() is None


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
    # world (3, 2) -> grid pixel (3, 3); the ss07 grid renders top-down (no flip),
    # so that maps straight to image (12, 12) at scale 4.
    trait.robot_position = Q10Point(3, 2)
    png = trait.render_path_on_map(position_color=(255, 211, 0, 255))
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    assert img.size == (8 * 4, 6 * 4)
    assert img.getpixel((12, 12)) == (255, 211, 0, 255)


def test_render_path_on_map_draws_heading_indicator() -> None:
    """A known heading draws a facing tick from the robot marker.

    With heading 0 (= +x world) and the identity-ish calibration, the tick
    extends to the right of the robot pixel; with the marker at image (12, 12)
    the tick covers pixels at x > 12 along y == 12.
    """
    trait = _trait_with_map()
    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = [Q10Point(1, 2), Q10Point(3, 2)]
    trait.robot_position = Q10Point(3, 2)
    trait.robot_heading = 0  # facing +x
    png = trait.render_path_on_map(position_color=(255, 211, 0, 255))
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    # tick runs +x from the marker (4 * radius = 16 px at scale 4)
    assert img.getpixel((20, 12)) == (255, 211, 0, 255)
    # ...and not behind it (the marker is a small disc; sample well to the left)
    assert img.getpixel((4, 12)) != (255, 211, 0, 255)


def test_parse_map_content_preserves_path_overlays_after_calibration() -> None:
    """Reparsing a calibrated map keeps path and vacuum position on MapData."""
    trait = _trait_with_map()
    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    trait.path = [Q10Point(1, 2), Q10Point(3, 2)]
    trait.robot_position = Q10Point(3, 2)

    trait.parse_map_content()

    assert trait.map_data is not None
    assert trait.map_data.path is not None
    assert trait.map_data.vacuum_position is not None
    assert (trait.map_data.vacuum_position.x, trait.map_data.vacuum_position.y) == (3.0, 3.0)


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

    blob = (
        bytes([1, 2])
        + rect(ZONE_TYPE_NO_GO, [(0, 0), (4, 0), (4, 4), (0, 4)])
        + rect(ZONE_TYPE_NO_MOP, [(1, 1), (2, 1), (2, 2), (1, 2)])
    )
    trait.load_overlays(restricted_zone_up=blob)

    assert len(trait.zones) == 2
    assert trait.map_data is not None
    assert len(trait.map_data.no_go_areas or []) == 1
    assert len(trait.map_data.no_mopping_areas or []) == 1
    # charger = path origin in pixels: (1, 5-1) = (1, 4)
    assert trait.map_data.charger is not None
    assert (trait.map_data.charger.x, trait.map_data.charger.y) == (1.0, 4.0)


def test_apply_erase_blanks_cells_with_calibration() -> None:
    """With a calibration, erase-zone cells are blanked from the layers + image."""
    trait = _trait_with_map()
    assert trait.layers is not None
    before_floor = trait.layers.class_counts.get("floor")
    before_image = trait.image_content
    assert before_floor and before_floor > 0

    # identity-ish calibration: world (x, y) -> pixel (x, 5 - y) over the 8x6 grid.
    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    # A rectangle covering the whole grid in world coords erases every cell.
    trait.erase_zones = [Q10EraseZone(vertices=[(0, 0), (7, 0), (7, 5), (0, 5)])]
    trait._apply_erase(trait.calibration)

    assert trait.layers.class_counts.get("floor", 0) == 0  # all floor erased
    assert trait.image_content != before_image  # re-rendered


def test_apply_erase_partial_rectangle() -> None:
    """An erase rectangle only blanks the cells it covers, leaving the rest."""
    trait = _trait_with_map()
    assert trait.layers is not None
    before_floor = trait.layers.class_counts.get("floor", 0)

    trait.calibration = GridCalibration(resolution=1.0, origin_x=0.0, origin_y=5.0, y_sign=1)
    # Cover only the top two grid rows (pixel y 0..1 -> world y 4..5).
    trait.erase_zones = [Q10EraseZone(vertices=[(0, 4), (7, 4), (7, 5), (0, 5)])]
    trait._apply_erase(trait.calibration)

    after_floor = trait.layers.class_counts.get("floor", 0)
    assert 0 < after_floor < before_floor  # some, not all, floor removed


def test_load_overlays_partial_update_keeps_existing_zones() -> None:
    """A status push without the zone DP (None) must not wipe loaded zones."""
    trait = MapContentTrait()
    blob = (
        bytes([1, 1])
        + bytes([0, 4])
        + b"".join(int.to_bytes(v & 0xFFFF, 2, "big") for xy in [(0, 0), (4, 0), (4, 4), (0, 4)] for v in xy)
    )
    trait.load_overlays(restricted_zone_up=blob)
    assert len(trait.zones) == 1
    # A later partial update carrying only the (empty) virtual-wall DP.
    trait.load_overlays(restricted_zone_up=None, virtual_wall_up=b"\x00")
    assert len(trait.zones) == 1  # zones preserved
    assert trait.virtual_walls == []


def test_update_from_dps_decodes_overlay_data_points() -> None:
    """The map trait picks the overlay DPs out of a DPS push and decodes them."""
    trait = MapContentTrait()
    blob = (
        bytes([1, 1])
        + bytes([0, 4])
        + b"".join(int.to_bytes(v & 0xFFFF, 2, "big") for xy in [(0, 0), (4, 0), (4, 4), (0, 4)] for v in xy)
    )
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    trait.update_from_dps({B01_Q10_DP.RESTRICTED_ZONE_UP: blob})

    assert len(trait.zones) == 1
    assert notified  # listeners learn the overlays changed


def test_update_from_dps_without_overlay_data_points_is_noop() -> None:
    """A DPS push carrying neither overlay DP leaves the trait untouched."""
    trait = MapContentTrait()
    notified = []
    trait.add_update_listener(lambda: notified.append(True))

    trait.update_from_dps({B01_Q10_DP.BATTERY: 50})

    assert trait.zones == []
    assert trait.virtual_walls == []
    assert not notified

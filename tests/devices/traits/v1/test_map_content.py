"""End-to-end tests for MapContentTrait backed by V1VacuumSimulator."""

from collections.abc import AsyncGenerator
from dataclasses import replace

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.rpc.v1_channel import V1Channel
from roborock.devices.traits.v1.map_content import MapContentTrait
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import V1RpcChannel
from roborock.testing import DEFAULT_STATUS, V1VacuumSimulator


@pytest.fixture(name="simulator")
def simulator_fixture(
    device_info: HomeDataDevice,
    products: list[HomeDataProduct],
    dock_type_code: RoborockDockTypeCode | None,
) -> V1VacuumSimulator:
    """Create a connected V1VacuumSimulator backing the device."""
    product = next(p for p in products if p.id == device_info.product_id)
    sim = V1VacuumSimulator(
        duid=device_info.duid,
        device_info=device_info,
        product=product,
        status=replace(DEFAULT_STATUS, dock_type=dock_type_code),
    )
    sim.connect()
    return sim


@pytest.fixture(name="channel")
def simulator_channel_fixture(simulator: V1VacuumSimulator) -> V1Channel:
    """Provide the simulator's real V1Channel."""
    return simulator.v1_channel


@pytest.fixture(name="mock_rpc_channel")
def simulator_rpc_channel_fixture(simulator: V1VacuumSimulator) -> V1RpcChannel:
    """Provide the simulator's real combined RPC channel."""
    return simulator.v1_channel.rpc_channel


@pytest.fixture(name="mock_mqtt_rpc_channel")
def simulator_mqtt_rpc_channel_fixture(simulator: V1VacuumSimulator) -> V1RpcChannel:
    """Provide the simulator's real MQTT RPC channel."""
    return simulator.v1_channel.mqtt_rpc_channel


@pytest.fixture(name="mock_map_rpc_channel")
def simulator_map_rpc_channel_fixture(simulator: V1VacuumSimulator) -> V1RpcChannel:
    """Provide the simulator's real map RPC channel."""
    return simulator.v1_channel.map_rpc_channel


@pytest.fixture(name="mock_blob_rpc_channel")
def simulator_blob_rpc_channel_fixture(simulator: V1VacuumSimulator) -> V1RpcChannel:
    """Provide the simulator's real blob RPC channel."""
    return simulator.v1_channel.blob_rpc_channel


@pytest.fixture(autouse=True)
async def discover_features_fixture(device: RoborockDevice) -> AsyncGenerator[None, None]:
    """Connect the device against the simulator and tear down cleanly."""
    await device.connect()
    try:
        yield
    finally:
        await device.close()


@pytest.fixture(name="map_content_trait")
def map_content_trait_fixture(device: RoborockDevice) -> MapContentTrait:
    """Return the device's MapContentTrait."""
    assert device.v1_properties
    return device.v1_properties.map_content


@pytest.mark.parametrize(
    ("map_parts", "map_part_order"),
    [
        (1, None),
        (2, [0, 1]),
        (2, [1, 0]),
        (3, [0, 1, 2]),
        (3, [2, 0, 1]),
        (4, [3, 1, 2, 0]),
    ],
    ids=[
        "single_part",
        "two_parts_in_order",
        "two_parts_out_of_order",
        "three_parts_in_order",
        "three_parts_out_of_order",
        "four_parts_permuted",
    ],
)
async def test_refresh_map_content_trait(
    simulator: V1VacuumSimulator,
    map_content_trait: MapContentTrait,
    map_parts: int,
    map_part_order: list[int] | None,
) -> None:
    """Test refreshing and parsing single-part and multi-part map responses end-to-end."""
    simulator.advance_path(80)
    simulator.robot_position = (31000, 32000, 180)
    simulator.map_parts = map_parts
    simulator.map_part_order = map_part_order

    await map_content_trait.refresh()

    assert map_content_trait.image_content is not None
    assert map_content_trait.image_content.startswith(b"\x89PNG")
    assert map_content_trait.raw_api_response == simulator.build_map_bytes()
    assert map_content_trait.map_data is not None
    assert map_content_trait.map_data.path is not None
    assert len(map_content_trait.map_data.path.path[0]) == 80
    assert map_content_trait.map_data.vacuum_position is not None
    assert (
        map_content_trait.map_data.vacuum_position.x,
        map_content_trait.map_data.vacuum_position.y,
    ) == (31000, 32000)


async def test_refresh_unchanged_content_skips_parsing(
    simulator: V1VacuumSimulator,
    map_content_trait: MapContentTrait,
) -> None:
    """Test that refresh avoids re-parsing unchanged maps and updates when map bytes change."""
    simulator.advance_path(40)
    simulator.robot_position = (28000, 29000, 90)
    simulator.map_parts = 3

    await map_content_trait.refresh()
    initial_image = map_content_trait.image_content
    initial_map_data = map_content_trait.map_data
    assert initial_image is not None
    assert initial_map_data is not None

    # Second refresh with identical multi-part map preserves the existing MapData instance
    await map_content_trait.refresh()
    assert map_content_trait.map_data is initial_map_data

    # Third refresh after robot movement re-parses and renders the updated map
    simulator.advance_path(40)
    simulator.robot_position = (33000, 34000, 270)
    simulator.map_part_order = [2, 0, 1]
    await map_content_trait.refresh()

    assert map_content_trait.map_data is not initial_map_data
    assert map_content_trait.image_content != initial_image
    assert map_content_trait.map_data is not None
    assert map_content_trait.map_data.path is not None
    assert len(map_content_trait.map_data.path.path[0]) == 80
    assert map_content_trait.map_data.vacuum_position is not None
    assert (
        map_content_trait.map_data.vacuum_position.x,
        map_content_trait.map_data.vacuum_position.y,
    ) == (33000, 34000)


async def test_refresh_invalid_map_raises_exception(
    simulator: V1VacuumSimulator,
    map_content_trait: MapContentTrait,
) -> None:
    """Test malformed map payload raises RoborockException after multi-part reassembly."""
    simulator.custom_handlers["get_map_v1"] = lambda _: b"corrupt_map_bytes"
    simulator.map_parts = 2

    with pytest.raises(RoborockException, match="Failed to parse map data"):
        await map_content_trait.refresh()


async def test_async_parse_map_content(
    simulator: V1VacuumSimulator,
    map_content_trait: MapContentTrait,
) -> None:
    """Test async_parse_map_content on MapContentConverter with real map bytes."""
    simulator.advance_path(25)
    map_bytes = simulator.build_map_bytes()

    result = await map_content_trait.converter.async_parse_map_content(map_bytes)

    assert result.image_content is not None
    assert result.image_content.startswith(b"\x89PNG")
    assert result.raw_api_response == map_bytes
    assert result.map_data is not None
    assert result.map_data.path is not None
    assert len(result.map_data.path.path[0]) == 25

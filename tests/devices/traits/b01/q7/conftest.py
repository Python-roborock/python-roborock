from typing import Any

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.devices.rpc.b01_q7_channel import Q7MapRpcChannel, Q7RpcChannel
from roborock.devices.traits.b01.q7 import Q7PropertiesApi, create


class FakeQ7Channel(Q7RpcChannel, Q7MapRpcChannel):
    """A plaintext mock for Q7 Rpc and Map Channel."""

    def __init__(self) -> None:
        self.published_commands: list[tuple[Any, Any]] = []
        self.response_queue: list[Any] = []
        self.side_effect: Exception | None = None

    async def send_command(self, command: Any, params: Any = None) -> Any:
        if self.side_effect:
            raise self.side_effect
        self.published_commands.append((command, params))
        if self.response_queue:
            return self.response_queue.pop(0)
        return {}

    async def send_map_command(self, command: Any, params: Any = None) -> bytes:
        self.published_commands.append((command, params))
        if self.response_queue:
            return self.response_queue.pop(0)
        return b""


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeQ7Channel:
    return FakeQ7Channel()


@pytest.fixture(name="product")
def product_fixture() -> HomeDataProduct:
    return HomeDataProduct(
        id="product-id-q7",
        name="Roborock Q7",
        model="roborock.vacuum.sc05",
        category=RoborockCategory.VACUUM,
    )


@pytest.fixture(name="device")
def device_fixture() -> HomeDataDevice:
    return HomeDataDevice(
        duid="abc123",
        name="Q7",
        local_key="key123key123key1",
        product_id="product-id-q7",
        sn="testsn012345",
    )


@pytest.fixture(name="q7_api")
def q7_api_fixture(
    fake_channel: FakeQ7Channel,
    device: HomeDataDevice,
    product: HomeDataProduct,
) -> Q7PropertiesApi:
    return create(product, device, fake_channel, fake_channel)

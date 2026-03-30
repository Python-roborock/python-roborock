import math
import time
from collections.abc import Generator
from unittest.mock import patch

import pytest

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


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
def q7_api_fixture(fake_channel: FakeChannel, device: HomeDataDevice, product: HomeDataProduct) -> Q7PropertiesApi:
    return Q7PropertiesApi(fake_channel, device=device, product=product)  # type: ignore[arg-type]


@pytest.fixture(name="expected_msg_id", autouse=True)
def next_message_id_fixture() -> Generator[int, None, None]:
    """Fixture to patch get_next_int to return the expected message ID.

    We pick an arbitrary number, but just need it to ensure we can craft a fake
    response with the message id matched to the outgoing RPC.
    """

    expected_msg_id = math.floor(time.time())

    # Patch get_next_int to return our expected msg_id so the channel waits for it
    with patch("roborock.protocols.b01_q7_protocol.get_next_int", return_value=expected_msg_id):
        yield expected_msg_id


@pytest.fixture(name="message_builder")
def message_builder_fixture(expected_msg_id: int) -> B01MessageBuilder:
    builder = B01MessageBuilder()
    builder.msg_id = expected_msg_id
    return builder

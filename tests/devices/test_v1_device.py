"""Tests for the Device class."""

import pathlib
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from syrupy import SnapshotAssertion

from roborock.data import HomeData, NetworkInfo, StatusV2, UserData
from roborock.devices.cache import DeviceCache, DeviceCacheData, InMemoryCache, NoCache
from roborock.devices.device import RoborockDevice
from roborock.devices.rpc.v1_channel import V1Channel
from roborock.devices.traits import v1
from roborock.devices.traits.v1.common import V1TraitMixin
from roborock.devices.transport.local_channel import LocalSession
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import SecurityData, decode_rpc_response
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests import mock_data
from tests.fixtures.channel_fixtures import FakeChannel

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
STATUS = StatusV2.from_dict(mock_data.STATUS)

TESTDATA = pathlib.Path("tests/protocols/testdata/v1_protocol/")


@pytest.fixture(autouse=True, name="channel")
def device_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="mqtt_rpc_channel")
def mqtt_rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="map_rpc_channel")
def map_rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="device")
def device_fixture(channel: AsyncMock, rpc_channel: AsyncMock, mqtt_rpc_channel: AsyncMock) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    return RoborockDevice(
        device_info=HOME_DATA.devices[0],
        product=HOME_DATA.products[0],
        channel=channel,
        trait=v1.create(
            HOME_DATA.devices[0].duid,
            HOME_DATA.products[0],
            HOME_DATA,
            rpc_channel,
            mqtt_rpc_channel,
            AsyncMock(),
            Mock(),
            AsyncMock(),
            device_cache=DeviceCache(HOME_DATA.devices[0].duid, NoCache()),
            region=USER_DATA.region,
        ),
    )


async def test_device_connection(device: RoborockDevice, channel: AsyncMock, setup_rpc_channel: AsyncMock) -> None:
    """Test the Device connection setup."""

    unsub = Mock()
    subscribe = AsyncMock()
    subscribe.return_value = unsub
    channel.subscribe = subscribe

    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"

    assert not subscribe.called

    await device.connect()
    assert subscribe.called
    assert not unsub.called

    await device.close()
    assert unsub.called


@pytest.mark.parametrize(
    ("connected", "local_connected"),
    [
        (True, False),
        (False, False),
        (True, True),
        (False, True),
    ],
)
async def test_connection_status(
    device: RoborockDevice,
    channel: AsyncMock,
    connected: bool,
    local_connected: bool,
) -> None:
    """Test successful RPC command sending and response handling."""
    channel.is_connected = connected
    channel.is_local_connected = local_connected
    assert device.is_connected is connected
    assert device.is_local_connected is local_connected


@pytest.fixture(name="payloads")
def payloads_fixture() -> list[pathlib.Path]:
    """Fixture to provide the payload for the tests."""
    return []


@pytest.fixture(name="setup_rpc_channel")
def setup_rpc_channel_fixture(rpc_channel: AsyncMock, payloads: list[pathlib.Path]) -> AsyncMock:
    """Fixture to set up the RPC channel for the tests."""
    # Device discovery calls
    side_effects: list[dict[str, Any] | list[Any] | int] = [
        [mock_data.APP_GET_INIT_STATUS],
        mock_data.STATUS,
    ]

    # Subsequent calls return the data payloads setup by the test.
    for payload in payloads:
        # The values other than the payload are arbitrary
        message = RoborockMessage(
            protocol=RoborockMessageProtocol.GENERAL_RESPONSE,
            payload=payload.read_bytes(),
            seq=12750,
            version=b"1.0",
            random=97431,
            timestamp=1652547161,
        )
        response_message = decode_rpc_response(message)
        side_effects.append(response_message.data)

    rpc_channel.send_command.side_effect = side_effects
    return rpc_channel


@pytest.mark.parametrize(
    ("payloads", "property_method"),
    [
        ([TESTDATA / "get_status.json"], lambda x: x.status),
        ([TESTDATA / "get_dnd.json"], lambda x: x.dnd),
        ([TESTDATA / "get_clean_summary.json", TESTDATA / "get_last_clean_record.json"], lambda x: x.clean_summary),
        ([TESTDATA / "get_volume.json"], lambda x: x.sound_volume),
    ],
    ids=[
        "status",
        "dnd",
        "clean_summary",
        "volume",
    ],
)
async def test_device_trait_command_parsing(
    device: RoborockDevice,
    setup_rpc_channel: AsyncMock,
    snapshot: SnapshotAssertion,
    property_method: Callable[..., V1TraitMixin],
) -> None:
    """Test the device trait command."""
    await device.connect()

    trait = property_method(device.v1_properties)
    assert trait
    assert isinstance(trait, V1TraitMixin)
    await trait.refresh()
    assert setup_rpc_channel.send_command.called

    assert trait == snapshot

    assert device.v1_properties
    device_dict = device.diagnostic_data()
    assert device_dict == snapshot


@pytest.mark.parametrize(
    "start_error",
    [RoborockException("transient status fetch failed"), ValueError("unexpected")],
    ids=["roborock-exception", "non-roborock-exception"],
)
async def test_connect_unsubscribes_when_start_fails(
    device: RoborockDevice,
    channel: AsyncMock,
    start_error: Exception,
) -> None:
    """connect() must release the channel when start() fails, for any exception.

    Regression: the cleanup was scoped to ``except RoborockException``, so a
    non-Roborock failure in start() propagated without unsubscribing, leaving the
    channel subscribed and the next attempt unable to re-subscribe.
    """
    unsub = Mock()
    channel.subscribe = AsyncMock(return_value=unsub)
    device.v1_properties.start = AsyncMock(side_effect=start_error)  # type: ignore[method-assign, union-attr]

    with pytest.raises(type(start_error)):
        await device.connect()

    # The channel was released before the error propagated.
    channel.subscribe.assert_awaited_once()
    unsub.assert_called_once()

    # The device is left re-connectable: once start() recovers, connect()
    # succeeds instead of raising "Already connected to the device".
    device.v1_properties.start = AsyncMock(return_value=None)  # type: ignore[method-assign, union-attr]
    await device.connect()
    assert channel.subscribe.await_count == 2


async def test_connect_retries_after_transient_start_failure() -> None:
    """End-to-end regression for the Q5 multi-vacuum bug.

    A device backed by a real V1Channel: the first connect() subscribes, then
    start() fails transiently. The retry must re-subscribe cleanly rather than
    raising "Only one subscription allowed at a time", and the device must end
    up connected.
    """
    duid = HOME_DATA.devices[0].duid

    mqtt_channel = FakeChannel()
    await mqtt_channel.connect()
    local_channel = FakeChannel()
    local_session = Mock(spec=LocalSession, return_value=local_channel)

    # Cache the network info so local connect doesn't need an MQTT round-trip.
    cache = InMemoryCache()
    device_cache = DeviceCache(duid, cache)
    await device_cache.set(DeviceCacheData(network_info=NetworkInfo.from_dict(mock_data.NETWORK_INFO)))

    v1_channel = V1Channel(
        device_uid=duid,
        security_data=SecurityData(endpoint="test_endpoint", nonce=b"test_nonce_16byt"),
        mqtt_channel=mqtt_channel,  # type: ignore[arg-type]
        local_session=local_session,
        device_cache=device_cache,
    )
    device = RoborockDevice(
        device_info=HOME_DATA.devices[0],
        product=HOME_DATA.products[0],
        channel=v1_channel,
        trait=v1.create(
            duid,
            HOME_DATA.products[0],
            HOME_DATA,
            AsyncMock(),
            AsyncMock(),
            AsyncMock(),
            Mock(),
            AsyncMock(),
            device_cache=device_cache,
            region=USER_DATA.region,
        ),
    )

    # First connect() subscribes successfully, then start() fails transiently;
    # the second succeeds.
    device.v1_properties.start = AsyncMock(side_effect=[RoborockException("transient"), None])  # type: ignore[method-assign, union-attr]

    with pytest.raises(RoborockException):
        await device.connect()

    # The retry must NOT raise "Only one subscription allowed at a time"; the
    # clean release after the transient failure lets connect() re-subscribe and
    # the device ends up connected.
    await device.connect()
    assert device.is_connected

    await device.close()

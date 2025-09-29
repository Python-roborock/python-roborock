"""Tests for the Device class."""

import pathlib
from collections.abc import Callable
from unittest.mock import AsyncMock, Mock

import pytest
from syrupy import SnapshotAssertion

from roborock.containers import HomeData, S7MaxVStatus, UserData
from roborock.devices.device import RoborockDevice
from roborock.devices.traits import v1
from roborock.devices.traits.v1.common import V1TraitMixin
from roborock.devices.v1_rpc_channel import decode_rpc_response
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)
STATUS = S7MaxVStatus.from_dict(mock_data.STATUS)

TESTDATA = pathlib.Path("tests/protocols/testdata/v1_protocol/")


@pytest.fixture(autouse=True, name="channel")
def device_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="rpc_channel")
def rpc_channel_fixture() -> AsyncMock:
    """Fixture to set up the channel for tests."""
    return AsyncMock()


@pytest.fixture(autouse=True, name="device")
def device_fixture(channel: AsyncMock, rpc_channel: AsyncMock) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    return RoborockDevice(
        device_info=HOME_DATA.devices[0],
        channel=channel,
        trait=v1.create(HOME_DATA.products[0], rpc_channel),
    )


async def test_device_connection(device: RoborockDevice, channel: AsyncMock) -> None:
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


@pytest.fixture(name="setup_rpc_channel")
def setup_rpc_channel_fixture(rpc_channel: AsyncMock, payload: pathlib.Path) -> AsyncMock:
    """Fixture to set up the RPC channel for the tests."""
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
    rpc_channel.send_command.return_value = response_message.data
    return rpc_channel


@pytest.mark.parametrize(
    ("payload", "property_method"),
    [
        (TESTDATA / "get_status.json", lambda x: x.status),
        (TESTDATA / "get_dnd.json", lambda x: x.dnd),
        (TESTDATA / "get_clean_summary.json", lambda x: x.clean_summary),
        (TESTDATA / "get_volume.json", lambda x: x.sound_volume),
    ],
)
async def test_device_trait_command_parsing(
    device: RoborockDevice,
    setup_rpc_channel: AsyncMock,
    snapshot: SnapshotAssertion,
    property_method: Callable[..., V1TraitMixin],
    payload: str,
) -> None:
    """Test the device trait command."""
    trait = property_method(device.v1_properties)
    assert trait
    assert isinstance(trait, V1TraitMixin)
    await trait.refresh()
    assert setup_rpc_channel.send_command.called

    assert trait == snapshot

"""Tests for the Device class."""

import pathlib
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, Mock

import pytest
from syrupy import SnapshotAssertion

from roborock.containers import HomeData, S7MaxVStatus, UserData
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.clean_summary import CleanSummaryTrait
from roborock.devices.traits.dnd import DoNotDisturbTrait
from roborock.devices.traits.sound_volume import SoundVolumeTrait
from roborock.devices.traits.status import StatusTrait
from roborock.devices.traits.trait import Trait
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
def device_fixture(channel: AsyncMock, traits: list[Trait]) -> RoborockDevice:
    """Fixture to set up the device for tests."""
    return RoborockDevice(
        device_info=HOME_DATA.devices[0],
        channel=channel,
        traits=traits,
    )


@pytest.fixture(autouse=True, name="traits")
def traits_fixture(rpc_channel: AsyncMock) -> list[Trait]:
    """Fixture to set up the V1 API for tests."""
    return [
        StatusTrait(
            product_info=HOME_DATA.products[0],
            rpc_channel=rpc_channel,
        ),
        CleanSummaryTrait(rpc_channel=rpc_channel),
        DoNotDisturbTrait(rpc_channel=rpc_channel),
        SoundVolumeTrait(rpc_channel=rpc_channel),
    ]


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
    ("payload", "trait_name", "trait_type", "trait_method"),
    [
        (TESTDATA / "get_status.json", "status", StatusTrait, StatusTrait.get_status),
        (TESTDATA / "get_dnd.json", "do_not_disturb", DoNotDisturbTrait, DoNotDisturbTrait.get_dnd_timer),
        (TESTDATA / "get_clean_summary.json", "clean_summary", CleanSummaryTrait, CleanSummaryTrait.get_clean_summary),
        (TESTDATA / "get_volume.json", "sound_volume", SoundVolumeTrait, SoundVolumeTrait.get_volume),
    ],
)
async def test_device_trait_command_parsing(
    device: RoborockDevice,
    setup_rpc_channel: AsyncMock,
    snapshot: SnapshotAssertion,
    trait_name: str,
    trait_type: type[Trait],
    trait_method: Callable[..., Awaitable[object]],
) -> None:
    """Test the device trait command."""
    trait = device.traits[trait_name]
    assert trait
    assert isinstance(trait, trait_type)
    result = await trait_method(trait)
    assert setup_rpc_channel.send_command.called

    assert result == snapshot

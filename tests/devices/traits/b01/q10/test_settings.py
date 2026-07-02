"""Tests for the Q10 B01 setting writer traits."""

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceDustCollectionFrequency
from roborock.devices.traits.b01.q10.button_light import ButtonLightTrait
from roborock.devices.traits.b01.q10.child_lock import ChildLockTrait
from roborock.devices.traits.b01.q10.command import CommandTrait
from roborock.devices.traits.b01.q10.do_not_disturb import DoNotDisturbTrait
from roborock.devices.traits.b01.q10.dust_collection import DustCollectionTrait
from roborock.devices.traits.b01.q10.volume import SoundVolumeTrait

from .conftest import FakeQ10RpcChannel


@pytest.fixture(name="fake_rpc_channel")
def fake_rpc_channel_fixture() -> FakeQ10RpcChannel:
    return FakeQ10RpcChannel()


@pytest.fixture(name="command")
def command_fixture(fake_rpc_channel: FakeQ10RpcChannel) -> CommandTrait:
    return CommandTrait(fake_rpc_channel)


def _sent_dps(fake_rpc_channel: FakeQ10RpcChannel) -> dict:
    assert len(fake_rpc_channel.published_commands) == 1
    command, params = fake_rpc_channel.published_commands[0]
    return {str(command.code): params}


async def test_set_volume_uses_common_wrapper(fake_rpc_channel: FakeQ10RpcChannel, command: CommandTrait) -> None:
    """Volume writes are wrapped in dpCommon (101) -> {"26": value}."""
    await SoundVolumeTrait(command).set_volume(55)
    assert _sent_dps(fake_rpc_channel) == {"101": {"26": 55}}


@pytest.mark.parametrize("volume", [-1, 101, 1000])
async def test_set_volume_rejects_out_of_range(command: CommandTrait, volume: int) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        await SoundVolumeTrait(command).set_volume(volume)


@pytest.mark.parametrize(
    ("trait_cls", "method", "code"),
    [
        (ChildLockTrait, "enable", "47"),
        (DoNotDisturbTrait, "enable", "25"),
        (ButtonLightTrait, "enable", "77"),
        (DustCollectionTrait, "enable", "37"),
    ],
)
async def test_switch_enable_writes_common_wrapped_dp(
    fake_rpc_channel: FakeQ10RpcChannel,
    command: CommandTrait,
    trait_cls: type,
    method: str,
    code: str,
) -> None:
    """Each switch trait's enable() writes its data point as int 1 under dpCommon."""
    await getattr(trait_cls(command), method)()
    assert _sent_dps(fake_rpc_channel) == {"101": {code: 1}}


async def test_switch_disable_sends_zero(fake_rpc_channel: FakeQ10RpcChannel, command: CommandTrait) -> None:
    await ChildLockTrait(command).disable()
    assert _sent_dps(fake_rpc_channel) == {"101": {"47": 0}}


@pytest.mark.parametrize(
    ("frequency", "code"),
    [
        (YXDeviceDustCollectionFrequency.REGULAR, 0),
        (YXDeviceDustCollectionFrequency.INTERVAL_30, 30),
        (YXDeviceDustCollectionFrequency.INTERVAL_60, 60),
        (YXDeviceDustCollectionFrequency.INTERVAL_15, 15),
    ],
)
async def test_set_dust_frequency_writes_interval_code(
    fake_rpc_channel: FakeQ10RpcChannel,
    command: CommandTrait,
    frequency: YXDeviceDustCollectionFrequency,
    code: int,
) -> None:
    """Frequency enum writes its interval code under dpDustSetting (50)."""
    await DustCollectionTrait(command).set_frequency(frequency)
    assert _sent_dps(fake_rpc_channel) == {"101": {"50": code}}

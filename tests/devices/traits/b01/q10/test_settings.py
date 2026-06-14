"""Tests for the Q10 B01 settings writer trait."""

import json
from typing import cast

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceDustCollectionFrequency
from roborock.devices.traits.b01.q10.command import CommandTrait
from roborock.devices.traits.b01.q10.settings import SettingsTrait
from roborock.devices.transport.mqtt_channel import MqttChannel
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture
def fake_channel() -> FakeChannel:
    return FakeChannel()


@pytest.fixture
def settings(fake_channel: FakeChannel) -> SettingsTrait:
    return SettingsTrait(CommandTrait(cast(MqttChannel, fake_channel)))


def _sent_dps(fake_channel: FakeChannel) -> dict:
    assert len(fake_channel.published_messages) == 1
    payload = fake_channel.published_messages[0].payload
    assert payload is not None
    return json.loads(payload)["dps"]


async def test_set_volume_uses_common_wrapper(fake_channel: FakeChannel, settings: SettingsTrait) -> None:
    """Volume writes are wrapped in dpCommon (101) -> {"26": value}."""
    await settings.set_volume(55)
    assert _sent_dps(fake_channel) == {"101": {"26": 55}}


@pytest.mark.parametrize("volume", [-1, 101, 1000])
async def test_set_volume_rejects_out_of_range(settings: SettingsTrait, volume: int) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        await settings.set_volume(volume)


@pytest.mark.parametrize(
    ("call", "code"),
    [
        ("set_child_lock", "47"),
        ("set_do_not_disturb", "25"),
        ("set_button_light", "77"),
        ("set_dust_collection", "37"),
    ],
)
async def test_boolean_setters_write_common_wrapped_dp(
    fake_channel: FakeChannel, settings: SettingsTrait, call: str, code: str
) -> None:
    """Each boolean setter writes its data point as int 1/0 under dpCommon."""
    await getattr(settings, call)(True)
    assert _sent_dps(fake_channel) == {"101": {code: 1}}


async def test_boolean_setter_disable_sends_zero(fake_channel: FakeChannel, settings: SettingsTrait) -> None:
    await settings.set_child_lock(False)
    assert _sent_dps(fake_channel) == {"101": {"47": 0}}


@pytest.mark.parametrize(
    ("frequency", "code"),
    [
        (YXDeviceDustCollectionFrequency.DAILY, 0),
        (YXDeviceDustCollectionFrequency.INTERVAL_30, 30),
        (60, 60),
        (15, 15),
    ],
)
async def test_set_dust_frequency_writes_interval_code(
    fake_channel: FakeChannel, settings: SettingsTrait, frequency: object, code: int
) -> None:
    """Frequency (enum or int) writes its interval code under dpDustSetting (50)."""
    await settings.set_dust_collection_frequency(frequency)  # type: ignore[arg-type]
    assert _sent_dps(fake_channel) == {"101": {"50": code}}


@pytest.mark.parametrize("bad", [1, 7, 90, -1])
async def test_set_dust_frequency_rejects_invalid(settings: SettingsTrait, bad: int) -> None:
    with pytest.raises(ValueError, match="dust collection frequency"):
        await settings.set_dust_collection_frequency(bad)

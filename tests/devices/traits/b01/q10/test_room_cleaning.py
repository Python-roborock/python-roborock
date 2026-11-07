"""Tests for customized Q10 room-cleaning commands and pushed settings."""

import base64

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    Q10CleanCount,
    Q10RoomCleanType,
    Q10RoomFanLevel,
    YXCleanLine,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10RoomCleanSettings
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import encode_room_clean_settings

from .conftest import FakeB01Q10Channel


def _settings(room_id: int = 3, *, fan: Q10RoomFanLevel = Q10RoomFanLevel.TURBO) -> Q10RoomCleanSettings:
    return Q10RoomCleanSettings(
        room_id=room_id,
        fan_level=fan,
        water_level=YXWaterLevel.HIGH,
        clean_type=Q10RoomCleanType.VAC_AND_MOP,
        clean_count=Q10CleanCount.TWICE,
        clean_line=YXCleanLine.FINE,
    )


def _complete_payload(settings: Q10RoomCleanSettings) -> str:
    properties = bytearray(26)
    properties[0:2] = settings.room_id.to_bytes(2, "big")
    properties[3:5] = b"\xff\xff"
    properties[5:7] = settings.clean_count.code.to_bytes(2, "big")
    properties[7] = settings.clean_type.code
    properties[8] = settings.fan_level.code
    properties[9] = settings.water_level.code
    properties[10] = 0xFF
    properties[11] = settings.clean_line.code
    name = b"Example"
    name_block = bytes((len(name),)) + name + bytes(19 - len(name))
    return base64.b64encode(b"\x01" + properties + name_block + b"\x00").decode()


async def test_set_settings_publishes_then_requests_full_settings(
    q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel
) -> None:
    settings = (_settings(),)
    await q10_api.room_cleaning.set_settings(settings)
    assert fake_channel.published_commands == [
        (B01_Q10_DP.COMMON, {"62": encode_room_clean_settings(settings)}),
        (B01_Q10_DP.COMMON, {"63": 0}),
    ]
    assert q10_api.room_cleaning.settings == ()


async def test_clean_rooms_sends_settings_mode_and_start_in_order(
    q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel
) -> None:
    settings = (_settings(3), _settings(9))
    await q10_api.vacuum.clean_rooms(settings)
    assert fake_channel.published_commands == [
        (B01_Q10_DP.COMMON, {"62": encode_room_clean_settings(settings)}),
        (B01_Q10_DP.CLEAN_MODE, 4),
        (B01_Q10_DP.START_CLEAN, {"cmd": 2, "clean_paramters": [3, 9]}),
    ]


@pytest.mark.parametrize("fail_on", [1, 2, 3])
async def test_publish_failure_stops_remaining_clean_commands(
    q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel, fail_on: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = fake_channel.send_command
    calls = 0

    async def send(command, params=None):
        nonlocal calls
        calls += 1
        if calls == fail_on:
            raise RoborockException("publish failed")
        await original(command, params)

    monkeypatch.setattr(fake_channel, "send_command", send)
    with pytest.raises(RoborockException, match="publish failed"):
        await q10_api.room_cleaning.clean((_settings(),))
    assert calls == fail_on
    assert len(fake_channel.published_commands) == fail_on - 1


async def test_set_settings_failure_does_not_request_refresh(
    q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def send(command, params=None):
        raise RoborockException("publish failed")

    monkeypatch.setattr(fake_channel, "send_command", send)
    with pytest.raises(RoborockException, match="publish failed"):
        await q10_api.room_cleaning.set_settings((_settings(),))
    assert fake_channel.published_commands == []


def test_full_push_replaces_and_compact_push_upserts(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    notified = []
    trait.add_update_listener(lambda: notified.append(True))
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(_settings(3))})
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((_settings(9),))})
    assert trait.settings == (_settings(3), _settings(9))
    changed = _settings(3, fan=Q10RoomFanLevel.MAX)
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((changed,))})
    assert trait.settings == (changed, _settings(9))
    assert trait.settings_for_room(3) == changed
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(_settings(1))})
    assert trait.settings == (_settings(1),)
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "invalid"})
    assert trait.settings == (_settings(1),)
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})
    assert trait.settings == ()
    assert trait.settings_available
    assert len(notified) == 5


@pytest.mark.parametrize("field", ["fan_level", "water_level", "clean_type", "clean_count", "clean_line"])
def test_unknown_setting_cannot_be_written(field: str) -> None:
    settings = _settings()
    setattr(settings, field, type(getattr(settings, field)).UNKNOWN)
    with pytest.raises(ValueError, match=field):
        encode_room_clean_settings((settings,))


@pytest.mark.parametrize("rooms", [(), (_settings(-1),), (_settings(256),), (_settings(), _settings())])
def test_semantic_room_guards(rooms: tuple[Q10RoomCleanSettings, ...]) -> None:
    with pytest.raises(ValueError):
        encode_room_clean_settings(rooms)

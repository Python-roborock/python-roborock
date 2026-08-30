"""Tests for Q10 customized room-cleaning controls."""

import asyncio
import base64

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    Q10CleanCount,
    Q10RoomCleanType,
    Q10RoomFanLevel,
    YXCleanLine,
    YXCleanType,
    YXDeviceCleanTask,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10ReportedRoomCleanSettings, Q10RoomCleanSettings
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.room_cleaning import RoomCleaningTrait
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import encode_room_clean_settings

from .conftest import FakeB01Q10Channel


@pytest.fixture(name="room_cleaning")
def room_cleaning_fixture(q10_api: Q10PropertiesApi) -> RoomCleaningTrait:
    return q10_api.room_cleaning


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


def _seed_rooms(room_cleaning: RoomCleaningTrait, *settings: Q10RoomCleanSettings) -> None:
    records = b"".join(base64.b64decode(_complete_payload(room))[1:] for room in settings)
    room_cleaning.update_from_dps(
        {B01_Q10_DP.CUSTOMER_CLEAN: base64.b64encode(bytes((len(settings),)) + records).decode()}
    )


def _reported(settings: Q10RoomCleanSettings) -> Q10ReportedRoomCleanSettings:
    return Q10ReportedRoomCleanSettings(**settings.__dict__)


async def test_refresh_requests_complete_room_settings(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    await room_cleaning.refresh()

    assert fake_channel.published_commands == [(B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0})]


def test_empty_complete_response_marks_settings_available_and_notifies(room_cleaning: RoomCleaningTrait) -> None:
    event = asyncio.Event()
    room_cleaning.add_update_listener(event.set)

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})

    assert room_cleaning.settings_available is True
    assert room_cleaning.settings == ()
    assert event.is_set()


async def test_set_settings_sends_compact_payload_without_mutating_state(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    settings = [_settings()]
    _seed_rooms(room_cleaning, *settings)

    task = asyncio.create_task(room_cleaning.set_settings(settings))
    await asyncio.sleep(0)
    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings(settings)})
    await task

    assert fake_channel.published_commands == [
        (
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.CUSTOMER_CLEAN.code): encode_room_clean_settings(settings)},
        ),
        (B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN_REQUEST.code): 0}),
    ]
    assert room_cleaning.settings == (_reported(settings[0]),)


async def test_set_settings_accepts_authoritative_response_when_echo_is_missing(
    room_cleaning: RoomCleaningTrait,
) -> None:
    settings = _settings()
    _seed_rooms(room_cleaning, settings)
    task = asyncio.create_task(room_cleaning.set_settings((settings,)))
    await asyncio.sleep(0)

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(settings)})
    await task


def test_complete_response_updates_immutable_state_and_notifies(room_cleaning: RoomCleaningTrait) -> None:
    event = asyncio.Event()
    room_cleaning.add_update_listener(event.set)
    settings = _settings()

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(settings)})

    assert room_cleaning.settings == (_reported(settings),)
    assert room_cleaning.settings_for_room(settings.room_id) == _reported(settings)
    assert room_cleaning.settings_for_room(99) is None
    assert event.is_set()


def test_compact_echo_and_malformed_push_do_not_replace_state(room_cleaning: RoomCleaningTrait) -> None:
    settings = _settings()
    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(settings)})

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((_settings(9),))})
    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "invalid"})

    assert room_cleaning.settings == (_reported(settings),)


async def test_clean_waits_for_confirmation_then_starts_selected_rooms(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    settings = (_settings(), _settings(9, fan=Q10RoomFanLevel.MAX_PLUS))
    _seed_rooms(room_cleaning, *settings)
    payload = encode_room_clean_settings(settings)
    task = asyncio.create_task(room_cleaning.clean(settings))
    await asyncio.sleep(0)

    assert fake_channel.published_commands == [(B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN.code): payload})]

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: payload})
    await task

    assert fake_channel.published_commands == [
        (B01_Q10_DP.COMMON, {str(B01_Q10_DP.CUSTOMER_CLEAN.code): payload}),
        (B01_Q10_DP.CLEAN_MODE, YXCleanType.CUSTOMIZED.code),
        (
            B01_Q10_DP.START_CLEAN,
            {
                "cmd": YXDeviceCleanTask.ELECTORAL.code,
                "clean_paramters": [3, 9],
            },
        ),
    ]


async def test_clean_accepts_matching_complete_response(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    settings = _settings()
    _seed_rooms(room_cleaning, settings)
    task = asyncio.create_task(room_cleaning.clean((settings,)))
    await asyncio.sleep(0)

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(settings)})
    await task

    assert len(fake_channel.published_commands) == 3
    assert room_cleaning.settings == (_reported(settings),)


async def test_clean_serializes_concurrent_configuration_sequences(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    first = _settings(3)
    second = _settings(9)
    _seed_rooms(room_cleaning, first, second)
    first_task = asyncio.create_task(room_cleaning.clean((first,)))
    second_task = asyncio.create_task(room_cleaning.clean((second,)))
    await asyncio.sleep(0)

    assert len(fake_channel.published_commands) == 1
    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((first,))})
    await first_task
    await asyncio.sleep(0)
    assert len(fake_channel.published_commands) == 4

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((second,))})
    await second_task

    assert [command for command, _ in fake_channel.published_commands] == [
        B01_Q10_DP.COMMON,
        B01_Q10_DP.CLEAN_MODE,
        B01_Q10_DP.START_CLEAN,
        B01_Q10_DP.COMMON,
        B01_Q10_DP.CLEAN_MODE,
        B01_Q10_DP.START_CLEAN,
    ]


async def test_clean_rejects_invalid_settings_without_publishing(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    with pytest.raises(ValueError, match="between 1 and 255"):
        await room_cleaning.clean(())

    assert fake_channel.published_commands == []


async def test_clean_does_not_start_without_confirmation(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("roborock.devices.traits.b01.q10.room_cleaning._WRITE_CONFIRMATION_TIMEOUT", 0.01)
    _seed_rooms(room_cleaning, _settings())

    with pytest.raises(RoborockException, match="did not confirm"):
        await room_cleaning.clean((_settings(),))

    assert len(fake_channel.published_commands) == 1


async def test_clean_ignores_unrelated_and_malformed_pushes_while_pending(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    settings = _settings()
    _seed_rooms(room_cleaning, settings)
    task = asyncio.create_task(room_cleaning.clean((settings,)))
    await asyncio.sleep(0)

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "invalid"})
    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((_settings(9),))})
    await asyncio.sleep(0)
    assert not task.done()

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((settings,))})
    await task
    assert len(fake_channel.published_commands) == 3


async def test_cancelled_clean_clears_pending_confirmation(
    room_cleaning: RoomCleaningTrait,
) -> None:
    settings = _settings()
    _seed_rooms(room_cleaning, settings)
    task = asyncio.create_task(room_cleaning.clean((settings,)))
    await asyncio.sleep(0)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((settings,))})


async def test_clean_rejects_unknown_room_before_publishing(
    room_cleaning: RoomCleaningTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    _seed_rooms(room_cleaning, _settings(3))

    with pytest.raises(ValueError, match="Unknown Q10 room_id"):
        await room_cleaning.clean((_settings(9),))

    assert fake_channel.published_commands == []


async def test_room_controls_reject_unverified_model(fake_channel: FakeB01Q10Channel) -> None:
    room_cleaning = create(fake_channel, model="roborock.vacuum.ss99").room_cleaning

    assert room_cleaning.supported is False
    assert room_cleaning.settings_available is False
    with pytest.raises(RoborockException, match="only verified"):
        await room_cleaning.refresh()


async def test_public_state_mutation_cannot_bypass_safety_checks(fake_channel: FakeB01Q10Channel) -> None:
    room_cleaning = create(fake_channel, model="roborock.vacuum.ss99").room_cleaning
    room_cleaning.supported = True
    room_cleaning.settings_available = True
    room_cleaning.settings = (_reported(_settings(3)),)

    with pytest.raises(RoborockException, match="only verified"):
        await room_cleaning.clean((_settings(3),))

    assert fake_channel.published_commands == []


def test_direct_factory_defaults_to_q10_support(fake_channel: FakeB01Q10Channel) -> None:
    api = create(fake_channel)

    assert api.room_cleaning.supported is True
    assert api.vacuum.advanced_cleaning_supported is True


async def test_map_change_invalidates_room_settings_even_when_room_ids_overlap(
    q10_api: Q10PropertiesApi,
) -> None:
    _seed_rooms(q10_api.room_cleaning, _settings(3))
    assert q10_api.room_cleaning.settings_available is True
    q10_api.maps.update_from_dps(
        {
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "first"}, {"id": "second"}],
                "op": "list",
                "result": 1,
            }
        }
    )

    await q10_api.maps.set_current_map("second")

    assert q10_api.room_cleaning.settings_available is False
    assert q10_api.room_cleaning.settings == ()
    with pytest.raises(RoborockException, match="Refresh"):
        await q10_api.room_cleaning.clean((_settings(3),))


async def test_map_change_aborts_pending_clean_before_late_echo(
    q10_api: Q10PropertiesApi,
    fake_channel: FakeB01Q10Channel,
) -> None:
    settings = _settings(3)
    _seed_rooms(q10_api.room_cleaning, settings)
    q10_api.maps.update_from_dps(
        {B01_Q10_DP.MULTI_MAP: {"data": [{"id": "first"}, {"id": "second"}], "op": "list", "result": 1}}
    )
    task = asyncio.create_task(q10_api.room_cleaning.clean((settings,)))
    await asyncio.sleep(0)

    await q10_api.maps.set_current_map("second")
    q10_api.room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((settings,))})

    with pytest.raises(RoborockException, match="map changed"):
        await task
    assert [command for command, _ in fake_channel.published_commands] == [B01_Q10_DP.COMMON, B01_Q10_DP.COMMON]


def test_external_map_change_invalidates_room_settings(q10_api: Q10PropertiesApi) -> None:
    _seed_rooms(q10_api.room_cleaning, _settings(3))
    q10_api.maps.update_from_dps(
        {B01_Q10_DP.MULTI_MAP: {"data": [{"id": "first"}, {"id": "second"}], "op": "list", "result": 1}}
    )

    q10_api.maps.update_from_dps(
        {B01_Q10_DP.MULTI_MAP: {"data": [{"id": "second"}, {"id": "first"}], "op": "list", "result": 1}}
    )

    assert q10_api.room_cleaning.settings_available is False
    assert q10_api.room_cleaning.settings == ()

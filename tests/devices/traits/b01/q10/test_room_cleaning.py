"""Tests for customized Q10 room-cleaning commands and pushed settings."""

import base64
import pathlib
from dataclasses import replace

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
        (B01_Q10_DP.COMMON, {"62": "AQMDAwECAg=="}),
        (B01_Q10_DP.COMMON, {"63": 0}),
    ]
    assert q10_api.room_cleaning.settings is None


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
    assert trait.settings == [_settings(3), _settings(9)]
    changed = _settings(3, fan=Q10RoomFanLevel.MAX)
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: encode_room_clean_settings((changed,))})
    assert trait.settings == [changed, _settings(9)]
    assert trait.settings_for_room(3) == changed
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(_settings(1))})
    assert trait.settings == [_settings(1)]
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "invalid"})
    assert trait.settings == [_settings(1)]
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})
    assert trait.settings == []
    assert len(notified) == 5


async def test_refresh_requests_complete_settings(q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel) -> None:
    await q10_api.room_cleaning.refresh()
    assert fake_channel.published_commands == [(B01_Q10_DP.COMMON, {"63": 0})]
    assert q10_api.room_cleaning.settings is None


def test_settings_for_room_unpopulated(q10_api: Q10PropertiesApi) -> None:
    assert q10_api.room_cleaning.settings_for_room(3) is None
    assert q10_api.room_cleaning.as_dict() == {}
    assert q10_api.as_dict()["room_cleaning"] == {}


def test_settings_for_room_missing(q10_api: Q10PropertiesApi) -> None:
    q10_api.room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(_settings(3))})
    assert q10_api.room_cleaning.settings_for_room(9) is None


def test_repeated_pushes_do_not_notify(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    notified: list[bool] = []
    trait.add_update_listener(lambda: notified.append(True))
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "invalid"})
    assert trait.settings is None
    assert not notified
    compact = encode_room_clean_settings((_settings(3),))
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: compact})
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: compact})
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: _complete_payload(_settings(3))})
    assert trait.settings == [_settings(3)]
    assert len(notified) == 1
    assert isinstance(trait.as_dict()["settings"], list)
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})
    assert trait.settings == []
    assert trait.as_dict() == {"settings": []}
    assert trait.settings_for_room(3) is None
    assert len(notified) == 2


def test_first_empty_push_is_reported(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    notified: list[bool] = []
    trait.add_update_listener(lambda: notified.append(True))
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AA=="})
    assert trait.settings == []
    assert trait.as_dict() == {"settings": []}
    assert notified == [True]


@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.parametrize(
    ("field", "compact_offset", "full_offset", "width"),
    [
        ("fan_level", 1, 8, 1),
        ("water_level", 2, 9, 1),
        ("clean_type", 3, 7, 1),
        ("clean_count", 4, 5, 2),
        ("clean_line", 5, 11, 1),
    ],
)
def test_unknown_mode_codes_use_enum_fallback(
    q10_api: Q10PropertiesApi, field: str, compact_offset: int, full_offset: int, width: int, complete: bool
) -> None:
    trait = q10_api.room_cleaning
    payload = _complete_payload(_settings()) if complete else "AQMDAwECAg=="
    raw = bytearray(base64.b64decode(payload))
    offset = full_offset + 1 if complete else compact_offset + 1
    code_width = width if complete else 1
    raw[offset : offset + code_width] = (99).to_bytes(code_width, "big")
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: base64.b64encode(raw).decode()})
    expected = _settings()
    setattr(expected, field, type(getattr(expected, field)).UNKNOWN)
    assert trait.settings == [expected]
    # A compact update must preserve the cached unknown code during conversion.
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AQkDAwECAg=="})
    assert trait.settings == [expected, _settings(9)]


@pytest.mark.parametrize("complete", [False, True])
def test_zero_mode_codes_are_preserved(q10_api: Q10PropertiesApi, complete: bool) -> None:
    settings = replace(_settings(), water_level=YXWaterLevel.OFF, clean_line=YXCleanLine.FAST)
    payload = _complete_payload(settings) if complete else "AQMDAAECAA=="
    q10_api.room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: payload})
    assert q10_api.room_cleaning.settings == [settings]


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("payload", [None, 1, {}, [], "invalid", "", "AQAA"])
def test_invalid_push_does_not_change_settings(q10_api: Q10PropertiesApi, populated: bool, payload: object) -> None:
    trait = q10_api.room_cleaning
    if populated:
        trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AQMDAwECAg=="})
    before = trait.settings
    notified: list[bool] = []
    trait.add_update_listener(lambda: notified.append(True))
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: payload})
    trait.update_from_dps({B01_Q10_DP.BATTERY: 100})
    assert trait.settings == before
    assert not notified


def test_malformed_later_record_is_atomic(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AQMDAwECAg=="})
    notified: list[bool] = []
    trait.add_update_listener(lambda: notified.append(True))
    first = base64.b64decode(_complete_payload(_settings(9)))[1:]
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: base64.b64encode(b"\x02" + first + b"\x00").decode()})
    assert trait.settings == [_settings(3)]
    assert not notified


def test_compact_update_preserves_existing_room_order(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AgMDAwECAgkDAwECAg=="})
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AgkEAwECAgEBAwECAg=="})
    assert trait.settings == [
        _settings(3),
        _settings(9, fan=Q10RoomFanLevel.MAX),
        _settings(1, fan=Q10RoomFanLevel.QUIET),
    ]


def test_sanitized_full_capture_builds_typed_models(q10_api: Q10PropertiesApi) -> None:
    payload = (
        pathlib.Path("tests/protocols/testdata/b01_q10_protocol/customer_clean_full_sanitized.b64").read_text().strip()
    )
    q10_api.room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: payload})
    assert q10_api.room_cleaning.settings == [
        _settings(1, fan=Q10RoomFanLevel.QUIET),
        _settings(2, fan=Q10RoomFanLevel.MAX_PLUS),
        replace(
            _settings(3, fan=Q10RoomFanLevel.MAX_PLUS),
            water_level=YXWaterLevel.MEDIUM,
            clean_type=Q10RoomCleanType.VACUUM,
        ),
        replace(
            _settings(4, fan=Q10RoomFanLevel.MAX_PLUS),
            water_level=YXWaterLevel.MEDIUM,
            clean_type=Q10RoomCleanType.VACUUM,
        ),
        _settings(5, fan=Q10RoomFanLevel.QUIET),
        _settings(6, fan=Q10RoomFanLevel.MAX_PLUS),
    ]


@pytest.mark.parametrize("method", ["set_settings", "clean_rooms"])
async def test_commands_leave_reported_settings_unchanged(q10_api: Q10PropertiesApi, method: str) -> None:
    q10_api.room_cleaning.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AQMDAwECAg=="})
    target = q10_api.room_cleaning if method == "set_settings" else q10_api.vacuum
    await getattr(target, method)((_settings(9),))
    assert q10_api.room_cleaning.settings == [_settings(3)]


def test_populated_diagnostics_use_model_field_names_and_enum_labels(q10_api: Q10PropertiesApi) -> None:
    trait = q10_api.room_cleaning
    trait.update_from_dps({B01_Q10_DP.CUSTOMER_CLEAN: "AQMDAwECAg=="})
    expected = {
        "settings": [
            {
                "roomId": 3,
                "fanLevel": "turbo",
                "waterLevel": "high",
                "cleanType": "vac_and_mop",
                "cleanCount": "twice",
                "cleanLine": "fine",
            }
        ]
    }
    assert trait.as_dict() == expected
    assert q10_api.as_dict()["room_cleaning"] == expected

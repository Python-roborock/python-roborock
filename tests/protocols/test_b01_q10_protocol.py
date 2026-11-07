"""Tests for the B01 protocol message encoding and decoding."""

import base64
import json
import logging
import pathlib
from base64 import b64decode
from collections.abc import Generator
from typing import Any

import pytest
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    Q10CleanCount,
    Q10RoomCleanType,
    Q10RoomFanLevel,
    YXCleanLine,
    YXWaterLevel,
)
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint, Q10RoomCleanSettings
from roborock.data.code_mappings import completed_warnings
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import Q10CleanRecordDetail, Q10MapPacket, Q10MapPacketKind, Q10TracePacket
from roborock.protocols.b01_q10_protocol import (
    CleanParams,
    Q10DpsUpdate,
    decode_message,
    decode_room_clean_settings,
    decode_rpc_response,
    encode_clean_params,
    encode_mqtt_payload,
    encode_room_clean_settings,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_q10_protocol/")
TESTDATA_FILES = list(TESTDATA_PATH.glob("*.json"))
TESTDATA_IDS = [x.stem for x in TESTDATA_FILES]

MAP_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_trace.bin")


def test_encode_clean_params_source_verified_fixture() -> None:
    """Zone parameters match a payload verified against ss07 hardware."""
    params = CleanParams(
        Q10RoborockPoint(25650, 25700),
        Q10RoborockPoint(25550, 25600),
        clean_count=2,
    )

    assert b64decode(encode_clean_params(params)) == bytes(
        (
            1,
            2,
            1,
            4,
            0,
            10,
            0,
            20,
            0,
            30,
            0,
            20,
            0,
            30,
            0,
            40,
            0,
            10,
            0,
            40,
            0,
            *([0] * 19),
        )
    )


@pytest.mark.parametrize("clean_count", [0, 4, True])
def test_encode_clean_params_rejects_invalid_clean_count(clean_count: int) -> None:
    """The protocol validates the device's supported clean-count range."""
    with pytest.raises(ValueError, match="clean_count must be between 1 and 3"):
        encode_clean_params(
            CleanParams(
                Q10RoborockPoint(25550, 25600),
                Q10RoborockPoint(25650, 25700),
                clean_count,
            )
        )


def test_encode_clean_params_rejects_empty_zone() -> None:
    """Two corners must enclose a non-empty rectangle."""
    with pytest.raises(ValueError, match="zone corners must enclose an area"):
        encode_clean_params(
            CleanParams(
                Q10RoborockPoint(25550, 25600),
                Q10RoborockPoint(25550, 25700),
            )
        )


def test_encode_clean_params_rejects_untyped_corners() -> None:
    """The wire encoder accepts only common-coordinate point objects."""
    with pytest.raises(ValueError, match="zone corners must be Q10RoborockPoint"):
        encode_clean_params(CleanParams((25550, 25600), (25650, 25700)))  # type: ignore[arg-type]


def _message(payload: bytes, protocol: RoborockMessageProtocol) -> RoborockMessage:
    return RoborockMessage(protocol=protocol, payload=payload, version=b"B01")


def test_decode_message_dps_update() -> None:
    """A non-MAP_RESPONSE message decodes into a Q10DpsUpdate."""
    message = _message(b'{"dps": {"122": 100}}', RoborockMessageProtocol.RPC_RESPONSE)
    decoded = decode_message(message)
    assert decoded == Q10DpsUpdate(dps={B01_Q10_DP.BATTERY: 100})


def test_decode_message_common_multi_map_list() -> None:
    """A nested dpCommon map-list response is flattened into dpMultiMap."""
    message = _message(
        b'{"dps":{"101":{"61":{"data":[{"id":"12345","name":"Map","timestamp":1}],"op":"list","result":1}}}}',
        RoborockMessageProtocol.RPC_RESPONSE,
    )

    decoded = decode_message(message)

    assert decoded == Q10DpsUpdate(
        dps={
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345", "name": "Map", "timestamp": 1}],
                "op": "list",
                "result": 1,
            }
        }
    )


def test_decode_message_map_packet() -> None:
    """A MAP_RESPONSE 01 01 payload decodes into a Q10MapPacket."""
    message = _message(MAP_FIXTURE.read_bytes(), RoborockMessageProtocol.MAP_RESPONSE)
    decoded = decode_message(message)
    assert isinstance(decoded, Q10MapPacket)
    assert {room.id: room.name for room in decoded.rooms} == {2: "Living Room", 3: "Bedroom"}


@pytest.mark.parametrize(
    ("marker", "kind"),
    [
        (b"\x03\x01", Q10MapPacketKind.CLEAN_RECORD_DETAIL),
        (b"\x04\x01", Q10MapPacketKind.SAVED_MAP_DETAIL),
    ],
)
def test_decode_message_archived_map_packet(marker: bytes, kind: Q10MapPacketKind) -> None:
    """The decoder recognizes both archived map-detail markers."""
    fixture = MAP_FIXTURE.read_bytes()
    decoded = decode_message(_message(marker + fixture[2:], RoborockMessageProtocol.MAP_RESPONSE))

    if kind is Q10MapPacketKind.CLEAN_RECORD_DETAIL:
        assert isinstance(decoded, Q10CleanRecordDetail)
        assert decoded.map.kind is kind
        assert decoded.trace is None
    else:
        assert isinstance(decoded, Q10MapPacket)
        assert decoded.kind is kind


def test_decode_message_trace_packet() -> None:
    """A MAP_RESPONSE 02 01 payload decodes into a Q10TracePacket."""
    message = _message(TRACE_FIXTURE.read_bytes(), RoborockMessageProtocol.MAP_RESPONSE)
    decoded = decode_message(message)
    assert isinstance(decoded, Q10TracePacket)
    # This docked capture carries only a heading (no path points); see the
    # parser tests for the full byte-level decode.
    assert decoded.points == []
    assert decoded.heading == 169


def test_decode_message_unknown_map_marker_returns_none() -> None:
    """A MAP_RESPONSE with an unrecognized marker is skipped (returns None)."""
    assert decode_message(_message(b"\x09\x09junk", RoborockMessageProtocol.MAP_RESPONSE)) is None
    assert decode_message(_message(b"", RoborockMessageProtocol.MAP_RESPONSE)) is None


@pytest.fixture(autouse=True)
def fixed_time_fixture() -> Generator[None, None, None]:
    """Fixture to freeze time for predictable request IDs."""
    with freeze_time("2025-01-20T12:00:00"):
        yield


@pytest.mark.parametrize("filename", TESTDATA_FILES, ids=TESTDATA_IDS)
def test_decode_rpc_payload(filename: str, snapshot: SnapshotAssertion) -> None:
    """Test decoding a B01 RPC response protocol message."""
    with open(filename, "rb") as f:
        payload = f.read()

    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    decoded_message = decode_rpc_response(message)
    assert json.dumps(decoded_message, indent=2) == snapshot


@pytest.mark.parametrize(
    ("payload", "expected_error_message"),
    [
        (b"", "missing payload"),
        (b"n", "Invalid B01 json payload"),
        (b"{}", "missing 'dps'"),
        (b'{"dps": []}', "'dps' should be a dictionary"),
        (b'{"dps": {"not_a_number": 123}}', "dps key is not a valid integer"),
        (b'{"dps": {"101": 123}}', "Invalid dpCommon format: expected dict"),
        (b'{"dps": {"101": {"not_a_number": 123}}}', "Invalid dpCommon format: dps key is not a valid intege"),
    ],
)
def test_decode_invalid_rpc_payload(payload: bytes, expected_error_message: str) -> None:
    """Test decoding a B01 RPC response protocol message."""
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )
    with pytest.raises(RoborockException, match=expected_error_message):
        decode_rpc_response(message)


def test_decode_unknown_dps_code(caplog: pytest.LogCaptureFixture) -> None:
    """Unknown data points are dropped silently, without logging warnings."""
    completed_warnings.discard("909090 is not a valid code for B01_Q10_DP")
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"dps": {"909090": 123, "122": 100}}',
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    with caplog.at_level(logging.WARNING):
        decoded_message = decode_rpc_response(message)
    assert decoded_message == {
        B01_Q10_DP.BATTERY: 100,
    }
    assert "not a valid code" not in caplog.text


def test_decode_mapped_112_113_dps() -> None:
    """Verify newly mapped status codes 112 and 113 decode correctly."""
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"dps": {"112": 0, "113": 0}}',
        seq=12751,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )
    decoded_message = decode_rpc_response(message)
    assert decoded_message == {
        B01_Q10_DP.UNKNOWN_112: 0,
        B01_Q10_DP.UNKNOWN_113: 0,
    }


@pytest.mark.parametrize(
    ("command", "params"),
    [
        (B01_Q10_DP.REQUEST_DPS, {}),
        (B01_Q10_DP.REQUEST_DPS, None),
        (B01_Q10_DP.START_CLEAN, {"cmd": 1}),
        (B01_Q10_DP.WATER_LEVEL, YXWaterLevel.MEDIUM.code),
    ],
)
def test_encode_mqtt_payload(command: B01_Q10_DP, params: dict[str, Any], snapshot) -> None:
    """Test encoding of MQTT payload for B01 Q10 commands."""

    message = encode_mqtt_payload(command, params)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"B01"
    assert message.payload is not None

    # Snapshot the raw payload to ensure stable encoding. We verify it is
    # valid json
    assert snapshot == message.payload

    json.loads(message.payload.decode())


def _room_settings(
    room_id: int = 3,
    *,
    fan: Q10RoomFanLevel = Q10RoomFanLevel.TURBO,
    water: YXWaterLevel = YXWaterLevel.HIGH,
    clean_type: Q10RoomCleanType = Q10RoomCleanType.VAC_AND_MOP,
    count: Q10CleanCount = Q10CleanCount.TWICE,
    line: YXCleanLine = YXCleanLine.FINE,
) -> Q10RoomCleanSettings:
    return Q10RoomCleanSettings(room_id, fan, water, clean_type, count, line)


def _full_room_record(settings: Q10RoomCleanSettings, name: str = "Example") -> bytes:
    properties = bytearray(26)
    properties[0:2] = settings.room_id.to_bytes(2, "big")
    properties[2] = 1
    properties[3:5] = b"\xff\xff"
    properties[5:7] = settings.clean_count.code.to_bytes(2, "big")
    properties[7] = settings.clean_type.code
    properties[8] = settings.fan_level.code
    properties[9] = settings.water_level.code
    properties[10] = 0xFF
    properties[11] = settings.clean_line.code
    encoded_name = name.encode()
    name_block = bytes((len(encoded_name),)) + encoded_name + bytes(19 - len(encoded_name))
    return bytes(properties) + name_block + b"\x00"


def test_encode_room_clean_settings_uses_compact_format() -> None:
    settings = [_room_settings(), _room_settings(9, fan=Q10RoomFanLevel.MAX_PLUS, water=YXWaterLevel.LOW)]

    encoded = encode_room_clean_settings(settings)

    assert base64.b64decode(encoded) == bytes((2, 3, 3, 3, 1, 2, 2, 9, 5, 1, 1, 2, 2))
    assert settings == [
        _room_settings(),
        _room_settings(9, fan=Q10RoomFanLevel.MAX_PLUS, water=YXWaterLevel.LOW),
    ]


def test_decode_room_clean_settings_distinguishes_echo_and_complete_response() -> None:
    first = _room_settings()
    second = _room_settings(9, fan=Q10RoomFanLevel.MAX_PLUS, water=YXWaterLevel.LOW)
    echo = decode_room_clean_settings(encode_room_clean_settings((first, second)))
    complete = decode_room_clean_settings(
        base64.b64encode(b"\x02" + _full_room_record(first) + _full_room_record(second)).decode()
    )

    assert echo.settings == (
        Q10RoomCleanSettings(**first.__dict__),
        Q10RoomCleanSettings(**second.__dict__),
    )
    assert echo.complete is False
    assert complete.settings == (
        Q10RoomCleanSettings(**first.__dict__),
        Q10RoomCleanSettings(**second.__dict__),
    )
    assert complete.complete is True


def test_decode_room_clean_settings_preserves_unknown_values() -> None:
    record = bytearray(_full_room_record(_room_settings()))
    record[8] = 42
    record[11] = 99

    decoded = decode_room_clean_settings(base64.b64encode(b"\x01" + record).decode())

    assert decoded.settings[0].fan_level is Q10RoomFanLevel.UNKNOWN
    assert decoded.settings[0].clean_line is YXCleanLine.UNKNOWN


def test_decode_room_clean_settings_empty_complete_response() -> None:
    decoded = decode_room_clean_settings("AA==")

    assert decoded.settings == ()
    assert decoded.complete is True


def test_encode_room_clean_settings_rejects_more_than_wire_count() -> None:
    with pytest.raises(ValueError, match="between 1 and 255"):
        encode_room_clean_settings([_room_settings(room_id) for room_id in range(256)])


def test_encode_room_clean_settings_matches_physical_echoes() -> None:
    candidate = Q10RoomCleanSettings(
        1,
        Q10RoomFanLevel.TURBO,
        YXWaterLevel.MEDIUM,
        Q10RoomCleanType.VAC_AND_MOP,
        Q10CleanCount.ONCE,
        YXCleanLine.DAILY,
    )
    restored = Q10RoomCleanSettings(
        1,
        Q10RoomFanLevel.QUIET,
        YXWaterLevel.HIGH,
        Q10RoomCleanType.VAC_AND_MOP,
        Q10CleanCount.TWICE,
        YXCleanLine.FINE,
    )

    assert encode_room_clean_settings((candidate,)) == "AQEDAgEBAQ=="
    assert encode_room_clean_settings((restored,)) == "AQEBAwECAg=="
    assert decode_room_clean_settings("AQEDAgEBAQ==").settings == (Q10RoomCleanSettings(**candidate.__dict__),)
    assert decode_room_clean_settings("AQEBAwECAg==").settings == (Q10RoomCleanSettings(**restored.__dict__),)


def test_encode_room_clean_settings_supports_three_pass_protocol_value() -> None:
    settings = _room_settings(count=Q10CleanCount.THREE_TIMES)

    assert base64.b64decode(encode_room_clean_settings((settings,)))[5] == 3


@pytest.mark.parametrize(
    "payload",
    [
        "not-base64",
        "",
        base64.b64encode(b"\x01\x00").decode(),
        base64.b64encode(b"\x01" + _full_room_record(_room_settings())[:-1]).decode(),
        base64.b64encode(b"\x01" + _full_room_record(_room_settings()) + b"extra").decode(),
        base64.b64encode(b"\x02" + bytes((3, 3, 3, 1, 2, 2)) * 2).decode(),
        base64.b64encode(b"\x02" + _full_room_record(_room_settings()) * 2).decode(),
    ],
)
def test_decode_room_clean_settings_rejects_malformed_payload(payload: str) -> None:
    with pytest.raises(RoborockException, match="customized-room"):
        decode_room_clean_settings(payload)


def test_decode_sanitized_physical_six_room_capture() -> None:
    payload = (TESTDATA_PATH / "customer_clean_full_sanitized.b64").read_text().strip()

    decoded = decode_room_clean_settings(payload)

    assert decoded.complete is True
    assert len(base64.b64decode(payload)) == 283
    assert list(decoded.settings) == [
        Q10RoomCleanSettings(
            1,
            Q10RoomFanLevel.QUIET,
            YXWaterLevel.HIGH,
            Q10RoomCleanType.VAC_AND_MOP,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
        Q10RoomCleanSettings(
            2,
            Q10RoomFanLevel.MAX_PLUS,
            YXWaterLevel.HIGH,
            Q10RoomCleanType.VAC_AND_MOP,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
        Q10RoomCleanSettings(
            3,
            Q10RoomFanLevel.MAX_PLUS,
            YXWaterLevel.MEDIUM,
            Q10RoomCleanType.VACUUM,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
        Q10RoomCleanSettings(
            4,
            Q10RoomFanLevel.MAX_PLUS,
            YXWaterLevel.MEDIUM,
            Q10RoomCleanType.VACUUM,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
        Q10RoomCleanSettings(
            5,
            Q10RoomFanLevel.QUIET,
            YXWaterLevel.HIGH,
            Q10RoomCleanType.VAC_AND_MOP,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
        Q10RoomCleanSettings(
            6,
            Q10RoomFanLevel.MAX_PLUS,
            YXWaterLevel.HIGH,
            Q10RoomCleanType.VAC_AND_MOP,
            Q10CleanCount.TWICE,
            YXCleanLine.FINE,
        ),
    ]

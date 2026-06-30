"""Tests for the B01 protocol message encoding and decoding."""

import json
import logging
import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXWaterLevel
from roborock.data.code_mappings import completed_warnings
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import Q10MapPacket, Q10TracePacket
from roborock.protocols.b01_q10_protocol import (
    Q10DpsUpdate,
    decode_message,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_q10_protocol/")
TESTDATA_FILES = list(TESTDATA_PATH.glob("*.json"))
TESTDATA_IDS = [x.stem for x in TESTDATA_FILES]

MAP_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_trace.bin")


def _message(payload: bytes, protocol: RoborockMessageProtocol) -> RoborockMessage:
    return RoborockMessage(protocol=protocol, payload=payload, version=b"B01")


def test_decode_message_dps_update() -> None:
    """A non-MAP_RESPONSE message decodes into a Q10DpsUpdate."""
    message = _message(b'{"dps": {"122": 100}}', RoborockMessageProtocol.RPC_RESPONSE)
    decoded = decode_message(message)
    assert decoded == Q10DpsUpdate(dps={B01_Q10_DP.BATTERY: 100})


def test_decode_message_map_packet() -> None:
    """A MAP_RESPONSE 01 01 payload decodes into a Q10MapPacket."""
    message = _message(MAP_FIXTURE.read_bytes(), RoborockMessageProtocol.MAP_RESPONSE)
    decoded = decode_message(message)
    assert isinstance(decoded, Q10MapPacket)
    assert {room.id: room.name for room in decoded.rooms} == {2: "Living Room", 3: "Bedroom"}


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
    """Unknown data points are dropped silently, without logging warnings.

    ss07 hardware pushes DPs 112 and 113 (and occasionally others) that this
    library does not model. They must be ignored without emitting "not a valid
    code" warnings, which previously spammed the log on every status push.
    """
    completed_warnings.discard("112 is not a valid code for B01_Q10_DP")
    completed_warnings.discard("113 is not a valid code for B01_Q10_DP")
    completed_warnings.discard("909090 is not a valid code for B01_Q10_DP")
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"dps": {"909090": 123, "112": 0, "113": 0, "122": 100}}',
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

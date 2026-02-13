"""Tests for the B01 protocol message encoding and decoding."""

import json
import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXWaterLevel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_q10_protocol/")
TESTDATA_FILES = list(TESTDATA_PATH.glob("*.json"))
TESTDATA_IDS = [x.stem for x in TESTDATA_FILES]


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


def test_decode_unknown_dps_code() -> None:
    """Test decoding a B01 RPC response protocol message."""
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"dps": {"909090": 123, "122":100}}',
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    decoded_message = decode_rpc_response(message)
    assert decoded_message == {
        B01_Q10_DP.BATTERY: 100,
    }


@pytest.mark.parametrize(
    ("command", "params"),
    [
        (B01_Q10_DP.REQUEST_DPS, {}),
        (B01_Q10_DP.REQUEST_DPS, None),
        (B01_Q10_DP.START_CLEAN, {"cmd": 1}),
        (B01_Q10_DP.WATER_LEVEL, YXWaterLevel.MIDDLE.code),
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

"""Tests for the B01 protocol message encoding and decoding."""

import json
import pathlib
from collections.abc import Generator

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.protocols.b01_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_protocol")
TESTDATA_FILES = list(TESTDATA_PATH.glob("**/*.json"))
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
    ("dps", "command", "params", "msg_id"),
    [
        (
            10000,
            "prop.get",
            {"property": ["status", "fault"]},
            "123456789",
        ),
    ],
)
def test_encode_mqtt_payload(dps: int, command: str, params: dict[str, list[str]], msg_id: str) -> None:
    """Test encoding of MQTT payload for B01 commands."""

    message = encode_mqtt_payload(dps, command, params, msg_id)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"B01"
    assert message.payload is not None
    unpadded = unpad(message.payload, AES.block_size)
    decoded_json = json.loads(unpadded.decode("utf-8"))

    assert decoded_json["dps"][str(dps)]["method"] == command
    assert decoded_json["dps"][str(dps)]["msgId"] == msg_id
    assert decoded_json["dps"][str(dps)]["params"] == params

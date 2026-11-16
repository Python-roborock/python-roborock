"""Tests for the B01 protocol message encoding and decoding."""

import base64
import json
import pathlib
from collections.abc import Generator

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.protocols.b01_q7_protocol import (
    Q7RequestMessage,
    create_map_response_assembler,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_q7_protocol")
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
    ("dps", "command", "params", "msg_id"),
    [
        (
            10000,
            "prop.get",
            {"property": ["status", "fault"]},
            123456789,
        ),
    ],
)
def test_encode_mqtt_payload(dps: int, command: str, params: dict[str, list[str]], msg_id: int) -> None:
    """Test encoding of MQTT payload for B01 commands."""

    message = encode_mqtt_payload(Q7RequestMessage(dps, command, params, msg_id))
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"B01"
    assert message.payload is not None
    unpadded = unpad(message.payload, AES.block_size)
    decoded_json = json.loads(unpadded.decode("utf-8"))

    assert decoded_json["dps"][str(dps)]["method"] == command
    assert decoded_json["dps"][str(dps)]["msgId"] == str(msg_id)
    assert decoded_json["dps"][str(dps)]["params"] == params


def _build_map_msg(
    payload: bytes | None,
    protocol: RoborockMessageProtocol = RoborockMessageProtocol.MAP_RESPONSE,
    *,
    seq: int = 1,
    random: int = 2716216127,
    timestamp: int = 1794578237,
    version: bytes = b"B01",
) -> RoborockMessage:
    return RoborockMessage(
        protocol=protocol,
        payload=payload,
        seq=seq,
        version=version,
        random=random,
        timestamp=timestamp,
    )


def test_map_response_assembler_single_part() -> None:
    """A complete single-part MAP_RESPONSE passes through regardless of MQTT seq."""
    assembler = create_map_response_assembler()
    payload = base64.b64encode(bytes(range(32)))

    assert assembler(_build_map_msg(payload, seq=12750)) == payload


@pytest.mark.parametrize("order", [(0, 1), (1, 0)], ids=["in_order", "out_of_order"])
def test_map_response_assembler_two_parts(order: tuple[int, int]) -> None:
    """Two-part fragmented map frames reassemble in-order and out-of-order."""
    assembler = create_map_response_assembler()
    full = base64.b64encode(bytes(range(48)))
    messages = [
        _build_map_msg(full[:32], RoborockMessageProtocol.MAP_RESPONSE_PART, seq=1),
        _build_map_msg(full[32:], RoborockMessageProtocol.MAP_RESPONSE, seq=2),
    ]

    assert assembler(messages[order[0]]) is None
    assert assembler(messages[order[1]]) == full


@pytest.mark.parametrize(
    "order",
    [(0, 1, 2), (2, 1, 0), (1, 2, 0)],
    ids=["in_order", "reverse", "suffix_first"],
)
def test_map_response_assembler_three_parts(order: tuple[int, int, int]) -> None:
    """Three-part frames wait for seq=1 even when trailing parts form a block-aligned suffix."""
    assembler = create_map_response_assembler()
    # 96 raw bytes -> 128 base64 chars; parts 2+3 alone decode to 48 bytes (a multiple of 16).
    full = base64.b64encode(bytes(range(96)))
    messages = [
        _build_map_msg(full[:64], RoborockMessageProtocol.MAP_RESPONSE_PART, seq=1),
        _build_map_msg(full[64:96], RoborockMessageProtocol.MAP_RESPONSE_PART, seq=2),
        _build_map_msg(full[96:], RoborockMessageProtocol.MAP_RESPONSE, seq=3),
    ]

    assert assembler(messages[order[0]]) is None
    assert assembler(messages[order[1]]) is None
    assert assembler(messages[order[2]]) == full


def test_map_response_assembler_evicts_stale_incomplete_frames() -> None:
    """Incomplete frames beyond the pending buffer cap are evicted FIFO."""
    assembler = create_map_response_assembler()
    full = base64.b64encode(bytes(range(48)))
    first_part, last_part = full[:32], full[32:]

    for idx in range(5):
        assert (
            assembler(
                _build_map_msg(
                    first_part,
                    RoborockMessageProtocol.MAP_RESPONSE_PART,
                    seq=1,
                    random=idx,
                )
            )
            is None
        )

    # random=0 was evicted when random=4 arrived; sending its trailing 301 fragment
    # buffers random=0 anew (evicting random=1) and returns None rather than joining.
    assert assembler(_build_map_msg(last_part, RoborockMessageProtocol.MAP_RESPONSE, seq=2, random=0)) is None
    # random=2 is still retained in the buffer and completes cleanly.
    assert assembler(_build_map_msg(last_part, RoborockMessageProtocol.MAP_RESPONSE, seq=2, random=2)) == full


@pytest.mark.parametrize(
    "message",
    [
        _build_map_msg(None),
        _build_map_msg(b""),
        _build_map_msg(base64.b64encode(bytes(range(32))), RoborockMessageProtocol.RPC_RESPONSE),
        _build_map_msg(base64.b64encode(bytes(range(32))), version=b"1.0"),
        _build_map_msg(
            base64.b64encode(bytes(range(48)))[:32],
            RoborockMessageProtocol.MAP_RESPONSE_PART,
            version=b"1.0",
        ),
    ],
    ids=["none_payload", "empty_payload", "wrong_protocol", "wrong_version_301", "wrong_version_300"],
)
def test_map_response_assembler_ignores_non_matching_messages(message: RoborockMessage) -> None:
    """Non-B01, non-map, or empty messages are ignored."""
    assembler = create_map_response_assembler()
    assert assembler(message) is None

"""Tests for the v1 protocol message encoding and decoding."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from roborock.containers import RoborockBase, UserData
from roborock.exceptions import RoborockException
from roborock.protocol import Utils
from roborock.protocols.v1_protocol import (
    SecurityData,
    create_map_response_decoder,
    create_mqtt_payload_encoder,
    decode_rpc_response,
    encode_local_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_REQUEST_ID = 44444
TEST_ENDPOINT = "87ItGWdb"
TEST_ENDPOINT_BYTES = TEST_ENDPOINT.encode()
SECURITY_DATA = SecurityData(
    endpoint=TEST_ENDPOINT,
    nonce=b"\x91\xbe\x10\xc9b+\x9d\x8a\xcdH*\x19\xf6\xfe\x81h",
)


@pytest.fixture(autouse=True)
def fixed_time_fixture() -> Generator[None, None, None]:
    """Fixture to freeze time for predictable request IDs."""
    # Freeze time to a specific point so request IDs are predictable
    with freeze_time("2025-01-20T12:00:00"):
        yield


@pytest.fixture(name="test_request_id", autouse=True)
def request_id_fixture() -> Generator[int, None, None]:
    """Fixture to provide a fixed request ID."""
    with patch("roborock.protocols.v1_protocol.get_next_int", return_value=TEST_REQUEST_ID):
        yield TEST_REQUEST_ID


@pytest.mark.parametrize(
    ("command", "params", "expected"),
    [
        (
            RoborockCommand.GET_STATUS,
            None,
            b'{"dps":{"101":"{\\"id\\":44444,\\"method\\":\\"get_status\\",\\"params\\":[]}"},"t":1737374400}',
        )
    ],
)
def test_encode_local_payload(command, params, expected):
    """Test encoding of local payload for V1 commands."""
    message = encode_local_payload(command, params)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.GENERAL_REQUEST
    assert message.payload == expected


@pytest.mark.parametrize(
    ("command", "params", "expected"),
    [
        (
            RoborockCommand.GET_STATUS,
            None,
            b'{"dps":{"101":"{\\"id\\":44444,\\"method\\":\\"get_status\\",\\"params\\":[],\\"security\\":{\\"endpoint\\":\\"87ItGWdb\\",\\"nonce\\":\\"91be10c9622b9d8acd482a19f6fe8168\\"}}"},"t":1737374400}',
        )
    ],
)
def test_encode_mqtt_payload(command, params, expected):
    """Test encoding of local payload for V1 commands."""
    encoder = create_mqtt_payload_encoder(SECURITY_DATA)
    message = encoder(command, params)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.payload == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            b'{"t":1652547161,"dps":{"102":"{\\"id\\":20005,\\"result\\":[{\\"msg_ver\\":2,\\"msg_seq\\":1072,\\"state\\":8,\\"battery\\":100,\\"clean_time\\":1041,\\"clean_area\\":37080000,\\"error_code\\":0,\\"map_present\\":1,\\"in_cleaning\\":0,\\"in_returning\\":0,\\"in_fresh_state\\":1,\\"lab_status\\":1,\\"water_box_status\\":0,\\"fan_power\\":103,\\"dnd_enabled\\":0,\\"map_status\\":3,\\"is_locating\\":0,\\"lock_status\\":0,\\"water_box_mode\\":202,\\"distance_off\\":0,\\"water_box_carriage_status\\":0,\\"mop_forbidden_enable\\":0,\\"unsave_map_reason\\":0,\\"unsave_map_flag\\":0}]}"}}',
            {
                "msg_ver": 2,
                "msg_seq": 1072,
                "state": 8,
                "battery": 100,
                "clean_time": 1041,
                "clean_area": 37080000,
                "error_code": 0,
                "map_present": 1,
                "in_cleaning": 0,
                "in_returning": 0,
                "in_fresh_state": 1,
                "lab_status": 1,
                "water_box_status": 0,
                "fan_power": 103,
                "dnd_enabled": 0,
                "map_status": 3,
                "is_locating": 0,
                "lock_status": 0,
                "water_box_mode": 202,
                "distance_off": 0,
                "water_box_carriage_status": 0,
                "mop_forbidden_enable": 0,
                "unsave_map_reason": 0,
                "unsave_map_flag": 0,
            },
        ),
    ],
)
def test_decode_rpc_response(payload: bytes, expected: RoborockBase) -> None:
    """Test decoding a v1 RPC response protocol message."""
    # The values other than the payload are arbitrary
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.GENERAL_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"1.0",
        random=97431,
        timestamp=1652547161,
    )
    decoded_message = decode_rpc_response(message)
    assert decoded_message == expected


def test_create_map_response_decoder():
    """Test creating and using a map response decoder."""
    test_data = b"some map\n"
    compressed_data = (
        b"\x1f\x8b\x08\x08\xf9\x13\x99h\x00\x03foo\x00+\xce\xcfMU\xc8M,\xe0\x02\x00@\xdb\xc6\x1a\t\x00\x00\x00"
    )

    # Create header: endpoint(8) + padding(8) + request_id(2) + padding(6)
    # request_id = 44508 (0xaddc in little endian)
    header = TEST_ENDPOINT_BYTES + b"\x00" * 8 + b"\xdc\xad" + b"\x00" * 6
    encrypted_data = Utils.encrypt_cbc(compressed_data, SECURITY_DATA.nonce)
    payload = header + encrypted_data

    message = RoborockMessage(
        protocol=RoborockMessageProtocol.MAP_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"1.0",
        random=97431,
        timestamp=1652547161,
    )

    decoder = create_map_response_decoder(SECURITY_DATA)
    result = decoder(message)

    assert result.request_id == 44508
    assert result.data == test_data


def test_create_map_response_decoder_invalid_endpoint():
    """Test map response decoder with invalid endpoint."""
    # Create header with wrong endpoint
    header = b"wrongend" + b"\x00" * 8 + b"\xdc\xad" + b"\x00" * 6
    payload = header + b"encrypted_data"

    message = RoborockMessage(
        protocol=RoborockMessageProtocol.MAP_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"1.0",
        random=97431,
        timestamp=1652547161,
    )

    decoder = create_map_response_decoder(SECURITY_DATA)

    with pytest.raises(RoborockException, match="Invalid V1 map response endpoint"):
        decoder(message)


def test_create_map_response_decoder_invalid_payload():
    """Test map response decoder with invalid payload."""
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.MAP_RESPONSE,
        payload=b"short",  # Too short payload
        seq=12750,
        version=b"1.0",
        random=97431,
        timestamp=1652547161,
    )

    decoder = create_map_response_decoder(SECURITY_DATA)

    with pytest.raises(RoborockException, match="Invalid V1 map response format: missing payload"):
        decoder(message)

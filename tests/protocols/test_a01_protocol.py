"""Tests for A01 protocol encoding and decoding."""

import json
from typing import Any

import pytest

from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import decode_rpc_response, encode_mqtt_payload
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)


def test_encode_mqtt_payload_basic():
    """Test basic MQTT payload encoding."""
    # Test data with proper protocol keys
    data: dict[RoborockDyadDataProtocol | RoborockZeoProtocol, Any] = {
        RoborockDyadDataProtocol.START: {"test": "data", "number": 42}
    }

    result = encode_mqtt_payload(data)

    # Verify result is a RoborockMessage
    assert isinstance(result, RoborockMessage)
    assert result.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert result.version == b"A01"
    assert result.payload is not None
    assert isinstance(result.payload, bytes)
    assert len(result.payload) % 16 == 0  # Should be padded to AES block size

    # Decode the payload to verify structure
    decoded_data = decode_rpc_response(result)
    assert decoded_data == {200: {"test": "data", "number": 42}}


def test_encode_mqtt_payload_empty_data():
    """Test encoding with empty data."""
    data: dict[RoborockDyadDataProtocol | RoborockZeoProtocol, Any] = {}

    result = encode_mqtt_payload(data)

    assert isinstance(result, RoborockMessage)
    assert result.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert result.payload is not None

    # Decode the payload to verify structure
    decoded_data = decode_rpc_response(result)
    assert decoded_data == {}


def test_encode_mqtt_payload_complex_data():
    """Test encoding with complex nested data."""
    data: dict[RoborockDyadDataProtocol | RoborockZeoProtocol, Any] = {
        RoborockDyadDataProtocol.STATUS: {
            "nested": {"deep": {"value": 123}},
            "list": [1, 2, 3, "test"],
            "boolean": True,
            "null": None,
        },
        RoborockZeoProtocol.MODE: "simple_value",
    }

    result = encode_mqtt_payload(data)

    assert isinstance(result, RoborockMessage)
    assert result.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert result.payload is not None
    assert isinstance(result.payload, bytes)

    # Decode the payload to verify structure
    decoded_data = decode_rpc_response(result)
    assert decoded_data == {
        201: {
            "nested": {"deep": {"value": 123}},
            "list": [1, 2, 3, "test"],
            "boolean": True,
            "null": None,
        },
        204: "simple_value",
    }


def test_decode_rpc_response_valid_message():
    """Test decoding a valid RPC response."""
    # Create a valid padded JSON payload
    payload_data = {"dps": {"1": {"key": "value"}, "2": 42, "10": ["list", "data"]}}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size (16 bytes)
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    result = decode_rpc_response(message)

    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result
    assert 10 in result
    assert result[1] == {"key": "value"}
    assert result[2] == 42
    assert result[10] == ["list", "data"]


def test_decode_rpc_response_string_keys():
    """Test decoding with string keys that can be converted to integers."""
    payload_data = {"dps": {"1": "first", "100": "hundred", "999": {"nested": "data"}}}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    result = decode_rpc_response(message)

    assert result[1] == "first"
    assert result[100] == "hundred"
    assert result[999] == {"nested": "data"}


def test_decode_rpc_response_missing_payload():
    """Test decoding fails when payload is missing."""
    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=None)

    with pytest.raises(RoborockException, match="Invalid A01 message format: missing payload"):
        decode_rpc_response(message)


def test_decode_rpc_response_invalid_padding():
    """Test decoding fails with invalid padding."""
    # Create invalid padded data
    invalid_payload = b"invalid padding data"

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=invalid_payload)

    with pytest.raises(RoborockException, match="Unable to unpad A01 payload"):
        decode_rpc_response(message)


def test_decode_rpc_response_invalid_json():
    """Test decoding fails with invalid JSON after unpadding."""
    # Create properly padded but invalid JSON
    invalid_json = b"invalid json data"
    padding_length = 16 - (len(invalid_json) % 16)
    padded_payload = invalid_json + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    with pytest.raises(RoborockException, match="Invalid A01 message payload"):
        decode_rpc_response(message)


def test_decode_rpc_response_missing_dps():
    """Test decoding with missing 'dps' key returns empty dict."""
    payload_data = {"other_key": "value"}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    result = decode_rpc_response(message)
    assert result == {}


def test_decode_rpc_response_dps_not_dict():
    """Test decoding fails when 'dps' is not a dictionary."""
    payload_data = {"dps": "not_a_dict"}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    with pytest.raises(RoborockException, match=r"Invalid A01 message format.*'dps' should be a dictionary"):
        decode_rpc_response(message)


def test_decode_rpc_response_invalid_key():
    """Test decoding fails when dps contains non-integer keys."""
    payload_data = {"dps": {"1": "valid", "not_a_number": "invalid"}}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    with pytest.raises(RoborockException, match=r"Invalid A01 message format:.*'dps' key should be an integer"):
        decode_rpc_response(message)


def test_decode_rpc_response_empty_dps():
    """Test decoding with empty dps dictionary."""
    payload_data: dict[str, Any] = {"dps": {}}
    json_payload = json.dumps(payload_data).encode("utf-8")

    # Pad to AES block size
    padding_length = 16 - (len(json_payload) % 16)
    padded_payload = json_payload + bytes([padding_length] * padding_length)

    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=padded_payload)

    result = decode_rpc_response(message)

    assert result == {}

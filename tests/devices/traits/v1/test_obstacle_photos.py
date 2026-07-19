"""Tests for the ObstaclePhotoTrait."""

import gzip
from unittest.mock import AsyncMock

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.obstacle_photos import (
    ObstaclePhotoTrait,
    parse_photo_data,
)
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import SecurityData, create_blob_response_decoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand

PNG_BYTES = b"\x89PNG\r\n\x1a\nphoto-bytes"
JPEG_BYTES = b"\xff\xd8\xff\xe0photo-bytes"


def _block(block_type: int, payload: bytes, header_size: int = 8) -> bytes:
    return (
        block_type.to_bytes(2, "little")
        + header_size.to_bytes(2, "little")
        + len(payload).to_bytes(4, "little")
        + b"\0" * (header_size - 8)
        + payload
    )


@pytest.fixture
def obstacle_photo_trait(device: RoborockDevice, mock_blob_rpc_channel: AsyncMock) -> ObstaclePhotoTrait:
    """Create an ObstaclePhotoTrait instance with mocked dependencies."""
    assert device.v1_properties
    trait = ObstaclePhotoTrait(
        device.v1_properties.status.rpc_channel,
        SecurityData(endpoint="endpoint", nonce=b"1234567890abcdef"),
    )
    trait._rpc_channel = mock_blob_rpc_channel
    return trait


def test_parse_photo_data() -> None:
    """Test parsing photo bytes from the get_photo typed payload."""
    assert parse_photo_data(_block(1, b"\x10\x00\x10\x00") + _block(3, PNG_BYTES)) == PNG_BYTES


def test_parse_photo_data_jpeg() -> None:
    """Test parsing JPEG photo bytes from the get_photo typed payload."""
    assert parse_photo_data(_block(1, b"\x80\x02\xe0\x01") + _block(3, JPEG_BYTES)) == JPEG_BYTES


def test_parse_photo_data_with_extended_header() -> None:
    """Test parsing a photo block whose header is larger than the minimum."""
    assert parse_photo_data(_block(3, PNG_BYTES, header_size=12)) == PNG_BYTES


def test_parse_photo_data_missing_photo() -> None:
    """Test missing photo data block raises."""
    with pytest.raises(RoborockException):
        parse_photo_data(_block(1, b"\x10\x00\x10\x00"))


def test_decode_blob_response() -> None:
    """Test decoding the gzip blob frame used by obstacle photos."""
    request_id = 20008
    decompressed = _block(3, JPEG_BYTES)
    compressed = gzip.compress(decompressed)
    header_size = 56
    payload = bytearray(header_size + len(compressed))
    payload[:8] = b"ROBOROCK"
    payload[8:12] = request_id.to_bytes(4, "little")
    payload[16:18] = header_size.to_bytes(2, "little")
    payload[20:24] = len(compressed).to_bytes(4, "little")
    payload[header_size:] = compressed

    response = create_blob_response_decoder()(
        RoborockMessage(protocol=RoborockMessageProtocol.MAP_RESPONSE, payload=bytes(payload))
    )

    assert response is not None
    assert response.request_id == request_id
    assert response.data == decompressed


def test_obstacle_photo_trait_metadata() -> None:
    """Test obstacle photos use the blob RPC channel when discovered."""
    assert ObstaclePhotoTrait.blob_rpc_channel is True
    assert ObstaclePhotoTrait.requires_feature == "is_ai_recognition_obstacle_supported"


async def test_get_enabled(obstacle_photo_trait: ObstaclePhotoTrait, mock_rpc_channel: AsyncMock) -> None:
    """Test reading the app's map-object photo enabled bit from camera status."""
    mock_rpc_channel.send_command.return_value = [1 << 10]

    assert await obstacle_photo_trait.get_enabled() is True
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CAMERA_STATUS)


async def test_get_photo(
    obstacle_photo_trait: ObstaclePhotoTrait,
    mock_blob_rpc_channel: AsyncMock,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test fetching and parsing obstacle photo content."""
    mock_rpc_channel.send_command.return_value = {"pub_key": {"n": "abc", "e": "010001"}}
    mock_blob_rpc_channel.send_command.return_value = _block(3, PNG_BYTES)

    photo = await obstacle_photo_trait.get_photo("photo-id")

    assert photo.photo_id == "photo-id"
    assert photo.image_content == PNG_BYTES
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_RANDOM_PKEY)
    mock_blob_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.GET_PHOTO,
        params={
            "security": {
                "pub_key": {"n": "abc", "e": "010001"},
                "cipher_suite": 0,
            },
            "endpoint": "endpoint",
            "nonce": "31323334353637383930616263646566",
            "data_filter": {"img_id": "photo-id", "type": 1},
        },
    )

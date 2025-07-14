"""Tests for the Roborock Local Client V1."""

import json
from collections.abc import AsyncGenerator
from queue import Queue
from typing import Any
from unittest.mock import patch

import pytest

from roborock.containers import RoomMapping
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.version_1_apis import RoborockLocalClientV1

from .mock_data import LOCAL_KEY


def build_rpc_response(seq: int, message: dict[str, Any]) -> bytes:
    """Build an encoded RPC response message."""
    return build_raw_response(
        protocol=RoborockMessageProtocol.GENERAL_REQUEST,
        seq=seq,
        payload=json.dumps(
            {
                "dps": {102: json.dumps(message)},
            }
        ).encode(),
    )


def build_raw_response(protocol: RoborockMessageProtocol, seq: int, payload: bytes) -> bytes:
    """Build an encoded RPC response message."""
    message = RoborockMessage(
        protocol=protocol,
        random=23,
        seq=seq,
        payload=payload,
    )
    return MessageParser.build(message, local_key=LOCAL_KEY)


async def test_async_connect(
    local_client: RoborockLocalClientV1,
    received_requests: Queue,
    response_queue: Queue,
):
    """Test that we can connect to the Roborock device."""
    response_queue.put(build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, b"ignored"))
    response_queue.put(build_raw_response(RoborockMessageProtocol.PING_RESPONSE, 2, b"ignored"))

    await local_client.async_connect()
    assert local_client.is_connected()
    assert received_requests.qsize() == 2

    await local_client.async_disconnect()
    assert not local_client.is_connected()


@pytest.fixture(name="connected_local_client")
async def connected_local_client_fixture(
    response_queue: Queue,
    local_client: RoborockLocalClientV1,
) -> AsyncGenerator[RoborockLocalClientV1, None]:
    response_queue.put(build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, b"ignored"))
    response_queue.put(build_raw_response(RoborockMessageProtocol.PING_RESPONSE, 2, b"ignored"))
    await local_client.async_connect()
    yield local_client


async def test_get_room_mapping(
    received_requests: Queue,
    response_queue: Queue,
    connected_local_client: RoborockLocalClientV1,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    test_request_id = 5050

    message = build_rpc_response(
        seq=test_request_id,
        message={
            "id": test_request_id,
            "result": [[16, "2362048"], [17, "2362044"]],
        },
    )
    response_queue.put(message)

    with patch("roborock.protocols.v1_protocol.get_next_int", return_value=test_request_id):
        room_mapping = await connected_local_client.get_room_mapping()

    assert room_mapping == [
        RoomMapping(segment_id=16, iot_id="2362048"),
        RoomMapping(segment_id=17, iot_id="2362044"),
    ]

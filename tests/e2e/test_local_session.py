"""End-to-end tests for LocalChannel using fake sockets."""

import asyncio
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import Mock, patch

import pytest

from roborock.devices.local_channel import LocalChannel
from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.conftest import RequestHandler
from tests.mock_data import LOCAL_KEY

TEST_HOST = "192.168.1.100"
TEST_DEVICE_UID = "test_device_uid"
TEST_CONNECT_NONCE = 12345
TEST_ACK_NONCE = 67890
TEST_RANDOM = 13579


@pytest.fixture(name="mock_create_local_connection")
def create_local_connection_fixture(request_handler: RequestHandler) -> Generator[None, None, None]:
    """Fixture that overrides the transport creation to wire it up to the mock socket."""

    async def create_connection(protocol_factory: Callable[[], asyncio.Protocol], *args, **kwargs) -> tuple[Any, Any]:
        protocol = protocol_factory()

        def handle_write(data: bytes) -> None:
            response = request_handler(data)
            if response is not None:
                # Call data_received directly to avoid loop scheduling issues in test
                protocol.data_received(response)

        closed = asyncio.Event()

        mock_transport = Mock()
        mock_transport.write = handle_write
        mock_transport.close = closed.set
        mock_transport.is_reading = lambda: not closed.is_set()

        return (mock_transport, protocol)

    with patch("roborock.devices.local_channel.asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.create_connection.side_effect = create_connection
        yield


@pytest.fixture(name="local_channel")
async def local_channel_fixture(mock_create_local_connection: None) -> AsyncGenerator[LocalChannel, None]:
    with patch(
        "roborock.devices.local_channel.get_next_int", return_value=TEST_CONNECT_NONCE, device_uid=TEST_DEVICE_UID
    ):
        channel = LocalChannel(host=TEST_HOST, local_key=LOCAL_KEY, device_uid=TEST_DEVICE_UID)
        yield channel
        channel.close()


def build_response(
    protocol: RoborockMessageProtocol,
    seq: int,
    payload: bytes,
    random: int,
) -> bytes:
    """Build an encoded response message."""
    if protocol == RoborockMessageProtocol.HELLO_RESPONSE:
        encoder = create_local_encoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=None)
    else:
        encoder = create_local_encoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=TEST_ACK_NONCE)

    msg = RoborockMessage(
        protocol=protocol,
        random=random,
        seq=seq,
        payload=payload,
    )
    return encoder(msg)


async def test_connect(
    local_channel: LocalChannel, response_queue: Queue[bytes], received_requests: Queue[bytes]
) -> None:
    """Test connecting to the device."""
    # Queue HELLO response with payload to ensure it can be parsed
    response_queue.put(build_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok", random=TEST_RANDOM))

    await local_channel.connect()

    assert local_channel.is_connected
    assert received_requests.qsize() == 1

    # Verify HELLO request
    request_bytes = received_requests.get()
    # Note: We cannot use create_local_decoder here because HELLO_REQUEST has payload=None
    # which causes MessageParser to fail parsing. For now we verify the raw bytes.

    # Protocol is at offset 19 (2 bytes)
    # Prefix(4) + Version(3) + Seq(4) + Random(4) + Timestamp(4) = 19
    assert len(request_bytes) >= 21
    protocol_bytes = request_bytes[19:21]
    assert int.from_bytes(protocol_bytes, "big") == RoborockMessageProtocol.HELLO_REQUEST


async def test_send_command(
    local_channel: LocalChannel, response_queue: Queue[bytes], received_requests: Queue[bytes]
) -> None:
    """Test sending a command."""
    # Queue HELLO response
    response_queue.put(build_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok", random=TEST_RANDOM))

    await local_channel.connect()

    # Clear requests from handshake
    while not received_requests.empty():
        received_requests.get()

    # Send command
    cmd_seq = 123
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        seq=cmd_seq,
        payload=b'{"method":"get_status"}',
    )

    await local_channel.publish(msg)

    # Verify request
    assert received_requests.qsize() == 1
    request_bytes = received_requests.get()

    # Decode request
    decoder = create_local_decoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=TEST_ACK_NONCE)
    msgs = list(decoder(request_bytes))
    assert len(msgs) == 1
    assert msgs[0].protocol == RoborockMessageProtocol.RPC_REQUEST
    assert msgs[0].payload == b'{"method":"get_status"}'

"""End-to-end tests for LocalChannel using fake sockets."""

import asyncio
from collections.abc import AsyncGenerator, Generator, Callable
from unittest.mock import patch, Mock
from typing import Any

import pytest
import syrupy

from roborock.devices.local_channel import LocalChannel
from roborock.protocol import MessageParser, create_local_decoder
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.logging import CapturedRequestLog
from tests.fixtures.mqtt import Subscriber
from tests.fixtures.local_async_fixtures import AsyncLocalRequestHandler
from tests.mock_data import LOCAL_KEY

TEST_HOST = "192.168.1.100"
TEST_DEVICE_UID = "test_device_uid"
TEST_RANDOM = 23


@pytest.fixture(name="mock_create_local_connection")
def create_local_connection_fixture(
    local_async_request_handler: AsyncLocalRequestHandler, log: CapturedRequestLog
) -> Generator[None, None, None]:
    """Fixture that overrides the transport creation to wire it up to the mock socket."""

    async def create_connection(protocol_factory: Callable[[], asyncio.Protocol], *args, **kwargs) -> tuple[Any, Any]:
        protocol = protocol_factory()

        async def handle_write(data: bytes) -> None:
            log.add_log_entry("[local >]", data)
            response = await local_async_request_handler(data)
            if response is not None:
                log.add_log_entry("[local <]", response)
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
    channel = LocalChannel(host=TEST_HOST, local_key=LOCAL_KEY, device_uid=TEST_DEVICE_UID)
    yield channel
    channel.close()


def build_raw_response(
    protocol: RoborockMessageProtocol,
    seq: int,
    payload: bytes,
    version: LocalProtocolVersion = LocalProtocolVersion.V1,
    connect_nonce: int | None = None,
    ack_nonce: int | None = None,
) -> bytes:
    """Build an encoded response message."""
    message = RoborockMessage(
        protocol=protocol,
        random=23,
        seq=seq,
        payload=payload,
        version=version.value.encode(),
    )
    return MessageParser.build(message, local_key=LOCAL_KEY, connect_nonce=connect_nonce, ack_nonce=ack_nonce)


async def test_connect(
    local_channel: LocalChannel,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test connecting to the device."""
    # Queue HELLO response with payload to ensure it can be parsed
    local_response_queue.put_nowait(
        build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok")
    )

    await local_channel.connect()

    assert local_channel.is_connected
    assert local_received_requests.qsize() == 1

    # Verify HELLO request
    request_bytes = await local_received_requests.get()
    # Note: We cannot use create_local_decoder here because HELLO_REQUEST has payload=None
    # which causes MessageParser to fail parsing. For now we verify the raw bytes.

    # Protocol is at offset 19 (2 bytes)
    # Prefix(4) + Version(3) + Seq(4) + Random(4) + Timestamp(4) = 19
    assert len(request_bytes) >= 21
    protocol_bytes = request_bytes[19:21]
    assert int.from_bytes(protocol_bytes, "big") == RoborockMessageProtocol.HELLO_REQUEST

    assert snapshot == log


async def test_send_command(
    local_channel: LocalChannel,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test sending a command."""
    # Queue HELLO response
    local_response_queue.put_nowait(
        build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok")
    )

    await local_channel.connect()

    # Clear requests from handshake
    while not local_received_requests.empty():
        await local_received_requests.get()

    # Send command
    cmd_seq = 123
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        seq=cmd_seq,
        payload=b'{"method":"get_status"}',
    )
    # Prepare a fake response to the command.
    response_queue.put(build_raw_response(RoborockMessageProtocol.RPC_RESPONSE, cmd_seq, payload=b'{"status": "ok"}'))

    subscriber = Subscriber()
    unsub = await local_channel.subscribe(subscriber.append)

    await local_channel.publish(msg)

    # Verify request received by the server
    request_bytes = await local_received_requests.get()
    assert local_received_requests.empty()

    # Decode request
    decoder = create_local_decoder(local_key=LOCAL_KEY)
    msgs = list(decoder(request_bytes))
    assert len(msgs) == 1
    assert msgs[0].protocol == RoborockMessageProtocol.RPC_REQUEST
    assert msgs[0].payload == b'{"method":"get_status"}'
    assert msgs[0].version == LocalProtocolVersion.V1.value.encode()

    # Verify response received by subscriber
    await subscriber.wait()
    assert len(subscriber.messages) == 1
    response_message = subscriber.messages[0]
    assert isinstance(response_message, RoborockMessage)
    assert response_message.protocol == RoborockMessageProtocol.RPC_RESPONSE
    assert response_message.payload == b'{"status": "ok"}'

    unsub()

    assert snapshot == log


async def test_l01_session(
    local_channel: LocalChannel,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test connecting to a device that speaks the L01 protocol.
    
    Note that this test currently has a delay because the actual local client
    will delay before retrying with L01 after a failed 1.0 attempt. This should
    also be improved in the actual client itself, but likely requires a closer
    look at the actual device response in that scenario or moving to a serial
    request/response behavior rather than publish/subscribe.
    """
    # Client first attempts 1.0 and we reply with a fake invalid response. The
    # response is arbitrary, and this could be improved by capturing a real L01
    # device response to a 1.0 message.
    local_response_queue.put_nowait(b"\x00")
    # The client attempts L01 protocol as a followup. The connect nonce uses
    # a deterministic number from deterministic_message_fixtures.
    connect_nonce = 9090
    local_response_queue.put_nowait(
        build_raw_response(
            RoborockMessageProtocol.HELLO_RESPONSE,
            1,
            payload=b"ok",
            version=LocalProtocolVersion.L01,
            connect_nonce=connect_nonce,
            ack_nonce=None,
        )
    )

    await local_channel.connect()

    assert local_channel.is_connected

    # Verify 1.0 HELLO request
    request_bytes = local_received_requests.get()
    # Protocol is at offset 19 (2 bytes)
    # Prefix(4) + Version(3) + Seq(4) + Random(4) + Timestamp(4) = 19
    assert len(request_bytes) >= 21
    protocol_bytes = request_bytes[19:21]
    assert int.from_bytes(protocol_bytes, "big") == RoborockMessageProtocol.HELLO_REQUEST

    # Verify L01 HELLO request
    request_bytes = local_received_requests.get()
    # Protocol is at offset 19 (2 bytes)
    # Prefix(4) + Version(3) + Seq(4) + Random(4) + Timestamp(4) = 19
    assert len(request_bytes) >= 21
    protocol_bytes = request_bytes[19:21]
    assert int.from_bytes(protocol_bytes, "big") == RoborockMessageProtocol.HELLO_REQUEST

    assert local_received_requests.empty()

    # Verify the channel switched to L01 protocol
    assert local_channel.protocol_version == LocalProtocolVersion.L01.value

    # We have established a connection. Now send some messages.
    # Publish an L01 command. Currently the caller of the local channel needs to
    # determine the protocol version to use, but this could be pushed inside of
    # the channel in the future.
    cmd_seq = 123
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        seq=cmd_seq,
        payload=b'{"method":"get_status"}',
        version=b"L01",
    )
    # Prepare a fake response to the command.
    local_response_queue.put_nowait(
        build_raw_response(
            RoborockMessageProtocol.RPC_RESPONSE,
            cmd_seq,
            payload=b'{"status": "ok"}',
            version=LocalProtocolVersion.L01,
            connect_nonce=connect_nonce,
            ack_nonce=TEST_RANDOM,
        )
    )

    # Set up a subscriber to listen for the response then publish the message.
    subscriber = Subscriber()
    unsub = await local_channel.subscribe(subscriber.append)
    await local_channel.publish(msg)

    # Verify request received by the server
    request_bytes = await local_received_requests.get()
    decoder = create_local_decoder(local_key=LOCAL_KEY, connect_nonce=connect_nonce, ack_nonce=TEST_RANDOM)
    msgs = list(decoder(request_bytes))
    assert len(msgs) == 1
    assert msgs[0].protocol == RoborockMessageProtocol.RPC_REQUEST
    assert msgs[0].payload == b'{"method":"get_status"}'
    assert msgs[0].version == LocalProtocolVersion.L01.value.encode()

    # Verify fake response published by the server, received by subscriber
    await subscriber.wait()
    assert len(subscriber.messages) == 1
    response_message = subscriber.messages[0]
    assert isinstance(response_message, RoborockMessage)
    assert response_message.protocol == RoborockMessageProtocol.RPC_RESPONSE
    assert response_message.payload == b'{"status": "ok"}'
    assert response_message.version == LocalProtocolVersion.L01.value.encode()

    unsub()

    assert snapshot == log

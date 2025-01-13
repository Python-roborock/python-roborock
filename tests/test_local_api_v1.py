"""Tests for the Roborock Local Client V1."""

from queue import Queue

from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.version_1_apis import RoborockLocalClientV1

from .mock_data import LOCAL_KEY


def build_rpc_response(protocol: RoborockMessageProtocol, seq: int) -> bytes:
    """Build an encoded RPC response message."""
    message = RoborockMessage(
        protocol=protocol,
        random=23,
        seq=seq,
        payload=b"ignored",
    )
    return MessageParser.build(message, local_key=LOCAL_KEY)


async def test_async_connect(
    local_client: RoborockLocalClientV1,
    received_requests: Queue,
    response_queue: Queue,
):
    """Test that we can connect to the Roborock device."""
    response_queue.put(build_rpc_response(RoborockMessageProtocol.HELLO_RESPONSE, 1))
    response_queue.put(build_rpc_response(RoborockMessageProtocol.PING_RESPONSE, 2))

    await local_client.async_connect()
    assert local_client.is_connected()
    assert received_requests.qsize() == 2

    await local_client.async_disconnect()
    assert not local_client.is_connected()

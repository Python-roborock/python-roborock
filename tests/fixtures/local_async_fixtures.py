import asyncio
import logging
import warnings
from collections.abc import Awaitable, Callable, Generator
from typing import Any
from unittest.mock import Mock, patch

import pytest

from .logging import CapturedRequestLog

_LOGGER = logging.getLogger(__name__)

AsyncLocalRequestHandler = Callable[[bytes], Awaitable[bytes | None]]


@pytest.fixture(name="local_received_requests")
def received_requests_fixture() -> asyncio.Queue[bytes]:
    """Fixture that provides access to the received requests."""
    return asyncio.Queue()


@pytest.fixture(name="local_response_queue")
def response_queue_fixture() -> Generator[asyncio.Queue[bytes], None, None]:
    """Fixture that provides a queue of responses to be sent to the client."""
    response_queue: asyncio.Queue[bytes] = asyncio.Queue()
    yield response_queue
    if not response_queue.empty():
        warnings.warn("Some enqueued local device responses were not consumed during the test")


@pytest.fixture(name="local_async_request_handler")
def local_request_handler_fixture(
    local_received_requests: asyncio.Queue[bytes], local_response_queue: asyncio.Queue[bytes]
) -> AsyncLocalRequestHandler:
    """Fixture records incoming requests and replies with responses from the queue."""

    async def handle_request(client_request: bytes) -> bytes | None:
        """Handle an incoming request from the client."""
        local_received_requests.put_nowait(client_request)

        # Insert a prepared response into the response buffer
        if not local_response_queue.empty():
            return await local_response_queue.get()
        return None

    return handle_request


@pytest.fixture(name="mock_async_create_local_connection")
def create_local_connection_fixture(
    local_async_request_handler: AsyncLocalRequestHandler,
    log: CapturedRequestLog,
) -> Generator[None, None, None]:
    """Fixture that overrides the transport creation to wire it up to the mock socket."""

    tasks = []

    async def create_connection(protocol_factory: Callable[[], asyncio.Protocol], *args, **kwargs) -> tuple[Any, Any]:
        protocol = protocol_factory()

        async def handle_write(data: bytes) -> None:
            log.add_log_entry("[local >]", data)
            response = await local_async_request_handler(data)
            if response is not None:
                # Call data_received directly to avoid loop scheduling issues in test
                log.add_log_entry("[local <]", response)
                protocol.data_received(response)

        def start_handle_write(data: bytes) -> None:
            tasks.append(asyncio.create_task(handle_write(data)))

        closed = asyncio.Event()

        mock_transport = Mock()
        mock_transport.write = start_handle_write
        mock_transport.close = closed.set
        mock_transport.is_reading = lambda: not closed.is_set()

        return (mock_transport, protocol)

    with patch("roborock.devices.local_channel.asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.create_connection.side_effect = create_connection
        yield

        for task in tasks:
            task.cancel()

import asyncio
import logging

import pytest

from roborock.exceptions import VacuumError
from roborock.roborock_future import RequestKey, RoborockFuture, WaitingQueue
from roborock.roborock_message import RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)
TIMEOUT = 5


async def test_can_create() -> None:
    RoborockFuture()


async def test_set_result() -> None:
    rq = RoborockFuture()
    rq.set_result("test")
    assert await rq.async_get(1) == "test"


async def test_set_exception() -> None:
    rq = RoborockFuture()
    rq.set_exception(VacuumError("test"))
    with pytest.raises(VacuumError):
        assert await rq.async_get(1)


async def test_get_timeout() -> None:
    rq = RoborockFuture()
    with pytest.raises(asyncio.TimeoutError):
        await rq.async_get(0.01)


@pytest.mark.parametrize(
    "key",
    [
        RequestKey(1),
        RequestKey(1, RoborockMessageProtocol.RPC_RESPONSE),
    ],
)
async def test_queue_result_in_thread(key: RequestKey) -> None:
    queue = WaitingQueue()

    future = RoborockFuture()
    queue.put(key, future)

    def set_result_in_thread():
        fut = queue.safe_pop(key)
        assert fut is not None
        fut.set_result("value1")

    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, set_result_in_thread)
    await task

    assert await future.async_get(TIMEOUT) == "value1"


@pytest.mark.parametrize(
    "key",
    [
        RequestKey(1),
        RequestKey(1, RoborockMessageProtocol.RPC_RESPONSE),
    ],
)
async def test_queue_set_exception_in_thread(key: RequestKey) -> None:
    queue = WaitingQueue()

    future = RoborockFuture()
    queue.put(key, future)

    def set_result_in_thread():
        fut = queue.safe_pop(key)
        assert fut is not None
        fut.set_exception(VacuumError("value1"))

    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, set_result_in_thread)
    await task

    with pytest.raises(VacuumError, match="value1"):
        await future.async_get(TIMEOUT)


@pytest.mark.parametrize(
    "key",
    [
        RequestKey(1),
        RequestKey(1, RoborockMessageProtocol.RPC_RESPONSE),
    ],
)
async def test_queue_item_not_found(key: RequestKey) -> None:
    queue = WaitingQueue()
    assert queue.safe_pop(key) is None


@pytest.mark.parametrize(
    "key",
    [
        RequestKey(1),
        RequestKey(1, RoborockMessageProtocol.RPC_RESPONSE),
    ],
)
async def test_queue_duplicate_item_fails(key: RequestKey) -> None:
    queue = WaitingQueue()
    future1 = RoborockFuture()
    queue.put(key, future1)

    future2 = RoborockFuture()
    with pytest.raises(ValueError):
        queue.put(key, future2)


async def test_unique_protocol() -> None:
    queue = WaitingQueue()
    future1 = RoborockFuture()
    queue.put(RequestKey(1, RoborockMessageProtocol.RPC_RESPONSE), future1)

    future2 = RoborockFuture()
    queue.put(RequestKey(1, RoborockMessageProtocol.GENERAL_RESPONSE), future2)

import asyncio

import pytest

from roborock.exceptions import VacuumError
from roborock.roborock_future import RoborockFuture


async def test_can_create():
    RoborockFuture(1)


@pytest.mark.asyncio
async def test_set_result():
    rq = RoborockFuture(1)
    rq.set_result("test")
    assert await rq.async_get(1) == "test"


@pytest.mark.asyncio
async def test_set_exception():
    rq = RoborockFuture(1)
    rq.set_exception(VacuumError("test"))
    with pytest.raises(VacuumError):
        assert await rq.async_get(1)


@pytest.mark.asyncio
async def test_get_timeout():
    rq = RoborockFuture(1)
    with pytest.raises(asyncio.TimeoutError):
        await rq.async_get(0.01)

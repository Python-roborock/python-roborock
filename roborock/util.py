from __future__ import annotations

import asyncio
import datetime
import logging
import math
import time
from asyncio import TimerHandle
from collections.abc import Callable, Coroutine, MutableMapping
from typing import Any, TypeVar

from roborock import RoborockException

T = TypeVar("T")
DEFAULT_TIME_ZONE: datetime.tzinfo | None = datetime.datetime.now().astimezone().tzinfo


def unpack_list(value: list[T], size: int) -> list[T | None]:
    return (value + [None] * size)[:size]  # type: ignore


def parse_datetime_to_roborock_datetime(
    start_datetime: datetime.datetime, end_datetime: datetime.datetime
) -> tuple[datetime.datetime, datetime.datetime]:
    now = datetime.datetime.now(DEFAULT_TIME_ZONE)
    start_datetime = start_datetime.replace(
        year=now.year, month=now.month, day=now.day, second=0, microsecond=0, tzinfo=DEFAULT_TIME_ZONE
    )
    end_datetime = end_datetime.replace(
        year=now.year, month=now.month, day=now.day, second=0, microsecond=0, tzinfo=DEFAULT_TIME_ZONE
    )
    if start_datetime > end_datetime:
        end_datetime += datetime.timedelta(days=1)
    elif end_datetime < now:
        start_datetime += datetime.timedelta(days=1)
        end_datetime += datetime.timedelta(days=1)

    return start_datetime, end_datetime


def parse_time_to_datetime(
    start_time: datetime.time, end_time: datetime.time
) -> tuple[datetime.datetime, datetime.datetime]:
    """Help to handle time data."""
    start_datetime = datetime.datetime.now(DEFAULT_TIME_ZONE).replace(
        hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0
    )
    end_datetime = datetime.datetime.now(DEFAULT_TIME_ZONE).replace(
        hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0
    )

    return parse_datetime_to_roborock_datetime(start_datetime, end_datetime)


class RepeatableTask:
    def __init__(self, callback: Callable[[], Coroutine], interval: int):
        self.callback = callback
        self.interval = interval
        self._task: TimerHandle | None = None

    async def _run_task(self):
        response = None
        try:
            response = await self.callback()
        except RoborockException:
            pass
        loop = asyncio.get_running_loop()
        self._task = loop.call_later(self.interval, self._run_task_soon)
        return response

    def _run_task_soon(self):
        asyncio.create_task(self._run_task())

    def cancel(self):
        if self._task:
            self._task.cancel()

    async def reset(self):
        self.cancel()
        return await self._run_task()


class RoborockLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix: str, logger: logging.Logger) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        return f"[{self.prefix}] {msg}", kwargs


counter_map: dict[tuple[int, int], int] = {}


def get_next_int(min_val: int, max_val: int) -> int:
    """Gets a random int in the range, precached to help keep it fast."""
    if (min_val, max_val) not in counter_map:
        # If we have never seen this range, or if the cache is getting low, make a bunch of preshuffled values.
        counter_map[(min_val, max_val)] = min_val
    counter_map[(min_val, max_val)] += 1
    return counter_map[(min_val, max_val)] % max_val + min_val


def get_timestamp() -> int:
    """Get the current timestamp in seconds since epoch.

    This is separated out to allow for easier mocking in tests.
    """
    return math.floor(time.time())

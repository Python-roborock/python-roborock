from __future__ import annotations

import logging
import math
import time
from collections.abc import MutableMapping
from typing import Any, TypeVar

from roborock.diagnostics import redact_device_uid

T = TypeVar("T")


def unpack_list(value: list[T], size: int) -> list[T | None]:
    return (value + [None] * size)[:size]  # type: ignore


class RoborockLoggerAdapter(logging.LoggerAdapter):
    def __init__(
        self,
        duid: str | None = None,
        name: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(logger or logging.getLogger(__name__), {})
        if name is not None:
            self.prefix = name
        elif duid is not None:
            self.prefix = redact_device_uid(duid)
        else:
            raise ValueError("Either duid or name must be provided")

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

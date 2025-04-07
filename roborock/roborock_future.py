from __future__ import annotations

import logging
from asyncio import Future
from dataclasses import dataclass
from threading import Lock
from typing import Any

import async_timeout

from .exceptions import VacuumError
from .roborock_message import RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestKey:
    """A key for a Roborock message request."""

    request_id: int
    protocol: RoborockMessageProtocol | int = 0

    def __str__(self) -> str:
        """Get the key for the request."""
        return f"{self.request_id}-{self.protocol}"


class WaitingQueue:
    """A threadsafe waiting queue for Roborock messages."""

    def __init__(self) -> None:
        """Initialize the waiting queue."""
        self._lock = Lock()
        self._queue: dict[RequestKey, RoborockFuture] = {}

    def put(self, request_key: RequestKey, future: RoborockFuture) -> None:
        """Create a future for the given protocol."""
        _LOGGER.debug("Putting request key %s in the queue", request_key)
        with self._lock:
            if request_key in self._queue:
                raise ValueError(f"Request key {request_key} already exists in the queue")
            self._queue[request_key] = future

    def safe_pop(self, request_key: RequestKey, label: str | None = None) -> RoborockFuture | None:
        """Get the future from the queue if it has not yet been popped, otherwise ignore.

        The label is used for logging when the request key is not found in the queue.
        """
        _LOGGER.debug("Popping request key %s (%s) from the queue", request_key, label)
        with self._lock:
            future = self._queue.pop(request_key, None)
            if future is None and label is not None:
                _LOGGER.warning("Received message for key %s (%s) not found in the queue", request_key, label)
            return future


class RoborockFuture:
    """A threadsafe asyncio Future for Roborock messages.

    The results may be set from a background thread. The future
    must be awaited in an asyncio event loop.
    """

    def __init__(self):
        """Initialize the Roborock future."""
        self.fut: Future = Future()
        self.loop = self.fut.get_loop()

    def _set_result(self, item: Any) -> None:
        if not self.fut.cancelled():
            self.fut.set_result(item)

    def set_result(self, item: Any) -> None:
        self.loop.call_soon_threadsafe(self._set_result, item)

    def _set_exception(self, exc: VacuumError) -> None:
        if not self.fut.cancelled():
            self.fut.set_exception(exc)

    def set_exception(self, exc: VacuumError) -> None:
        self.loop.call_soon_threadsafe(self._set_exception, exc)

    async def async_get(self, timeout: float | int) -> Any:
        """Get the result from the future or raises an error."""
        try:
            async with async_timeout.timeout(timeout):
                return await self.fut
        finally:
            self.fut.cancel()

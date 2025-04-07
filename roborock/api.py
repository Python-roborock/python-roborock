"""The Roborock api."""

from __future__ import annotations

import asyncio
import base64
import logging
import secrets
import time
from abc import ABC, abstractmethod
from typing import Any

from .containers import (
    DeviceData,
)
from .exceptions import (
    RoborockTimeout,
    UnknownMethodError,
)
from .roborock_future import RequestKey, RoborockFuture, WaitingQueue
from .roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)
from .util import get_next_int

_LOGGER = logging.getLogger(__name__)
KEEPALIVE = 60


class RoborockClient(ABC):
    """Roborock client base class."""

    _logger: logging.LoggerAdapter
    queue_timeout: int

    def __init__(self, device_info: DeviceData) -> None:
        """Initialize RoborockClient."""
        self.device_info = device_info
        self._nonce = secrets.token_bytes(16)
        self._waiting_queue = WaitingQueue()
        self._last_device_msg_in = time.monotonic()
        self._last_disconnection = time.monotonic()
        self.keep_alive = KEEPALIVE
        self._diagnostic_data: dict[str, dict[str, Any]] = {
            "misc_info": {"Nonce": base64.b64encode(self._nonce).decode("utf-8")}
        }
        self.is_available: bool = True

    async def async_release(self) -> None:
        await self.async_disconnect()

    @property
    def diagnostic_data(self) -> dict:
        return self._diagnostic_data

    @abstractmethod
    async def async_connect(self):
        """Connect to the Roborock device."""

    @abstractmethod
    async def async_disconnect(self) -> Any:
        """Disconnect from the Roborock device."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the client is connected to the device."""

    @abstractmethod
    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        """Handle received incoming messages from the device."""

    def on_connection_lost(self, exc: Exception | None) -> None:
        self._last_disconnection = time.monotonic()
        self._logger.info("Roborock client disconnected")
        if exc is not None:
            self._logger.warning(exc)

    def should_keepalive(self) -> bool:
        now = time.monotonic()
        # noinspection PyUnresolvedReferences
        if now - self._last_disconnection > self.keep_alive**2 and now - self._last_device_msg_in > self.keep_alive:
            return False
        return True

    async def validate_connection(self) -> None:
        if not self.should_keepalive():
            self._logger.info("Resetting Roborock connection due to kepalive timeout")
            await self.async_disconnect()
        await self.async_connect()

    async def _wait_response(self, request_key: RequestKey, future: RoborockFuture) -> Any:
        try:
            response = await future.async_get(self.queue_timeout)
            if response == "unknown_method":
                raise UnknownMethodError("Unknown method")
            return response
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(f"id={request_key} Timeout after {self.queue_timeout} seconds") from None
        finally:
            self._waiting_queue.safe_pop(request_key)


    def _async_response(self, request_key: RequestKey) -> Any:
        future = RoborockFuture()
        self._waiting_queue.put(request_key, future)
        return asyncio.ensure_future(self._wait_response(request_key, future))

    @abstractmethod
    async def send_message(self, roborock_message: RoborockMessage):
        """Send a message to the Roborock device."""

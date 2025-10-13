from __future__ import annotations

import asyncio
from asyncio import Future
from typing import Any

from .exceptions import VacuumError


class RoborockFuture:
    def __init__(self, protocol: int):
        self.protocol = protocol
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

    async def async_get(self, timeout: float | int) -> tuple[Any, VacuumError | None]:
        try:
            async with asyncio.timeout(timeout):
                return await self.fut
        finally:
            self.fut.cancel()

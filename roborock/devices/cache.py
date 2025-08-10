"""This module provides caching functionality for the Roborock device management system.

This module defines a cache interface that you may use to cache device
information to avoid unnecessary API calls. Callers may implement
this interface to provide their own caching mechanism.
"""

from dataclasses import dataclass, field
from typing import Protocol

from roborock.containers import HomeData, NetworkInfo


@dataclass
class CacheData:
    """Data structure for caching device information."""

    home_data: HomeData | None = None
    """Home data containing device and product information."""

    network_info: dict[str, NetworkInfo] = field(default_factory=dict)
    """Network information indexed by device DUID."""


class Cache(Protocol):
    """Protocol for a cache that can store and retrieve values."""

    async def get(self) -> CacheData:
        """Get cached value."""
        ...

    async def set(self, value: CacheData) -> None:
        """Set value in the cache."""
        ...


class InMemoryCache(Cache):
    """In-memory cache implementation."""

    def __init__(self):
        self._data = CacheData()

    async def get(self) -> CacheData:
        return self._data

    async def set(self, value: CacheData) -> None:
        self._data = value


class NoCache(Cache):
    """No-op cache implementation."""

    async def get(self) -> CacheData:
        return CacheData()

    async def set(self, value: CacheData) -> None:
        pass

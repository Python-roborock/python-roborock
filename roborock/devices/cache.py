"""This module provides caching functionality for the Roborock device management system.

This module defines a cache interface that you may use to cache device
information to avoid unnecessary API calls. Callers may implement
this interface to provide their own caching mechanism.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from roborock.data import CombinedMapInfo, HomeData, NetworkInfo
from roborock.device_features import DeviceFeatures


@dataclass
class CacheData:
    """Data structure for caching device information."""

    home_data: HomeData | None = None
    """Home data containing device and product information."""

    network_info: dict[str, NetworkInfo] = field(default_factory=dict)
    """Network information indexed by device DUID."""

    home_map_info: dict[int, CombinedMapInfo] = field(default_factory=dict)
    """Home map information indexed by map_flag."""

    home_map_content: dict[int, bytes] = field(default_factory=dict)
    """Home cache content for each map data indexed by map_flag."""

    device_features: DeviceFeatures | None = None
    """Device features information."""

    trait_data: dict[str, Any] | None = None
    """Trait-specific cached data used internally for caching device features."""


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

    def __init__(self) -> None:
        """Initialize the in-memory cache."""
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

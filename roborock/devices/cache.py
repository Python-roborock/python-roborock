"""This module provides caching functionality for the Roborock device management system.

This module defines a cache interface that you may use to cache device
information to avoid unnecessary API calls. Callers may implement
this interface to provide their own caching mechanism.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from roborock.data import CombinedMapInfo, HomeData, NetworkInfo, RoborockBase
from roborock.device_features import DeviceFeatures


@dataclass
class DeviceCacheData(RoborockBase):
    """Data structure for caching device information."""

    network_info: NetworkInfo | None = None
    """Network information for the device"""

    home_map_info: dict[int, CombinedMapInfo] | None = None
    """Home map information for the device by map_flag."""

    home_map_content_base64: dict[int, str] | None = None
    """Home cache content for the device (encoded base64) by map_flag."""

    device_features: DeviceFeatures | None = None
    """Device features information."""

    trait_data: dict[str, Any] | None = None
    """Trait-specific cached data used internally for caching device features."""


@dataclass
class CacheData(RoborockBase):
    """Data structure for caching device information."""

    home_data: HomeData | None = None
    """Home data containing device and product information."""

    device_info: dict[str, DeviceCacheData] = field(default_factory=dict)
    """Per-device cached information indexed by device DUID."""

    network_info: dict[str, NetworkInfo] = field(default_factory=dict)
    """Network information indexed by device DUID.

    This is deprecated. Use the per-device `network_info` field instead.
    """

    home_map_info: dict[int, CombinedMapInfo] = field(default_factory=dict)
    """Home map information indexed by map_flag.

    This is deprecated. Use the per-device `home_map_info` field instead.
    """

    home_map_content: dict[int, bytes] = field(default_factory=dict)
    """Home cache content for each map data indexed by map_flag.

    This is deprecated. Use the per-device `home_map_content_base64` field instead.
    """

    home_map_content_base64: dict[int, str] = field(default_factory=dict)
    """Home cache content for each map data (encoded base64) indexed by map_flag.

    This is deprecated. Use the per-device `home_map_content_base64` field instead.
    """

    device_features: DeviceFeatures | None = None
    """Device features information.

    This is deprecated. Use the per-device `device_features` field instead.
    """

    trait_data: dict[str, Any] | None = None
    """Trait-specific cached data used internally for caching device features.

    This is deprecated. Use the per-device `trait_data` field instead.
    """


class Cache(Protocol):
    """Protocol for a cache that can store and retrieve values."""

    async def get(self) -> CacheData:
        """Get cached value."""
        ...

    async def set(self, value: CacheData) -> None:
        """Set value in the cache."""
        ...


@dataclass
class DeviceCache(RoborockBase):
    """Provides a cache interface for a specific device.

    This is a convenience wrapper around a general Cache implementation to
    provide device-specific caching functionality.
    """

    def __init__(self, duid: str, cache: Cache) -> None:
        """Initialize the device cache with the given cache implementation."""
        self._duid = duid
        self._cache = cache

    async def get(self) -> DeviceCacheData:
        """Get cached device-specific information."""
        cache_data = await self._cache.get()
        if self._duid not in cache_data.device_info:
            cache_data.device_info[self._duid] = DeviceCacheData()
            await self._cache.set(cache_data)
        return cache_data.device_info[self._duid]

    async def set(self, device_cache_data: DeviceCacheData) -> None:
        """Set cached device-specific information."""
        cache_data = await self._cache.get()
        cache_data.device_info[self._duid] = device_cache_data
        await self._cache.set(cache_data)


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

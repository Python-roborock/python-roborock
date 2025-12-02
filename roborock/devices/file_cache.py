"""This module implements a file-backed cache for device information.

This module provides a `FileCache` class that implements the `Cache` protocol
to store and retrieve cached device information from a file on disk. This allows
persistent caching of device data across application restarts.
"""

import asyncio
import pathlib
import pickle
from collections.abc import Callable
from typing import Any

from .cache import Cache, CacheData


class FileCache(Cache):
    """File backed cache implementation."""

    def __init__(
        self,
        file_path: pathlib.Path,
        init_fn: Callable[[], CacheData] = CacheData,
        serialize_fn: Callable[[Any], bytes] = pickle.dumps,
        deserialize_fn: Callable[[bytes], Any] = pickle.loads,
    ) -> None:
        """Initialize the file cache with the given file path."""
        self._init_fn = init_fn
        self._file_path = file_path
        self._cache_data: CacheData | None = None
        self._serialize_fn = serialize_fn
        self._deserialize_fn = deserialize_fn

    async def get(self) -> CacheData:
        """Get cached value."""
        if self._cache_data is not None:
            return self._cache_data
        data = await load_value(self._file_path, self._deserialize_fn)
        if data is not None and not isinstance(data, CacheData):
            raise TypeError(f"Invalid cache data loaded from {self._file_path}")

        self._cache_data = data or self._init_fn()
        return self._cache_data

    async def set(self, value: CacheData) -> None:  # type: ignore[override]
        """Set value in the cache."""
        self._cache_data = value

    async def flush(self) -> None:
        """Flush the cache to disk."""
        if self._cache_data is None:
            return
        await store_value(self._file_path, self._cache_data, self._serialize_fn)


async def store_value(file_path: pathlib.Path, value: Any, serialize_fn: Callable[[Any], bytes] = pickle.dumps) -> None:
    """Store a value to the given file path."""

    def _store_to_disk(file_path: pathlib.Path, value: Any) -> None:
        with open(file_path, "wb") as f:
            data = serialize_fn(value)
            f.write(data)

    await asyncio.to_thread(_store_to_disk, file_path, value)


async def load_value(file_path: pathlib.Path, deserialize_fn: Callable[[bytes], Any] = pickle.loads) -> Any | None:
    """Load a value from the given file path."""

    def _load_from_disk(file_path: pathlib.Path) -> Any | None:
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            data = f.read()
            return deserialize_fn(data)

    return await asyncio.to_thread(_load_from_disk, file_path)

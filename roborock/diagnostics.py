"""Diagnostics for debugging.

A Diagnostics object can be used to track counts and latencies of various
operations within a module. This can be useful for debugging performance issues
or understanding usage patterns.

This is an internal facing module and is not intended for public use. Diagnostics
data is collected and exposed to clients via higher level APIs like the
DeviceManager.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any, TypeVar, cast


class Diagnostics:
    """A class that holds diagnostics information for a module.

    You can use this class to hold counter or for recording timing information
    that can be exported as a dictionary for debugging purposes.
    """

    def __init__(self) -> None:
        """Initialize Diagnostics."""
        self._counter: Counter = Counter()
        self._subkeys: dict[str, Diagnostics] = {}

    def increment(self, key: str, count: int = 1) -> None:
        """Increment a counter for the specified key/event."""
        self._counter.update(Counter({key: count}))

    def elapsed(self, key_prefix: str, elapsed_ms: int = 1) -> None:
        """Track a latency event for the specified key/event prefix."""
        self.increment(f"{key_prefix}_count", 1)
        self.increment(f"{key_prefix}_sum", elapsed_ms)

    def as_dict(self) -> Mapping[str, Any]:
        """Return diagnostics as a debug dictionary."""
        data: dict[str, Any] = {k: self._counter[k] for k in self._counter}
        for k, d in self._subkeys.items():
            v = d.as_dict()
            if not v:
                continue
            data[k] = v
        return data

    def subkey(self, key: str) -> Diagnostics:
        """Return sub-Diagnostics object with the specified subkey.

        This will create a new Diagnostics object if one does not already exist
        for the specified subkey. Stats from the sub-Diagnostics will be included
        in the parent Diagnostics when exported as a dictionary.

        Args:
            key: The subkey for the diagnostics.

        Returns:
            The Diagnostics object for the specified subkey.
        """
        if key not in self._subkeys:
            self._subkeys[key] = Diagnostics()
        return self._subkeys[key]

    @contextmanager
    def timer(self, key_prefix: str) -> Generator[None, None, None]:
        """A context manager that records the timing of operations as a diagnostic."""
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            ms = int((end - start) * 1000)
            self.elapsed(key_prefix, ms)

    def reset(self) -> None:
        """Clear all diagnostics, for testing."""
        self._counter = Counter()
        for d in self._subkeys.values():
            d.reset()


T = TypeVar("T")

REDACT_KEYS = {
    # Potential identifiers
    "localKey",
    "mac",
    "bssid",
    "sn",
    "ip",
    "u",
    "s",
    "h",
    "k",
    # Large binary blobs are entirely omitted
    "imageContent",
    "mapData",
    "rawApiResponse",
}
DEVICE_UID = "duid"
REDACTED = "**REDACTED**"


def redact_device_data(data: T) -> T | dict[str, Any]:
    """Redact sensitive data in a dict."""
    if not isinstance(data, (Mapping, list)):
        return data

    if isinstance(data, list):
        return cast(T, [redact_device_data(item) for item in data])

    redacted = {**data}

    for key, value in redacted.items():
        if key in REDACT_KEYS:
            redacted[key] = REDACTED
        elif key == DEVICE_UID and isinstance(value, str):
            redacted[key] = redact_device_uid(value)
        elif isinstance(value, dict):
            redacted[key] = redact_device_data(value)
        elif isinstance(value, list):
            redacted[key] = [redact_device_data(item) for item in value]

    return redacted


def redact_topic_name(topic: str) -> str:
    """Redact potentially identifying information from a topic name."""
    parts = topic.split("/")
    redacted_parts = parts[:4]
    for part in parts[4:]:
        if len(part) <= 5:
            redacted_parts.append("*****")
        else:
            redacted_parts.append("*****" + part[-5:])
    return "/".join(redacted_parts)


def redact_device_uid(duid: str) -> str:
    """Redact a device UID to hide identifying information."""
    return "******" + duid[-5:]

"""Module for managing callback utility functions."""

import logging
from collections.abc import Callable
from typing import Generic, TypeVar

_LOGGER = logging.getLogger(__name__)

K = TypeVar("K")
V = TypeVar("V")


def safe_callback(callback: Callable[[V], None], logger: logging.Logger | None = None) -> Callable[[V], None]:
    """Wrap a callback to catch and log exceptions.

    This is useful for ensuring that errors in callbacks do not propagate
    and cause unexpected behavior. Any failures during callback execution will be logged.
    """

    if logger is None:
        logger = _LOGGER

    def wrapper(value: V) -> None:
        try:
            callback(value)
        except Exception as ex:  # noqa: BLE001
            logger.error("Uncaught error in callback '%s': %s", callback.__name__, ex)

    return wrapper


class CallbackMap(Generic[K, V]):
    """A mapping of callbacks for specific keys.

    This allows for registering multiple callbacks for different keys and invoking them
    when a value is received for a specific key.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._callbacks: dict[K, list[Callable[[V], None]]] = {}
        self._logger = logger or _LOGGER

    def keys(self) -> list[K]:
        """Get all keys in the callback map."""
        return list(self._callbacks.keys())

    def add_callback(self, key: K, callback: Callable[[V], None]) -> Callable[[], None]:
        """Add a callback for a specific key.

        Any failures during callback execution will be logged.

        Returns a callable that can be used to remove the callback.
        """
        self._callbacks.setdefault(key, []).append(callback)

        def remove_callback() -> None:
            """Remove the callback for the specific key."""
            if cb_list := self._callbacks.get(key):
                cb_list.remove(callback)
                if not cb_list:
                    del self._callbacks[key]

        return remove_callback

    def get_callbacks(self, key: K) -> list[Callable[[V], None]]:
        """Get all callbacks for a specific key."""
        return self._callbacks.get(key, [])

    def __call__(self, key: K, value: V) -> None:
        """Invoke all callbacks for a specific key."""
        for callback in self.get_callbacks(key):
            safe_callback(callback, self._logger)(value)


class CallbackList(Generic[V]):
    """A list of callbacks that can be invoked.

    This combines a list of callbacks into a single callable. Callers can add
    additional callbacks to the list at any time.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._callbacks: list[Callable[[V], None]] = []
        self._logger = logger or _LOGGER

    def add_callback(self, callback: Callable[[V], None]) -> Callable[[], None]:
        """Add a callback to the list.

        Any failures during callback execution will be logged.

        Returns a callable that can be used to remove the callback.
        """
        self._callbacks.append(callback)

        return lambda: self._callbacks.remove(callback)

    def __call__(self, value: V) -> None:
        """Invoke all callbacks in the list."""
        for callback in self._callbacks:
            safe_callback(callback, self._logger)(value)


def decoder_callback(
    decoder: Callable[[K], list[V]], callback: Callable[[V], None], logger: logging.Logger | None = None
) -> Callable[[K], None]:
    """Create a callback that decodes messages using a decoder and invokes a callback.

    The decoder converts a value into a list of values. The callback is then invoked
    for each value in the list.

    Any failures during decoding or invoking the callbacks will be logged.
    """
    if logger is None:
        logger = _LOGGER

    safe_cb = safe_callback(callback, logger)

    def wrapper(data: K) -> None:
        if not (messages := decoder(data)):
            logger.warning("Failed to decode message: %s", data)
            return
        for message in messages:
            _LOGGER.debug("Decoded message: %s", message)
            safe_cb(message)

    return wrapper

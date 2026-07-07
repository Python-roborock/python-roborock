"""Fake channel transport implementation for python-roborock.

This module defines `FakeChannel`, which simulates low-level connection,
subscription, and publishing logic at the message boundary. It acts as an
in-memory replacement for `MqttChannel` and `LocalChannel` during testing.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from roborock.devices.transport.channel import Channel
from roborock.mqtt.health_manager import HealthManager
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockMessage


class FakeChannel(Channel):
    """A stateful, in-memory transport simulator implementing the Channel protocol.

    It captures all published messages in `published_messages`, maintains a registry
    of active callbacks in `subscribers`, and enables tests or stateful simulators to
    unconditionally push unsolicited messages using `notify_subscribers`.

    Caller API
    ----------
    The public interface consists of `AsyncMock` / `MagicMock` attributes that
    wrap internal implementations. Because they are mocks, callers can:

    - **Inspect calls**: ``channel.publish.assert_called_once()``
    - **Inject failures**: ``channel.publish.side_effect = RoborockException(...)``
      to simulate transport errors on the next publish.
    - **Replace behavior**: ``channel.connect.side_effect = my_custom_connect``
      to substitute entirely custom logic.
    - **Queue canned responses**: Append to ``channel.response_queue`` to have
      the channel automatically deliver a response to subscribers on the next
      publish (useful for low-level RPC request/response testing).
    - **Push unsolicited messages**: Call ``channel.notify_subscribers(msg)``
      to simulate the device broadcasting a state change.
    """

    subscribe: Any

    def __init__(self, is_local: bool = False):
        """Initialize the fake channel."""
        self.subscribers: list[Callable[[RoborockMessage], None]] = []
        self.published_messages: list[RoborockMessage] = []
        self.response_queue: list[RoborockMessage] = []
        self._is_connected = False
        self._is_local = is_local

        # Set this to an exception instance to make the next publish raise it.
        # This is a convenience shortcut; callers can also replace
        # ``publish.side_effect`` directly for more control.
        self.publish_side_effect: Exception | None = None

        # AsyncMock wrapping _publish. Callers can replace side_effect to
        # inject transport errors, e.g.:
        #   channel.publish.side_effect = RoborockException("timeout")
        self.publish = AsyncMock(side_effect=self._publish)

        # AsyncMock wrapping _subscribe. Callers can replace side_effect to
        # simulate subscription failures, e.g.:
        #   channel.subscribe.side_effect = RoborockException("sub failed")
        self.subscribe = AsyncMock(side_effect=self._subscribe)  # type: ignore[assignment]

        # AsyncMock wrapping _connect. Callers can replace side_effect to
        # simulate connection failures, e.g.:
        #   channel.connect.side_effect = RoborockException("refused")
        self.connect = AsyncMock(side_effect=self._connect)

        # MagicMock wrapping _close. Callers can assert close was called
        # or inject errors on teardown.
        self.close = MagicMock(side_effect=self._close)

        self.protocol_version = LocalProtocolVersion.V1
        self.restart = AsyncMock()
        self.health_manager = HealthManager(self.restart)

    async def _connect(self) -> None:
        self._is_connected = True

    def _close(self) -> None:
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Return true if connected."""
        return self._is_connected

    @property
    def is_local_connected(self) -> bool:
        """Return true if locally connected."""
        return self._is_connected and self._is_local

    async def _publish(self, message: RoborockMessage) -> None:
        """Default publish implementation.

        Records the message in ``published_messages`` and, if
        ``response_queue`` is non-empty, pops the first response and
        delivers it to all current subscribers (simulating a
        request/response round-trip).
        """
        self.published_messages.append(message)
        if self.publish_side_effect:
            raise self.publish_side_effect
        if self.response_queue:
            response = self.response_queue.pop(0)
            self.notify_subscribers(response)

    async def _subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Default subscribe implementation.

        Registers the callback and returns an unsubscribe function.
        """
        self.subscribers.append(callback)
        return lambda: self.subscribers.remove(callback)

    def notify_subscribers(self, message: RoborockMessage) -> None:
        """Deliver a message to all current subscribers.

        Use this to simulate the channel receiving an unsolicited message
        from the device (e.g. a state change broadcast).
        """
        for subscriber in list(self.subscribers):
            subscriber(message)

"""Fake channel transport implementation for python-roborock.

This module defines `FakeChannel`, which simulates low-level connection,
subscription, and publishing logic at the message boundary. It acts as an
in-memory replacement for `MqttChannel` and `LocalChannel` during testing.
"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from roborock.devices.transport.channel import Channel
from roborock.mqtt.health_manager import HealthManager
from roborock.mqtt.session import MqttQos
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
    - **Intercept published messages**: Register a handler/callback via
      ``channel.publish_handler = my_handler`` (e.g. stateful simulator)
      to reactively process commands.
    """

    subscribe: Any

    def __init__(self, is_local: bool = False):
        """Initialize the fake channel."""
        self.subscribers: list[Callable[[RoborockMessage], None]] = []
        self.published_messages: list[RoborockMessage] = []
        self.response_queue: list[RoborockMessage] = []
        self._is_connected = False
        self._is_local = is_local

        # A callback to intercept published messages (e.g., bound simulator handler).
        # Must be asynchronous: Callable[[RoborockMessage], Awaitable[Any]].
        # By default, routes to self._default_publish_handler to handle the response_queue.
        self.publish_handler: Callable[[RoborockMessage], Awaitable[Any]] | None = self._default_publish_handler

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

    async def _publish(self, message: RoborockMessage, qos: MqttQos = MqttQos.AT_MOST_ONCE) -> None:
        """Default publish implementation.

        Records the message in ``published_messages`` and executes ``publish_handler``.

        The ``qos`` parameter is accepted for compatibility with
        ``MqttChannel.publish`` but not simulated by the fake channel.
        """
        self.published_messages.append(message)
        if self.publish_side_effect:
            raise self.publish_side_effect
        if self.publish_handler:
            await self.publish_handler(message)

    async def _default_publish_handler(self, message: RoborockMessage) -> None:
        """Default handler that pops canned responses from response_queue."""
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

    def inject_error(self, exception: Exception) -> None:
        """Inject a transient failure into all channel operations (publish, subscribe, connect)."""
        self.publish.side_effect = exception
        self.subscribe.side_effect = exception
        self.connect.side_effect = exception

    def clear_error(self) -> None:
        """Restore default success behaviors on all channel operations."""
        self.publish.side_effect = self._publish
        self.subscribe.side_effect = self._subscribe
        self.connect.side_effect = self._connect

    async def subscribe_stream(self) -> AsyncGenerator[RoborockMessage, None]:
        """Stream messages received via this channel."""
        queue: asyncio.Queue[RoborockMessage] = asyncio.Queue()

        def callback(message: RoborockMessage) -> None:
            queue.put_nowait(message)

        unsub = await self.subscribe(callback)
        try:
            while True:
                yield await queue.get()
        finally:
            unsub()

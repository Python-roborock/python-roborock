from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

from roborock.mqtt.health_manager import HealthManager
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockMessage


class FakeChannel:
    """A fake channel that handles publish and subscribe calls."""

    def __init__(self):
        """Initialize the fake channel."""
        self.subscribers: list[Callable[[RoborockMessage], None]] = []
        self.published_messages: list[RoborockMessage] = []
        self.response_queue: list[RoborockMessage] = []
        self._is_connected = False
        self.publish_side_effect: Exception | None = None
        self.publish = AsyncMock(side_effect=self._publish)
        self.subscribe = AsyncMock(side_effect=self._subscribe)
        self.connect = AsyncMock(side_effect=self._connect)
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

    async def _publish(self, message: RoborockMessage) -> None:
        """Simulate publishing a message and triggering a response."""
        self.published_messages.append(message)
        if self.publish_side_effect:
            raise self.publish_side_effect
        # When a message is published, simulate a response
        if self.response_queue:
            response = self.response_queue.pop(0)
            # Give a chance for the subscriber to be registered
            for subscriber in list(self.subscribers):
                subscriber(response)

    async def _subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Simulate subscribing to messages."""
        self.subscribers.append(callback)
        return lambda: self.subscribers.remove(callback)

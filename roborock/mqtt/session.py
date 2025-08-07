"""An MQTT session for sending and receiving messages."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from roborock.exceptions import RoborockException

DEFAULT_TIMEOUT = 30.0


@dataclass
class MqttParams:
    """MQTT parameters for the connection."""

    host: str
    """MQTT host to connect to."""

    port: int
    """MQTT port to connect to."""

    tls: bool
    """Use TLS for the connection."""

    username: str
    """MQTT username to use for authentication."""

    password: str
    """MQTT password to use for authentication."""

    timeout: float = DEFAULT_TIMEOUT
    """Timeout for communications with the broker in seconds."""


class MqttSession(ABC):
    """An MQTT session for sending and receiving messages."""

    @property
    @abstractmethod
    def connected(self) -> bool:
        """True if the session is connected to the broker."""

    @abstractmethod
    async def subscribe(self, device_id: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        """Invoke the callback when messages are received on the topic.

        The returned callable unsubscribes from the topic when called.
        """

    @abstractmethod
    async def publish(self, topic: str, message: bytes) -> None:
        """Publish a message on the specified topic.

        This will raise an exception if the message could not be sent.
        """

    @abstractmethod
    async def close(self) -> None:
        """Cancels the mqtt loop"""


class MqttSessionException(RoborockException):
    """ "Raised when there is an error communicating with MQTT."""

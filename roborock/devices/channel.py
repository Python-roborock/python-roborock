"""Low-level interface for connections to Roborock devices."""

import logging
from collections.abc import Callable
from typing import Protocol

from roborock.roborock_message import RoborockMessage

_LOGGER = logging.getLogger(__name__)


class Channel(Protocol):
    """A generic channel for establishing a connection with a Roborock device.

    Individual channel implementations have their own methods for speaking to
    the device that hide some of the protocol specific complexity, but they
    are still specialized for the device type and protocol.
    """

    @property
    def is_connected(self) -> bool:
        """Return true if the channel is connected."""
        ...

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to messages from the device."""
        ...

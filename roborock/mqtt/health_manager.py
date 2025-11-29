"""A health manager for monitoring MQTT connections to Roborock devices.

We observe a problem where sometimes the MQTT connection appears to be alive but
no messages are being received. To mitigate this, we track consecutive timeouts
and restart the connection if too many timeouts occur in succession.
"""

import datetime
from collections.abc import Awaitable, Callable

# Number of consecutive timeouts before considering the connection unhealthy.
TIMEOUT_THRESHOLD = 3

# We won't restart the session more often than this interval.
RESTART_COOLDOWN = datetime.timedelta(minutes=30)


class HealthManager:
    """Manager for monitoring the health of MQTT connections.

    This tracks communication timeouts and can trigger restarts of the MQTT
    session if too many timeouts occur in succession.
    """

    def __init__(self, restart: Callable[[], Awaitable[None]]) -> None:
        """Initialize the health manager.

        Args:
            restart: A callable to restart the MQTT session.
        """
        self._consecutive_timeouts = 0
        self._restart = restart
        self._last_restart: datetime.datetime | None = None

    async def on_success(self) -> None:
        """Record a successful communication event."""
        self._consecutive_timeouts = 0

    async def on_timeout(self) -> None:
        """Record a timeout event.

        This may trigger a restart of the MQTT session if too many timeouts
        have occurred in succession.
        """
        self._consecutive_timeouts += 1
        if self._consecutive_timeouts >= TIMEOUT_THRESHOLD:
            now = datetime.datetime.now()
            if self._last_restart is None or now - self._last_restart >= RESTART_COOLDOWN:
                await self._restart()
                self._last_restart = now
                self._consecutive_timeouts = 0

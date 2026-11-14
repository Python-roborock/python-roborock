"""A health manager for monitoring MQTT connections to Roborock devices.

We observe a problem where sometimes the MQTT connection appears to be alive but
no messages are being received. To mitigate this, we track timeouts and restart
the connection if too many of them occur.

The broker can also stop delivering messages for a single device's topic while
the rest of the session keeps working, so timeouts are tracked both for the
session as a whole and for each device. Subscribing to the device's topic again
on the same connection does not bring the messages back; only a new connection
does, so the session is restarted. Such a failure can be partial, with some
requests still answered in between, so a device's timeouts are counted within a
time window rather than in a row.
"""

import datetime
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from roborock.diagnostics import redact_device_uid

_LOGGER = logging.getLogger(__name__)

# Number of timeouts before considering the connection unhealthy: in a row across the
# session, or within TIMEOUT_WINDOW for a single device.
TIMEOUT_THRESHOLD = 3

# Timeouts of a device older than this no longer count towards a restart. Successful
# requests in between don't reset the count, since a failing connection may still
# deliver some responses.
TIMEOUT_WINDOW = datetime.timedelta(minutes=30)

# A failing device counts as recovered after this many successful requests in a row, or at
# its first successful request once its timeouts fell out of TIMEOUT_WINDOW.
RECOVERY_THRESHOLD = 3

# We won't restart the session more often than this interval.
RESTART_COOLDOWN = datetime.timedelta(minutes=30)

# A device that fails while the rest of the session works may simply be offline,
# which a restart can't fix. Until it responds again, the interval between the
# session restarts it triggers doubles after each restart, up to this maximum.
MAX_DEVICE_RESTART_COOLDOWN = datetime.timedelta(hours=6)

# Number of health changes kept per device for diagnostics.
MAX_DEVICE_EVENTS = 10


@dataclass
class _DeviceHealth:
    """The MQTT request history of a single device."""

    recent_timeouts: deque[datetime.datetime] = field(default_factory=deque)
    successes_in_a_row: int = 0
    failing_since: datetime.datetime | None = None
    restart_cooldown_start: datetime.datetime | None = None
    restart_cooldown: datetime.timedelta | None = None
    timeouts: int = 0
    successes: int = 0
    last_success: datetime.datetime | None = None
    last_timeout: datetime.datetime | None = None
    events: deque[dict[str, str]] = field(default_factory=lambda: deque(maxlen=MAX_DEVICE_EVENTS))

    def add_event(self, time: datetime.datetime, event: str, **details: str) -> None:
        """Record a change of the device's health for diagnostics."""
        self.events.append({"time": time.isoformat(), "event": event, **details})

    def forget_old_timeouts(self, now: datetime.datetime) -> None:
        """Drop the timeouts that fell out of the time window."""
        while self.recent_timeouts and now - self.recent_timeouts[0] >= TIMEOUT_WINDOW:
            self.recent_timeouts.popleft()


def _isoformat(value: datetime.datetime | None) -> str | None:
    """Format an optional timestamp for diagnostics."""
    return value.isoformat() if value else None


def _duration(value: datetime.timedelta) -> datetime.timedelta:
    """Round a duration to whole seconds for logs.

    Logs show durations rather than timestamps, which are in UTC and easy to
    misread in another time zone.
    """
    return datetime.timedelta(seconds=round(value.total_seconds()))


class HealthManager:
    """Manager for monitoring the health of MQTT connections.

    This tracks communication timeouts and can trigger restarts of the MQTT
    session if too many timeouts occur, either in a row across the whole
    session or within a time window for a single device.
    """

    def __init__(
        self,
        restart: Callable[[], Awaitable[None]],
        is_connected: Callable[[], bool] = lambda: True,
    ) -> None:
        """Initialize the health manager.

        Args:
            restart: A callable to restart the MQTT session.
            is_connected: A callable returning whether the session is connected. While it
                isn't, the session is already reconnecting, so timeouts don't restart it.
        """
        self._consecutive_timeouts = 0
        self._timed_out_devices: set[str] = set()
        self._devices: dict[str, _DeviceHealth] = {}
        self._restart = restart
        self._is_connected = is_connected
        self._last_restart: datetime.datetime | None = None

    def _device(self, device_id: str) -> _DeviceHealth:
        """Return the history of a device, creating it on first use."""
        return self._devices.setdefault(device_id, _DeviceHealth())

    def on_connected(self) -> None:
        """Forget the timeouts counted on a previous connection.

        Timeouts on an old connection say nothing about a new one, whether the
        session reconnected on its own or was restarted.
        """
        self._consecutive_timeouts = 0
        self._timed_out_devices.clear()
        for device in self._devices.values():
            device.recent_timeouts.clear()

    async def on_success(self, device_id: str) -> None:
        """Record a successful communication event for a device."""
        self._consecutive_timeouts = 0
        self._timed_out_devices.clear()
        device = self._device(device_id)
        now = datetime.datetime.now(datetime.UTC)
        device.successes += 1
        device.successes_in_a_row += 1
        device.last_success = now
        device.forget_old_timeouts(now)
        # Only responses in a row show the device is reliable again. A device that answers
        # once after every restart and then fails again keeps its growing restart interval.
        if device.successes_in_a_row >= RECOVERY_THRESHOLD:
            device.restart_cooldown_start = None
            device.restart_cooldown = None
        if device.failing_since is None:
            return
        # A single response in between timeouts doesn't mean the device recovered yet.
        if device.recent_timeouts and device.successes_in_a_row < RECOVERY_THRESHOLD:
            return
        _LOGGER.info(
            "Device %s responds over MQTT again after timing out for %s",
            redact_device_uid(device_id),
            _duration(now - device.failing_since),
        )
        device.add_event(now, "recovered")
        device.recent_timeouts.clear()
        device.failing_since = None

    async def on_timeout(self, device_id: str) -> None:
        """Record a timeout event for a device.

        This may trigger a restart of the MQTT session if too many timeouts
        have occurred.
        """
        now = datetime.datetime.now(datetime.UTC)
        self._consecutive_timeouts += 1
        self._timed_out_devices.add(device_id)
        device = self._device(device_id)
        device_name = redact_device_uid(device_id)
        if device.failing_since is None:
            device.failing_since = now
            _LOGGER.info("Device %s started timing out over MQTT", device_name)
            device.add_event(now, "timeouts_started")
        device.forget_old_timeouts(now)
        device.recent_timeouts.append(now)
        device.successes_in_a_row = 0
        device.timeouts += 1
        device.last_timeout = now

        # Only timeouts from several devices implicate the session itself. A single failing device
        # may just be offline, even when it is the only device reporting to this session.
        session_unhealthy = self._consecutive_timeouts >= TIMEOUT_THRESHOLD and len(self._timed_out_devices) > 1
        if not session_unhealthy and len(device.recent_timeouts) < TIMEOUT_THRESHOLD:
            return

        if not self._is_connected():
            _LOGGER.debug("Not restarting MQTT session for device %s, it is already reconnecting", device_name)
            return

        since_last = (now - self._last_restart) if self._last_restart else None
        if since_last is not None and since_last < RESTART_COOLDOWN:
            _LOGGER.debug(
                "Not restarting MQTT session for device %s, last restart was %s ago", device_name, _duration(since_last)
            )
            return

        reason = f"{self._consecutive_timeouts} timeouts in a row across {len(self._timed_out_devices)} devices"
        if not session_unhealthy:
            cooldown_start, cooldown = device.restart_cooldown_start, device.restart_cooldown
            if cooldown_start is not None and cooldown is not None and now - cooldown_start < cooldown:
                _LOGGER.debug(
                    "Not restarting MQTT session for device %s, it is still failing and may restart it again in %s",
                    device_name,
                    _duration(cooldown_start + cooldown - now),
                )
                return
            device.restart_cooldown_start = now
            device.restart_cooldown = (
                min(cooldown * 2, MAX_DEVICE_RESTART_COOLDOWN) if cooldown is not None else RESTART_COOLDOWN
            )
            reason = (
                f"device {device_name} timed out {len(device.recent_timeouts)} times in {TIMEOUT_WINDOW}; "
                f"it may restart the session again in {device.restart_cooldown} if it keeps failing"
            )

        _LOGGER.info(
            "Restarting MQTT session: %s (last restart: %s)",
            reason,
            f"{_duration(since_last)} ago" if since_last is not None else "never",
        )
        # Update the state before awaiting, so timeouts arriving meanwhile don't restart again.
        self._last_restart = now
        # The restart affects every device, so each one records it along with what caused it.
        several_devices = len(self._timed_out_devices) > 1
        for tracked_id, tracked_device in self._devices.items():
            if several_devices:
                cause = "several_devices"
            else:
                cause = "this_device" if tracked_id == device_id else "other_device"
            tracked_device.add_event(now, "session_restart", cause=cause)
            # Timeouts on the old connection say nothing about the new one.
            tracked_device.recent_timeouts.clear()
        self._consecutive_timeouts = 0
        self._timed_out_devices.clear()
        await self._restart()

    def device_diagnostic_data(self, device_id: str) -> dict[str, Any]:
        """Return diagnostics about a device's MQTT requests."""
        device = self._devices.get(device_id, _DeviceHealth())
        return {
            "failing_since": _isoformat(device.failing_since),
            "last_success": _isoformat(device.last_success),
            "last_timeout": _isoformat(device.last_timeout),
            "successes": device.successes,
            "timeouts": device.timeouts,
            # Newest first, so the current state of the device is at the top.
            "events": [dict(event) for event in reversed(device.events)],
        }


class DeviceHealthManager:
    """Reports the outcome of a single device's MQTT requests to the session's health manager."""

    def __init__(self, health_manager: HealthManager, device_id: str) -> None:
        """Initialize the device health manager."""
        self._health_manager = health_manager
        self._device_id = device_id

    async def on_success(self) -> None:
        """Record a successful communication event."""
        await self._health_manager.on_success(self._device_id)

    async def on_timeout(self) -> None:
        """Record a timeout event."""
        await self._health_manager.on_timeout(self._device_id)

    def diagnostic_data(self) -> dict[str, Any]:
        """Return diagnostics about this device's MQTT requests."""
        return self._health_manager.device_diagnostic_data(self._device_id)

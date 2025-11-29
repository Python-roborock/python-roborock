"""Tests for the health manager."""

import datetime
from unittest.mock import AsyncMock, patch

from roborock.mqtt.health_manager import HealthManager


async def test_health_manager_restart_called_after_timeouts() -> None:
    """Test that the health manager calls restart after consecutive timeouts."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)

    await health_manager.on_timeout()
    await health_manager.on_timeout()
    restart.assert_not_called()

    await health_manager.on_timeout()
    restart.assert_called_once()


async def test_health_manager_success_resets_counter() -> None:
    """Test that a successful message resets the timeout counter."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)

    await health_manager.on_timeout()
    await health_manager.on_timeout()
    restart.assert_not_called()

    await health_manager.on_success()

    await health_manager.on_timeout()
    await health_manager.on_timeout()
    restart.assert_not_called()

    await health_manager.on_timeout()
    restart.assert_called_once()


async def test_cooldown() -> None:
    """Test that the health manager respects the restart cooldown."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now

        # Trigger first restart
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        # Advance time but stay within cooldown (30 mins)
        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=10)

        # Trigger timeouts again
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        restart.assert_not_called()

        # Advance time past cooldown
        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=31)

        # Trigger timeouts again
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        restart.assert_called_once()

"""Tests for the health manager."""

import asyncio
import datetime
import logging
from unittest.mock import AsyncMock, patch

import pytest

from roborock.mqtt.health_manager import (
    MAX_DEVICE_EVENTS,
    MAX_DEVICE_RESTART_COOLDOWN,
    RECOVERY_THRESHOLD,
    TIMEOUT_WINDOW,
    DeviceHealthManager,
    HealthManager,
)

DEVICE_ID = "device-1"


async def test_health_manager_restart_called_after_timeouts() -> None:
    """Test that the health manager calls restart after consecutive timeouts."""
    restart = AsyncMock()
    health_manager = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    await health_manager.on_timeout()
    await health_manager.on_timeout()
    restart.assert_not_called()

    await health_manager.on_timeout()
    restart.assert_called_once()


async def test_responses_in_between_do_not_hide_a_partial_failure() -> None:
    """Test that timeouts interleaved with successful responses still restart the session."""
    restart = AsyncMock()
    health_manager = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    await health_manager.on_timeout()
    await health_manager.on_success()
    await health_manager.on_timeout()
    await health_manager.on_success()
    restart.assert_not_called()

    await health_manager.on_timeout()
    restart.assert_called_once()
    # The device kept timing out, so the responses in between are not recorded as a recovery.
    assert [event["event"] for event in health_manager.diagnostic_data()["events"]] == [
        "session_restart",
        "timeouts_started",
    ]


async def test_responses_in_a_row_mark_recovery() -> None:
    """Test that a device answering several requests in a row recovers before its timeouts expire."""
    restart = AsyncMock()
    health_manager = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    await health_manager.on_timeout()
    await health_manager.on_timeout()
    for _ in range(RECOVERY_THRESHOLD - 1):
        await health_manager.on_success()
    assert health_manager.diagnostic_data()["failing_since"] is not None

    await health_manager.on_success()
    assert health_manager.diagnostic_data()["failing_since"] is None
    assert [event["event"] for event in health_manager.diagnostic_data()["events"]] == [
        "recovered",
        "timeouts_started",
    ]

    # The timeouts before the recovery no longer count towards a restart.
    await health_manager.on_timeout()
    await health_manager.on_timeout()
    restart.assert_not_called()


async def test_timeouts_before_a_reconnect_do_not_count() -> None:
    """Test that a new connection is not restarted because of the old connection's timeouts."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    device = DeviceHealthManager(health_manager, DEVICE_ID)

    await device.on_timeout()
    await device.on_timeout()
    health_manager.on_connected()

    await device.on_timeout()
    await device.on_timeout()
    restart.assert_not_called()

    await device.on_timeout()
    restart.assert_called_once()


async def test_old_timeouts_do_not_count() -> None:
    """Test that only the timeouts within the time window restart the session."""
    restart = AsyncMock()
    health_manager = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        await health_manager.on_timeout()
        await health_manager.on_timeout()

        mock_datetime.datetime.now.return_value = now + TIMEOUT_WINDOW
        await health_manager.on_timeout()
        await health_manager.on_timeout()
        restart.assert_not_called()

        await health_manager.on_timeout()
        restart.assert_called_once()


async def test_cooldown() -> None:
    """Test that the health manager respects the restart cooldown."""
    restart = AsyncMock()
    health_manager = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

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


async def test_timeouts_across_devices_restart_session() -> None:
    """Test that timeouts spread across devices still count towards the session."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)

    await DeviceHealthManager(health_manager, "device-1").on_timeout()
    await DeviceHealthManager(health_manager, "device-2").on_timeout()
    restart.assert_not_called()

    await DeviceHealthManager(health_manager, "device-3").on_timeout()
    restart.assert_called_once()


async def test_other_device_success_does_not_hide_failing_device() -> None:
    """Test that one device's timeouts restart the session while another device works."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    await failing.on_timeout()
    await failing.on_timeout()
    await working.on_success()
    restart.assert_not_called()

    await failing.on_timeout()
    restart.assert_called_once()


async def test_device_needs_timeouts_of_its_own() -> None:
    """Test that timeouts of other devices don't count towards a device's restart."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    device = DeviceHealthManager(health_manager, DEVICE_ID)
    other = DeviceHealthManager(health_manager, "other")

    await device.on_timeout()
    await device.on_success()
    await other.on_timeout()
    await other.on_success()
    await device.on_timeout()
    restart.assert_not_called()


async def test_restart_clears_counters_of_all_devices() -> None:
    """Test that every device starts counting again after a session restart."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    first = DeviceHealthManager(health_manager, "first")
    second = DeviceHealthManager(health_manager, "second")
    working = DeviceHealthManager(health_manager, "working")

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now

        await second.on_timeout()
        await second.on_timeout()
        await working.on_success()
        await first.on_timeout()
        await first.on_timeout()
        await working.on_success()
        await first.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        # The restart gave "second" a new subscription, so its earlier timeouts no longer count.
        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=31)
        await working.on_success()
        await second.on_timeout()
        restart.assert_not_called()


async def test_single_failing_device_cooldown_grows() -> None:
    """Test that a device that stays unreachable restarts a working session less and less often."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    async def time_out_while_session_works() -> None:
        for _ in range(3):
            await working.on_success()
            await failing.on_timeout()

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        await time_out_while_session_works()
        restart.assert_called_once()

        # The interval between restarts doubles from the session cooldown up to the maximum.
        hours = datetime.timedelta(hours=1)
        for cooldown in (
            hours / 2,
            hours,
            2 * hours,
            4 * hours,
            MAX_DEVICE_RESTART_COOLDOWN,
            MAX_DEVICE_RESTART_COOLDOWN,
        ):
            restart.reset_mock()
            mock_datetime.datetime.now.return_value = now + cooldown - datetime.timedelta(minutes=1)
            await time_out_while_session_works()
            restart.assert_not_called()

            now += cooldown
            mock_datetime.datetime.now.return_value = now
            await time_out_while_session_works()
            restart.assert_called_once()


@pytest.mark.parametrize(
    ("responses_between", "restarts_again"),
    [
        # A single response after each restart doesn't reset the growing interval.
        (1, False),
        (RECOVERY_THRESHOLD, True),
    ],
)
async def test_responses_in_a_row_clear_device_cooldown(responses_between: int, restarts_again: bool) -> None:
    """Test that only a device answering several requests in a row gets its restart interval reset."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    async def time_out_while_session_works() -> None:
        for _ in range(3):
            await working.on_success()
            await failing.on_timeout()

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        for _ in range(2):
            mock_datetime.datetime.now.return_value = now
            await time_out_while_session_works()
            health_manager.on_connected()
            for _ in range(responses_between):
                await failing.on_success()
            now += datetime.timedelta(minutes=31)
        assert restart.call_count == 2
        restart.reset_mock()

        # The interval grew to an hour, unless the device proved reliable in between.
        mock_datetime.datetime.now.return_value = now
        await time_out_while_session_works()
        assert restart.called is restarts_again


async def test_device_diagnostics_are_separate_per_device() -> None:
    """Test that diagnostics keep each device's history apart and survive counter resets."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        mock_datetime.datetime.now.return_value = now
        await failing.on_success()

        mock_datetime.datetime.now.return_value = now + datetime.timedelta(hours=1)
        for _ in range(4):
            await working.on_success()
            await failing.on_timeout()

    last_timeout = "2023-01-01T13:00:00+00:00"
    assert failing.diagnostic_data() == {
        "failing_since": last_timeout,
        "last_success": "2023-01-01T12:00:00+00:00",
        "last_timeout": last_timeout,
        "successes": 1,
        "timeouts": 4,
        "events": [
            {"time": last_timeout, "event": "session_restart", "cause": "this_device"},
            {"time": last_timeout, "event": "timeouts_started"},
        ],
    }
    assert working.diagnostic_data() == {
        "failing_since": None,
        "last_success": last_timeout,
        "last_timeout": None,
        "successes": 4,
        "timeouts": 0,
        "events": [
            {"time": last_timeout, "event": "session_restart", "cause": "other_device"},
        ],
    }


async def test_diagnostics_for_device_without_requests() -> None:
    """Test the diagnostics of a device that has not used MQTT yet."""
    device = DeviceHealthManager(HealthManager(restart=AsyncMock()), DEVICE_ID)

    assert device.diagnostic_data() == {
        "failing_since": None,
        "last_success": None,
        "last_timeout": None,
        "successes": 0,
        "timeouts": 0,
        "events": [],
    }


async def test_diagnostics_record_when_timeouts_start_and_recover() -> None:
    """Test that only changes of a device's health are recorded."""
    device = DeviceHealthManager(HealthManager(restart=AsyncMock()), DEVICE_ID)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        start = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        mock_datetime.datetime.now.return_value = start
        await device.on_success()
        await device.on_timeout()
        await device.on_timeout()

        # A response while the timeouts still count is not a recovery yet.
        mock_datetime.datetime.now.return_value = start + datetime.timedelta(minutes=10)
        await device.on_success()

        recovered = start + TIMEOUT_WINDOW
        mock_datetime.datetime.now.return_value = recovered
        await device.on_success()
        await device.on_success()

    assert device.diagnostic_data()["events"] == [
        {"time": recovered.isoformat(), "event": "recovered"},
        {"time": start.isoformat(), "event": "timeouts_started"},
    ]
    assert device.diagnostic_data()["failing_since"] is None


async def test_no_restart_while_session_reconnects() -> None:
    """Test that timeouts while the session is already reconnecting don't restart it."""
    restart = AsyncMock()
    connected = False
    health_manager = HealthManager(restart=restart, is_connected=lambda: connected)
    device = DeviceHealthManager(health_manager, DEVICE_ID)

    for _ in range(3):
        await device.on_timeout()
    restart.assert_not_called()
    assert [event["event"] for event in device.diagnostic_data()["events"]] == ["timeouts_started"]

    # Once connected, the device's recent timeouts still count.
    connected = True
    await device.on_timeout()
    restart.assert_called_once()


async def test_diagnostics_record_recovery_after_restart() -> None:
    """Test that a device that recovers after a session restart is recorded as recovered."""
    restart = AsyncMock()
    device = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        start = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        mock_datetime.datetime.now.return_value = start
        for _ in range(3):
            await device.on_timeout()
        restart.assert_called_once()

        recovered = start + datetime.timedelta(minutes=10)
        mock_datetime.datetime.now.return_value = recovered
        await device.on_success()

    assert device.diagnostic_data()["events"] == [
        {"time": recovered.isoformat(), "event": "recovered"},
        {"time": start.isoformat(), "event": "session_restart", "cause": "this_device"},
        {"time": start.isoformat(), "event": "timeouts_started"},
    ]
    assert device.diagnostic_data()["failing_since"] is None


async def test_health_changes_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Test that every decision about a failing device is visible in the info log."""
    caplog.set_level(logging.INFO, logger="roborock.mqtt.health_manager")
    health_manager = HealthManager(restart=AsyncMock())
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        mock_datetime.timedelta = datetime.timedelta
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        for _ in range(3):
            await working.on_success()
            await failing.on_timeout()

        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=1, seconds=10.4)
        await failing.on_success()

    messages = [record.getMessage() for record in caplog.records]
    assert [message.split(" ")[0] for message in messages] == ["Device", "Restarting", "Device"]
    assert "started timing out over MQTT" in messages[0]
    assert "may restart the session again in 0:30:00" in messages[1]
    assert "(last restart: never)" in messages[1]
    # Logs show how long the device was failing rather than a UTC timestamp.
    assert messages[2].endswith("responds over MQTT again after timing out for 0:01:10")


async def test_only_known_device_is_paced_like_any_failing_device() -> None:
    """Test that the restarts triggered by the only device of a session become rarer."""
    restart = AsyncMock()
    device = DeviceHealthManager(HealthManager(restart=restart), DEVICE_ID)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        for _ in range(3):
            await device.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        # The second restart is allowed after 30 minutes, the third only after another hour.
        now += datetime.timedelta(minutes=31)
        mock_datetime.datetime.now.return_value = now
        for _ in range(3):
            await device.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=45)
        for _ in range(3):
            await device.on_timeout()
        restart.assert_not_called()


async def test_concurrent_timeouts_restart_once() -> None:
    """Test that timeouts arriving while the session is restarting don't restart it again."""
    restarted = asyncio.Event()
    calls = 0

    async def slow_restart() -> None:
        nonlocal calls
        calls += 1
        await restarted.wait()

    health_manager = HealthManager(restart=slow_restart)
    failing = DeviceHealthManager(health_manager, "failing")
    await DeviceHealthManager(health_manager, "working").on_success()

    await failing.on_timeout()
    await failing.on_timeout()
    pending = [asyncio.create_task(failing.on_timeout()) for _ in range(5)]
    await asyncio.sleep(0)
    restarted.set()
    await asyncio.gather(*pending)

    assert calls == 1
    assert [event["event"] for event in failing.diagnostic_data()["events"]] == [
        "session_restart",
        "timeouts_started",
    ]


async def test_session_failure_is_recorded_on_every_device() -> None:
    """Test that a restart caused by several devices names them all as the cause."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    first = DeviceHealthManager(health_manager, "first")
    second = DeviceHealthManager(health_manager, "second")

    await first.on_timeout()
    await second.on_timeout()
    await first.on_timeout()

    restart.assert_called_once()
    for device in (first, second):
        assert device.diagnostic_data()["events"][0]["cause"] == "several_devices"


async def test_diagnostics_keep_only_recent_events() -> None:
    """Test that the event history of a device is bounded."""
    device = DeviceHealthManager(HealthManager(restart=AsyncMock()), DEVICE_ID)

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        for _ in range(MAX_DEVICE_EVENTS):
            mock_datetime.datetime.now.return_value = now
            await device.on_timeout()
            now += TIMEOUT_WINDOW
            mock_datetime.datetime.now.return_value = now
            await device.on_success()

    assert len(device.diagnostic_data()["events"]) == MAX_DEVICE_EVENTS


async def test_device_cooldown_applies_without_successes_from_other_devices() -> None:
    """Test that a failing device keeps its cooldown when other devices report nothing in between."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    failing = DeviceHealthManager(health_manager, "failing")
    working = DeviceHealthManager(health_manager, "working")

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        await working.on_success()

        for _ in range(3):
            await failing.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        now += datetime.timedelta(minutes=31)
        mock_datetime.datetime.now.return_value = now
        for _ in range(3):
            await failing.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        # Past the session cooldown, but only this device is failing and its own cooldown has grown.
        mock_datetime.datetime.now.return_value = now + datetime.timedelta(minutes=45)
        for _ in range(3):
            await failing.on_timeout()
        restart.assert_not_called()


async def test_timeouts_from_several_devices_bypass_device_cooldown() -> None:
    """Test that a session failing for several devices restarts during one device's cooldown."""
    restart = AsyncMock()
    health_manager = HealthManager(restart=restart)
    first = DeviceHealthManager(health_manager, "first")
    second = DeviceHealthManager(health_manager, "second")

    with patch("roborock.mqtt.health_manager.datetime") as mock_datetime:
        now = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = now
        await second.on_success()

        for _ in range(3):
            await first.on_timeout()
        restart.assert_called_once()
        restart.reset_mock()

        # The second device is failing too, so the session is restarted again.
        mock_datetime.datetime.now.return_value = now + datetime.timedelta(hours=1)
        await first.on_timeout()
        await second.on_timeout()
        restart.assert_not_called()

        await first.on_timeout()
        restart.assert_called_once()

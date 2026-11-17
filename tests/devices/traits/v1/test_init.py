"""Tests for the V1 trait properties API push handling."""

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.data import HomeData, HomeDataDevice, HomeDataProduct
from roborock.devices.cache import DeviceCache
from roborock.devices.traits import v1
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockDataProtocol

DpsListener = Callable[[dict[RoborockDataProtocol, Any]], None]

DELAY = 0.01
# Long enough for a read-back that should not happen to have run.
SETTLE = DELAY * 8
TIMEOUT = 1


@pytest.fixture(name="refresh_delay", autouse=True)
def refresh_delay_fixture(monkeypatch: pytest.MonkeyPatch) -> float:
    """Shorten the read-back delay so tests run quickly."""
    monkeypatch.setattr(v1, "_STATUS_REFRESH_DELAY", DELAY)
    return DELAY


@pytest.fixture(name="props")
async def props_fixture(
    device_info: HomeDataDevice,
    products: list[HomeDataProduct],
    trait_home_data: HomeData,
    device_cache: DeviceCache,
) -> AsyncIterator[tuple[v1.PropertiesApi, DpsListener]]:
    """Create a started properties API and the DPS listener it registered."""
    product = next(p for p in products if p.id == device_info.product_id)
    listeners: list[DpsListener] = []

    def add_dps_listener(listener: DpsListener) -> Callable[[], None]:
        listeners.append(listener)
        return Mock()

    api = v1.create(
        device_info.duid,
        product,
        trait_home_data,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        add_dps_listener,
        AsyncMock(),
        device_cache=device_cache,
    )
    api.discover_features = AsyncMock()  # type: ignore[method-assign]
    await api.start()
    yield api, listeners[0]
    api.close()


@pytest.fixture(name="read_back")
def read_back_fixture(props: tuple[v1.PropertiesApi, DpsListener]) -> asyncio.Event:
    """Mock the status read-back and return an event set each time it runs."""
    api, _ = props
    ran = asyncio.Event()

    async def refresh() -> None:
        ran.set()

    api.status.refresh_and_notify = AsyncMock(side_effect=refresh)  # type: ignore[method-assign]
    return ran


async def test_fan_and_water_push_reads_status_back(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """A fan power and water mode push triggers one status read-back."""
    api, push = props
    push({RoborockDataProtocol.FAN_POWER: 101, RoborockDataProtocol.WATER_BOX_MODE: 202})
    api.status.refresh_and_notify.assert_not_awaited()  # type: ignore[attr-defined]

    await asyncio.wait_for(read_back.wait(), timeout=TIMEOUT)
    await asyncio.sleep(SETTLE)
    api.status.refresh_and_notify.assert_awaited_once()  # type: ignore[attr-defined]


async def test_repeated_pushes_are_debounced(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """Several pushes before the delay elapses cause a single read-back."""
    api, push = props
    push({RoborockDataProtocol.FAN_POWER: 101})
    push({RoborockDataProtocol.WATER_BOX_MODE: 202})
    push({RoborockDataProtocol.FAN_POWER: 102})

    await asyncio.wait_for(read_back.wait(), timeout=TIMEOUT)
    await asyncio.sleep(SETTLE)
    api.status.refresh_and_notify.assert_awaited_once()  # type: ignore[attr-defined]


async def test_unrelated_push_does_not_read_back(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """Pushes without fan power or water mode do not refresh status."""
    api, push = props
    push({RoborockDataProtocol.BATTERY: 80})

    await asyncio.sleep(SETTLE)
    api.status.refresh_and_notify.assert_not_awaited()  # type: ignore[attr-defined]


async def test_refresh_failure_is_contained(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """A failing read-back does not raise and later pushes still read back."""
    api, push = props
    refresh = api.status.refresh_and_notify
    ran = asyncio.Event()

    async def failing_refresh() -> None:
        ran.set()
        raise RoborockException("boom")

    refresh.side_effect = failing_refresh  # type: ignore[attr-defined]
    push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.wait_for(ran.wait(), timeout=TIMEOUT)

    ran.clear()
    push({RoborockDataProtocol.FAN_POWER: 102})
    await asyncio.wait_for(ran.wait(), timeout=TIMEOUT)
    assert refresh.await_count == 2  # type: ignore[attr-defined]


async def test_close_cancels_pending_read_back(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """Closing while a read-back is pending prevents it from running."""
    api, push = props
    push({RoborockDataProtocol.FAN_POWER: 101})
    api.close()

    await asyncio.sleep(SETTLE)
    api.status.refresh_and_notify.assert_not_awaited()  # type: ignore[attr-defined]


async def test_close_cancels_in_flight_read_back(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """Closing while a read-back is running cancels it."""
    api, push = props
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def hanging_refresh() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    api.status.refresh_and_notify.side_effect = hanging_refresh  # type: ignore[attr-defined]
    push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.wait_for(started.wait(), timeout=TIMEOUT)

    api.close()
    await asyncio.wait_for(cancelled.wait(), timeout=TIMEOUT)
    api.status.refresh_and_notify.assert_awaited_once()  # type: ignore[attr-defined]


async def test_push_during_refresh_schedules_another(
    props: tuple[v1.PropertiesApi, DpsListener], read_back: asyncio.Event
) -> None:
    """A push arriving while a read-back is running is followed by another one."""
    api, push = props
    started = asyncio.Event()
    release = asyncio.Event()
    second_ran = asyncio.Event()
    calls = 0

    async def slow_refresh() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            second_ran.set()
            return
        started.set()
        await release.wait()

    api.status.refresh_and_notify.side_effect = slow_refresh  # type: ignore[attr-defined]
    push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.wait_for(started.wait(), timeout=TIMEOUT)

    push({RoborockDataProtocol.WATER_BOX_MODE: 202})
    release.set()

    await asyncio.wait_for(second_ran.wait(), timeout=TIMEOUT)
    assert calls == 2


async def test_read_back_notifies_status_listeners(props: tuple[v1.PropertiesApi, DpsListener]) -> None:
    """Status listeners hear about values changed by the read-back."""
    api, push = props
    changed = asyncio.Event()
    listener = Mock(side_effect=lambda: changed.set())
    api.status.add_update_listener(listener)

    async def refresh() -> None:
        api.status.mop_mode = 301

    api.status.refresh = AsyncMock(side_effect=refresh)  # type: ignore[method-assign]
    push({RoborockDataProtocol.WATER_BOX_MODE: 202})
    # The push itself notifies once; the read-back's change is the second call.
    changed.clear()

    await asyncio.wait_for(changed.wait(), timeout=TIMEOUT)
    assert api.status.mop_mode == 301
    assert listener.call_count == 2

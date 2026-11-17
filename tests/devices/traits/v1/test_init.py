"""Tests for the V1 trait properties API push handling."""

import asyncio
from collections.abc import Callable
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
# Long enough for any scheduled read-back to have run.
SETTLE = DELAY * 8


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
) -> Any:
    """Create a started properties API and expose its DPS listener as `props.push`."""
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
    api.status.refresh = AsyncMock()  # type: ignore[method-assign]
    await api.start()
    api.push = listeners[0]  # type: ignore[attr-defined]
    yield api
    api.close()


async def test_fan_and_water_push_reads_status_back(props: Any) -> None:
    """A fan power and water mode push triggers one status read-back."""
    props.push({RoborockDataProtocol.FAN_POWER: 101, RoborockDataProtocol.WATER_BOX_MODE: 202})
    props.status.refresh.assert_not_awaited()

    await asyncio.sleep(SETTLE)
    props.status.refresh.assert_awaited_once()


async def test_repeated_pushes_are_debounced(props: Any) -> None:
    """Several pushes before the delay elapses cause a single read-back."""
    props.push({RoborockDataProtocol.FAN_POWER: 101})
    props.push({RoborockDataProtocol.WATER_BOX_MODE: 202})
    props.push({RoborockDataProtocol.FAN_POWER: 102})

    await asyncio.sleep(SETTLE)
    props.status.refresh.assert_awaited_once()


async def test_unrelated_push_does_not_read_back(props: Any) -> None:
    """Pushes without fan power or water mode do not refresh status."""
    props.push({RoborockDataProtocol.BATTERY: 80})

    await asyncio.sleep(SETTLE)
    props.status.refresh.assert_not_awaited()


async def test_refresh_failure_is_contained(props: Any) -> None:
    """A failing read-back does not raise and later pushes still read back."""
    props.status.refresh.side_effect = RoborockException("boom")
    props.push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.sleep(SETTLE)
    assert props.status.refresh.await_count == 1

    props.push({RoborockDataProtocol.FAN_POWER: 102})
    await asyncio.sleep(SETTLE)
    assert props.status.refresh.await_count == 2


async def test_close_cancels_pending_read_back(props: Any) -> None:
    """Closing while a read-back is pending prevents it from running."""
    props.push({RoborockDataProtocol.FAN_POWER: 101})
    props.close()

    await asyncio.sleep(SETTLE)
    props.status.refresh.assert_not_awaited()


async def test_close_cancels_in_flight_read_back(props: Any) -> None:
    """Closing while a read-back is running cancels it."""
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def hanging_refresh() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    props.status.refresh.side_effect = hanging_refresh
    props.push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.wait_for(started.wait(), timeout=1)

    props.close()
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    props.status.refresh.assert_awaited_once()


async def test_push_during_refresh_schedules_another(props: Any) -> None:
    """A push arriving while a read-back is running is followed by another one."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_refresh() -> None:
        started.set()
        await release.wait()

    props.status.refresh.side_effect = slow_refresh
    props.push({RoborockDataProtocol.FAN_POWER: 101})
    await asyncio.wait_for(started.wait(), timeout=1)

    props.push({RoborockDataProtocol.WATER_BOX_MODE: 202})
    release.set()

    await asyncio.sleep(SETTLE)
    assert props.status.refresh.await_count == 2

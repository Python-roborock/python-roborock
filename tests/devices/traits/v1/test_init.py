"""Tests for the V1 trait properties API."""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.data import HomeData, HomeDataDevice, HomeDataProduct
from roborock.devices.cache import DeviceCache
from roborock.devices.traits import v1
from roborock.devices.traits.v1 import status as status_module
from roborock.roborock_message import RoborockDataProtocol

DELAY = 0.01


async def test_close_cancels_status_read_back(
    device_info: HomeDataDevice,
    products: list[HomeDataProduct],
    trait_home_data: HomeData,
    device_cache: DeviceCache,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing the properties API stops a status read-back that a push scheduled."""
    monkeypatch.setattr(status_module, "_STATUS_REFRESH_DELAY", DELAY)
    product = next(p for p in products if p.id == device_info.product_id)
    listeners: list[Callable[[dict[RoborockDataProtocol, Any]], None]] = []

    def add_dps_listener(listener: Callable[[dict[RoborockDataProtocol, Any]], None]) -> Callable[[], None]:
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
    api.status.refresh_and_notify = AsyncMock()  # type: ignore[method-assign]
    await api.start()

    listeners[0]({RoborockDataProtocol.FAN_POWER: 101})
    api.close()

    await asyncio.sleep(DELAY * 8)
    api.status.refresh_and_notify.assert_not_awaited()  # type: ignore[attr-defined]

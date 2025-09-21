"""Module for Roborock V1 devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import logging
from typing import Any

from roborock.containers import (
    HomeDataProduct,
    ModelStatus,
    S7MaxVStatus,
    Status,
)
from roborock.devices.v1_rpc_channel import V1RpcChannel
from roborock.roborock_typing import RoborockCommand

from .trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "StatusTrait",
]


class StatusTrait(Trait):
    """Trait for managing the status of Roborock devices."""

    name = "status"

    def __init__(self, product_info: HomeDataProduct, rpc_channel: V1RpcChannel) -> None:
        """Initialize the StatusTrait."""
        self._product_info = product_info
        self._rpc_channel = rpc_channel

    async def get_status(self) -> Status:
        """Get the current status of the device.

        This is a placeholder command and will likely be changed/moved in the future.
        """
        status_type: type[Status] = ModelStatus.get(self._product_info.model, S7MaxVStatus)
        status: dict[str, Any] | list = await self._rpc_channel.send_command(RoborockCommand.GET_STATUS)
        if isinstance(status, list):
            status = status[0]
        if not isinstance(status, dict):
            raise ValueError(f"Unexpected status format: {status!r}")
        return status_type.from_dict(status)

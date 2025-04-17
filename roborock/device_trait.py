import datetime
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from . import RoborockCommand
from .containers import Consumable, DeviceFeatures, DnDTimer, RoborockBase


@dataclass
class DeviceTrait(ABC):
    handle_command: RoborockCommand
    _status_type: type[RoborockBase] = RoborockBase

    def __init__(self, send_command: Callable[..., Awaitable[None]]):
        self.send_command = send_command
        self.status: RoborockBase | None = None
        self.subscriptions = []

    @classmethod
    @abstractmethod
    def supported(cls, features: DeviceFeatures) -> bool:
        raise NotImplementedError

    def on_message(self, data: dict) -> None:
        self.status = self._status_type.from_dict(data)
        for callback in self.subscriptions:
            callback(self.status)

    def subscribe(self, callable: Callable):
        # Maybe needs to handle async too?
        self.subscriptions.append(callable)

    @abstractmethod
    def get(self):
        raise NotImplementedError


class DndTrait(DeviceTrait):
    handle_command: RoborockCommand = RoborockCommand.GET_DND_TIMER
    _status_type: type[DnDTimer] = DnDTimer
    status: DnDTimer

    def __init__(self, send_command: Callable[..., Awaitable[None]]):
        super().__init__(send_command)

    @classmethod
    def supported(cls, features: DeviceFeatures) -> bool:
        return features.is_support_custom_dnd

    async def update_dnd(self, enabled: bool, start_time: datetime.time, end_time: datetime.time) -> None:
        if self.status.enabled and not enabled:
            await self.send_command(RoborockCommand.CLOSE_DND_TIMER)
        else:
            start = start_time if start_time is not None else self.status.start_time
            end = end_time if end_time is not None else self.status.end_time
            await self.send_command(RoborockCommand.SET_DND_TIMER, [start.hour, start.minute, end.hour, end.minute])

    async def get(self) -> None:
        await self.send_command(RoborockCommand.GET_DND_TIMER)


class ConsumableTrait(DeviceTrait):
    handle_command = RoborockCommand.GET_CONSUMABLE
    _status_type: type[Consumable] = DnDTimer
    status: Consumable

    def __init__(self, send_command: Callable[..., Awaitable[None]]):
        super().__init__(send_command)

    @classmethod
    def supported(cls, features: DeviceFeatures) -> bool:
        return True

    async def reset_consumable(self, consumable: str) -> None:
        await self.send_command(RoborockCommand.RESET_CONSUMABLE, [consumable])

    async def get(self) -> None:
        await self.send_command(RoborockCommand.GET_CONSUMABLE)

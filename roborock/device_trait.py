from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from . import RoborockCommand
from .containers import DeviceFeatures


@dataclass
class DeviceTrait(ABC):
    handle_command: RoborockCommand

    def __init__(self, send_command: Callable[..., Awaitable[None]]):
        self.send_command = send_command
        self.subscriptions = []

    @classmethod
    @abstractmethod
    def supported(cls, features: DeviceFeatures) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update(cls, data: dict) -> bool:
        raise NotImplementedError

    def on_message(self, data: dict) -> None:
        self.status = self.update(data)
        for callback in self.subscriptions:
            callback(self.status)

    def subscribe(self, callable: Callable):
        # Maybe needs to handle async too?
        self.subscriptions.append(callable)

    @abstractmethod
    def get(self):
        raise NotImplementedError


# class ConsumableTrait(DeviceTrait):
#     handle_command = RoborockCommand.GET_CONSUMABLE
#     _status_type: type[Consumable] = DnDTimer
#     status: Consumable
#
#     def __init__(self, send_command: Callable[..., Awaitable[None]]):
#         super().__init__(send_command)
#
#     @classmethod
#     def supported(cls, features: DeviceFeatures) -> bool:
#         return True
#
#     async def reset_consumable(self, consumable: str) -> None:
#         await self.send_command(RoborockCommand.RESET_CONSUMABLE, [consumable])
#
#     async def get(self) -> None:
#         await self.send_command(RoborockCommand.GET_CONSUMABLE)

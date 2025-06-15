import datetime
from collections.abc import Awaitable, Callable

from roborock import DeviceFeatures, DndActions, RoborockCommand
from roborock.device_trait import DeviceTrait


class Dnd(DeviceTrait):
    handle_command: RoborockCommand = RoborockCommand.GET_DND_TIMER

    def __init__(self, send_command: Callable[..., Awaitable[None]]):
        self.start_hour: int | None = None
        self.start_minute: int | None = None
        self.end_hour: int | None = None
        self.end_minute: int | None = None
        self.enabled: bool | None = None
        self.start_time: datetime.time | None = None
        self.end_time: datetime.time | None = None
        self.actions: DndActions | None = None
        super().__init__(send_command)

    def from_dict(self, dnd_dict: dict):
        self.start_hour = dnd_dict.get("start_hour")
        self.start_minute = dnd_dict.get("start_minute")
        self.end_hour = dnd_dict.get("end_hour")
        self.end_minute = dnd_dict.get("end_minute")
        self.enabled = bool(dnd_dict.get("enabled"))
        self.actions = DndActions.from_dict(dnd_dict.get("actions"))
        self.start_time = (
            datetime.time(hour=self.start_hour, minute=self.start_minute)
            if self.start_hour is not None and self.start_minute is not None
            else None
        )
        self.end_time = (
            datetime.time(hour=self.end_hour, minute=self.end_minute)
            if self.end_hour is not None and self.end_minute is not None
            else None
        )

    def to_dict(self) -> dict:
        return {}

    @classmethod
    def supported(cls, features: DeviceFeatures) -> bool:
        return features.is_support_custom_dnd

    async def update_dnd(self, enabled: bool, start_time: datetime.time, end_time: datetime.time) -> None:
        if self.enabled and not enabled:
            await self.send_command(RoborockCommand.CLOSE_DND_TIMER)
        else:
            start = start_time if start_time is not None else self.start_time
            end = end_time if end_time is not None else self.end_time
            await self.send_command(RoborockCommand.SET_DND_TIMER, [start.hour, start.minute, end.hour, end.minute])

    async def get(self) -> None:
        await self.send_command(RoborockCommand.GET_DND_TIMER)

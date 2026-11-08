from dataclasses import dataclass

from ..containers import RoborockBase


@dataclass
class DyadProductInfo(RoborockBase):
    sn: str
    ssid: str
    timezone: str
    posix_timezone: str
    ip: str
    mac: str
    oba: dict


@dataclass
class DyadSndState(RoborockBase):
    sid_in_use: int
    sid_version: int
    location: str
    bom: str
    language: str


@dataclass
class DyadScheduleTask(RoborockBase):
    """A task from the device schedule (DP 10002).

    `cron` uses the device's local time. On the F25 Ultra every task had the same
    `dp_action`, while the device ran nothing, drying, or self-clean and drying,
    so the action that will run cannot be inferred from `dp_action`.
    """

    id: int
    on: bool
    cron: str
    dp_action: dict[int, int]


@dataclass
class DyadOtaNfo(RoborockBase):
    mqttOtaData: dict

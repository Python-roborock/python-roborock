import dataclasses
import datetime
import json
import logging
import re
import types
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import cached_property
from typing import Any, NamedTuple, get_args, get_origin

from .code_mappings import (
    SHORT_MODEL_TO_ENUM,
    RoborockCategory,
    RoborockModeEnum,
    RoborockProductNickname,
)

_LOGGER = logging.getLogger(__name__)


def _camelize(s: str):
    first, *others = s.split("_")
    if len(others) == 0:
        return s
    return "".join([first.lower(), *map(str.title, others)])


def _decamelize(s: str):
    return re.sub("([A-Z]+)", "_\\1", s).lower()


def _attr_repr(obj: Any) -> str:
    """Return a string representation of the object including specified attributes.

    This reproduces the default repr behavior of dataclasses, but also includes
    properties. This must be called by the child class's __repr__ method since
    the parent RoborockBase class does not know about the child class's attributes.
    """
    # Reproduce default repr behavior
    parts = []
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except (RuntimeError, Exception):
            continue
        if callable(v):
            continue
        parts.append(f"{k}={v!r}")
    return f"{type(obj).__name__}({', '.join(parts)})"


@dataclass(repr=False)
class RoborockBase:
    """Base class for all Roborock data classes."""

    @staticmethod
    def _convert_to_class_obj(class_type: type, value):
        if get_origin(class_type) is list:
            sub_type = get_args(class_type)[0]
            return [RoborockBase._convert_to_class_obj(sub_type, obj) for obj in value]
        if get_origin(class_type) is dict:
            _, value_type = get_args(class_type)  # assume keys are only basic types
            return {k: RoborockBase._convert_to_class_obj(value_type, v) for k, v in value.items()}
        if issubclass(class_type, RoborockBase):
            return class_type.from_dict(value)
        if issubclass(class_type, RoborockModeEnum):
            return class_type.from_code(value)
        if class_type is Any:
            return value
        return class_type(value)  # type: ignore[call-arg]

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Create an instance of the class from a dictionary."""
        if not isinstance(data, dict):
            return None
        field_types = {field.name: field.type for field in dataclasses.fields(cls)}
        result: dict[str, Any] = {}
        for orig_key, value in data.items():
            key = _decamelize(orig_key)
            if (field_type := field_types.get(key)) is None:
                continue
            if value == "None" or value is None:
                result[key] = None
                continue
            if isinstance(field_type, types.UnionType):
                for subtype in get_args(field_type):
                    if subtype is types.NoneType:
                        continue
                    try:
                        result[key] = RoborockBase._convert_to_class_obj(subtype, value)
                        break
                    except Exception:
                        _LOGGER.exception(f"Failed to convert {key} with value {value} to type {subtype}")
                        continue
            else:
                try:
                    result[key] = RoborockBase._convert_to_class_obj(field_type, value)
                except Exception:
                    _LOGGER.exception(f"Failed to convert {key} with value {value} to type {field_type}")
                    continue

        return cls(**result)

    def as_dict(self) -> dict:
        return asdict(
            self,
            dict_factory=lambda _fields: {
                _camelize(key): value.value if isinstance(value, Enum) else value
                for (key, value) in _fields
                if value is not None
            },
        )


@dataclass
class RoborockBaseTimer(RoborockBase):
    start_hour: int | None = None
    start_minute: int | None = None
    end_hour: int | None = None
    end_minute: int | None = None
    enabled: int | None = None

    @property
    def start_time(self) -> datetime.time | None:
        return (
            datetime.time(hour=self.start_hour, minute=self.start_minute)
            if self.start_hour is not None and self.start_minute is not None
            else None
        )

    @property
    def end_time(self) -> datetime.time | None:
        return (
            datetime.time(hour=self.end_hour, minute=self.end_minute)
            if self.end_hour is not None and self.end_minute is not None
            else None
        )

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class Reference(RoborockBase):
    r: str | None = None
    a: str | None = None
    m: str | None = None
    l: str | None = None


@dataclass
class RRiot(RoborockBase):
    u: str
    s: str
    h: str
    k: str
    r: Reference


@dataclass
class UserData(RoborockBase):
    rriot: RRiot
    uid: int | None = None
    tokentype: str | None = None
    token: str | None = None
    rruid: str | None = None
    region: str | None = None
    countrycode: str | None = None
    country: str | None = None
    nickname: str | None = None
    tuya_device_state: int | None = None
    avatarurl: str | None = None


@dataclass
class HomeDataProductSchema(RoborockBase):
    id: Any | None = None
    name: Any | None = None
    code: Any | None = None
    mode: Any | None = None
    type: Any | None = None
    product_property: Any | None = None
    property: Any | None = None
    desc: Any | None = None


@dataclass
class HomeDataProduct(RoborockBase):
    id: str
    name: str
    model: str
    category: RoborockCategory
    code: str | None = None
    icon_url: str | None = None
    attribute: Any | None = None
    capability: int | None = None
    schema: list[HomeDataProductSchema] | None = None

    @property
    def product_nickname(self) -> RoborockProductNickname:
        return SHORT_MODEL_TO_ENUM.get(self.model.split(".")[-1], RoborockProductNickname.PEARLPLUS)


@dataclass
class HomeDataDevice(RoborockBase):
    duid: str
    name: str
    local_key: str
    fv: str
    product_id: str
    attribute: Any | None = None
    active_time: int | None = None
    runtime_env: Any | None = None
    time_zone_id: str | None = None
    icon_url: str | None = None
    lon: Any | None = None
    lat: Any | None = None
    share: Any | None = None
    share_time: Any | None = None
    online: bool | None = None
    pv: str | None = None
    room_id: Any | None = None
    tuya_uuid: Any | None = None
    tuya_migrated: bool | None = None
    extra: Any | None = None
    sn: str | None = None
    feature_set: str | None = None
    new_feature_set: str | None = None
    device_status: dict | None = None
    silent_ota_switch: bool | None = None
    setting: Any | None = None
    f: bool | None = None


@dataclass
class HomeDataRoom(RoborockBase):
    id: int
    name: str


@dataclass
class HomeDataScene(RoborockBase):
    id: int
    name: str


@dataclass
class HomeData(RoborockBase):
    id: int
    name: str
    products: list[HomeDataProduct] = field(default_factory=lambda: [])
    devices: list[HomeDataDevice] = field(default_factory=lambda: [])
    received_devices: list[HomeDataDevice] = field(default_factory=lambda: [])
    lon: Any | None = None
    lat: Any | None = None
    geo_name: Any | None = None
    rooms: list[HomeDataRoom] = field(default_factory=list)

    def get_all_devices(self) -> list[HomeDataDevice]:
        devices = []
        if self.devices is not None:
            devices += self.devices
        if self.received_devices is not None:
            devices += self.received_devices
        return devices

    @cached_property
    def product_map(self) -> dict[str, HomeDataProduct]:
        """Returns a dictionary of product IDs to HomeDataProduct objects."""
        return {product.id: product for product in self.products}

    @cached_property
    def device_products(self) -> dict[str, tuple[HomeDataDevice, HomeDataProduct]]:
        """Returns a dictionary of device DUIDs to HomeDataDeviceProduct objects."""
        product_map = self.product_map
        return {
            device.duid: (device, product)
            for device in self.get_all_devices()
            if (product := product_map.get(device.product_id)) is not None
        }


@dataclass
class LoginData(RoborockBase):
    user_data: UserData
    email: str
    home_data: HomeData | None = None


@dataclass
class DeviceData(RoborockBase):
    device: HomeDataDevice
    model: str
    host: str | None = None

    @property
    def product_nickname(self) -> RoborockProductNickname:
        return SHORT_MODEL_TO_ENUM.get(self.model.split(".")[-1], RoborockProductNickname.PEARLPLUS)

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class RoomMapping(RoborockBase):
    segment_id: int
    iot_id: str


@dataclass
class NamedRoomMapping(RoomMapping):
    """Dataclass representing a mapping of a room segment to a name.

    The name information is not provided by the device directly, but is provided
    from the HomeData based on the iot_id from the room.
    """

    name: str
    """The human-readable name of the room, if available."""


@dataclass
class CombinedMapInfo(RoborockBase):
    """Data structure for caching home information.

    This is not provided directly by the API, but is a combination of map data
    and room data to provide a more useful structure.
    """

    map_flag: int
    """The map identifier."""

    name: str
    """The name of the map from MultiMapsListMapInfo."""

    rooms: list[NamedRoomMapping]
    """The list of rooms in the map."""


@dataclass
class BroadcastMessage(RoborockBase):
    duid: str
    ip: str
    version: bytes


class ServerTimer(NamedTuple):
    id: str
    status: str
    dontknow: int


@dataclass
class RoborockProductStateValue(RoborockBase):
    value: list
    desc: dict


@dataclass
class RoborockProductState(RoborockBase):
    dps: int
    desc: dict
    value: list[RoborockProductStateValue]


@dataclass
class RoborockProductSpec(RoborockBase):
    state: RoborockProductState
    battery: dict | None = None
    dry_countdown: dict | None = None
    extra: dict | None = None
    offpeak: dict | None = None
    countdown: dict | None = None
    mode: dict | None = None
    ota_nfo: dict | None = None
    pause: dict | None = None
    program: dict | None = None
    shutdown: dict | None = None
    washing_left: dict | None = None


@dataclass
class RoborockProduct(RoborockBase):
    id: int | None = None
    name: str | None = None
    model: str | None = None
    packagename: str | None = None
    ssid: str | None = None
    picurl: str | None = None
    cardpicurl: str | None = None
    mediumCardpicurl: str | None = None
    resetwifipicurl: str | None = None
    configPicUrl: str | None = None
    pluginPicUrl: str | None = None
    resetwifitext: dict | None = None
    tuyaid: str | None = None
    status: int | None = None
    rriotid: str | None = None
    pictures: list | None = None
    ncMode: str | None = None
    scope: str | None = None
    product_tags: list | None = None
    agreements: list | None = None
    cardspec: str | None = None
    plugin_pic_url: str | None = None

    @property
    def product_nickname(self) -> RoborockProductNickname | None:
        if self.cardspec:
            return RoborockProductSpec.from_dict(json.loads(self.cardspec).get("data"))
        return None

    def __repr__(self) -> str:
        return _attr_repr(self)


@dataclass
class RoborockProductCategory(RoborockBase):
    id: int
    display_name: str
    icon_url: str


@dataclass
class RoborockCategoryDetail(RoborockBase):
    category: RoborockProductCategory
    product_list: list[RoborockProduct]


@dataclass
class ProductResponse(RoborockBase):
    category_detail_list: list[RoborockCategoryDetail]

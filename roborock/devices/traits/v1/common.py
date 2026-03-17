"""Module for Roborock V1 devices common trait commands.

This is an internal library and should not be used directly by consumers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import fields
from typing import ClassVar

from roborock.data import RoborockBase
from roborock.protocols.v1_protocol import V1RpcChannel
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)


V1ResponseData = dict | list | int | str


class V1TraitDataConverter(ABC):
    """Converts responses to RoborockBase objects.

    This is an internal class and should not be used directly by consumers.
    """

    @abstractmethod
    def convert(self, response: V1ResponseData) -> RoborockBase:
        """Convert the values to a dict that can be parsed as a RoborockBase."""

    def __repr__(self) -> str:
        return self.__class__.__name__


class V1TraitMixin(ABC):
    """Base model that supports v1 traits.

    This class provides functioanlity for parsing responses from V1 devices
    into dataclass instances. It also provides a reference to the V1RpcChannel
    used to communicate with the device to execute commands.

    Each trait subclass must define a class variable `command` that specifies
    the RoborockCommand used to fetch the trait data from the device. The
    `refresh()` method can be called to update the contents of the trait data
    from the device.

    A trait can also support additional commands for updating state associated
    with the trait. It is expected that a trait will update its own internal
    state either reflecting the change optimistically or by refreshing the
    trait state from the device. In cases where one trait caches data that is
    also represented in another trait, it is the responsibility of the caller
    to ensure that both traits are refreshed as needed to keep them in sync.

    The traits typically subclass RoborockBase to provide serialization
    and deserialization functionality, but this is not strictly required.
    """

    command: ClassVar[RoborockCommand]
    """The RoborockCommand used to fetch the trait data from the device (internal only)."""

    converter: V1TraitDataConverter
    """The converter used to parse the response from the device (internal only)."""

    def __init__(self) -> None:
        """Initialize the V1TraitMixin."""
        self._rpc_channel = None

    @property
    def rpc_channel(self) -> V1RpcChannel:
        """Helper for executing commands, used internally by the trait"""
        if not self._rpc_channel:
            raise ValueError("Device trait in invalid state")
        return self._rpc_channel

    async def refresh(self) -> None:
        """Refresh the contents of this trait."""
        response = await self.rpc_channel.send_command(self.command)
        new_data = self.converter.convert(response)
        merge_trait_values(self, new_data)  # type: ignore[arg-type]


def merge_trait_values(target: RoborockBase, new_object: RoborockBase) -> bool:
    """Update the target object with set fields in new_object."""
    updated = False
    for field in fields(new_object):
        old_value = getattr(target, field.name, None)
        new_value = getattr(new_object, field.name, None)
        if new_value != old_value:
            setattr(target, field.name, new_value)
            updated = True
    return updated


class DefaultConverter(V1TraitDataConverter):
    """Converts responses to RoborockBase objects."""

    def __init__(self, dataclass_type: type[RoborockBase]) -> None:
        """Initialize the converter."""
        self._dataclass_type = dataclass_type

    def convert(self, response: V1ResponseData) -> RoborockBase:
        """Convert the values to a dict that can be parsed as a RoborockBase.

        Subclasses can override to implement custom parsing logic
        """
        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"Unexpected {self._dataclass_type.__name__} response format: {response!r}")
        return self._dataclass_type.from_dict(response)


class SingleValueConverter(DefaultConverter):
    """Base class for traits that represent a single value.

    This class is intended to be subclassed by traits that represent a single
    value, such as volume or brightness. The subclass should define a single
    field with the metadata `roborock_value=True` to indicate which field
    represents the main value of the trait.
    """

    def __init__(self, dataclass_type: type[RoborockBase], value_field: str) -> None:
        """Initialize the converter."""
        super().__init__(dataclass_type)
        self._value_field = value_field

    def convert(self, response: V1ResponseData) -> RoborockBase:
        """Parse the response from the device into a RoborockValueBase."""
        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, int):
            raise ValueError(f"Unexpected response format: {response!r}")
        return super().convert({self._value_field: response})


class RoborockSwitchBase(ABC):
    """Base class for traits that represent a boolean switch."""

    @property
    @abstractmethod
    def is_on(self) -> bool:
        """Return whether the switch is on."""

    @abstractmethod
    async def enable(self) -> None:
        """Enable the switch."""

    @abstractmethod
    async def disable(self) -> None:
        """Disable the switch."""


def mqtt_rpc_channel(cls):
    """Decorator to mark a function as cloud only.

    Normally a trait uses an adaptive rpc channel that can use either local
    or cloud communication depending on what is available. This will force
    the trait to always use the cloud rpc channel.
    """

    def wrapper(*args, **kwargs):
        return cls(*args, **kwargs)

    cls.mqtt_rpc_channel = True  # type: ignore[attr-defined]
    return wrapper


def map_rpc_channel(cls):
    """Decorator to mark a function as cloud only using the map rpc format."""

    def wrapper(*args, **kwargs):
        return cls(*args, **kwargs)

    cls.map_rpc_channel = True  # type: ignore[attr-defined]
    return wrapper

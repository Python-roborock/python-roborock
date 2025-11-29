"""Module for Roborock V1 devices common trait commands.

This is an internal library and should not be used directly by consumers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import ClassVar, Self

from roborock.data import RoborockBase
from roborock.protocols.v1_protocol import V1RpcChannel
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)

V1ResponseData = dict | list | int | str


@dataclass
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

    @classmethod
    def _parse_type_response(cls, response: V1ResponseData) -> RoborockBase:
        """Parse the response from the device into a a RoborockBase.

        Subclasses should override this method to implement custom parsing
        logic as needed.
        """
        if not issubclass(cls, RoborockBase):
            raise NotImplementedError(f"Trait {cls} does not implement RoborockBase")
        # Subclasses can override to implement custom parsing logic
        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"Unexpected {cls} response format: {response!r}")
        return cls.from_dict(response)

    def _parse_response(self, response: V1ResponseData) -> RoborockBase:
        """Parse the response from the device into a a RoborockBase.

        This is used by subclasses that want to override the class
        behavior with instance-specific data.
        """
        return self._parse_type_response(response)

    def __post_init__(self) -> None:
        """Post-initialization to set up the RPC channel.

        This is called automatically after the dataclass is initialized by the
        device setup code.
        """
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
        new_data = self._parse_response(response)
        if not isinstance(new_data, RoborockBase):
            raise ValueError(f"Internal error, unexpected response type: {new_data!r}")
        _LOGGER.debug("Refreshed %s: %s", self.__class__.__name__, new_data)
        self._update_trait_values(new_data)

    def _update_trait_values(self, new_data: RoborockBase) -> None:
        """Update the values of this trait from another instance."""
        for field in fields(new_data):
            new_value = getattr(new_data, field.name, None)
            setattr(self, field.name, new_value)


def _get_value_field(clazz: type[V1TraitMixin]) -> str:
    """Get the name of the field marked as the main value of the RoborockValueBase."""
    value_fields = [field.name for field in fields(clazz) if field.metadata.get("roborock_value", False)]
    if len(value_fields) != 1:
        raise ValueError(
            f"RoborockValueBase subclass {clazz} must have exactly one field marked as roborock_value, "
            f" but found: {value_fields}"
        )
    return value_fields[0]


@dataclass(init=False, kw_only=True)
class RoborockValueBase(V1TraitMixin, RoborockBase):
    """Base class for traits that represent a single value.

    This class is intended to be subclassed by traits that represent a single
    value, such as volume or brightness. The subclass should define a single
    field with the metadata `roborock_value=True` to indicate which field
    represents the main value of the trait.
    """

    @classmethod
    def _parse_response(cls, response: V1ResponseData) -> Self:
        """Parse the response from the device into a RoborockValueBase."""
        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, int):
            raise ValueError(f"Unexpected response format: {response!r}")
        value_field = _get_value_field(cls)
        return cls(**{value_field: response})


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

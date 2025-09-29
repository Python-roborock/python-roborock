"""Module for device traits."""

from abc import ABC

__all__ = [
    "Trait",
    "traits_mixin",
    "v1",
    "a01",
    "b01",
]


class Trait(ABC):
    """Base class for all traits."""

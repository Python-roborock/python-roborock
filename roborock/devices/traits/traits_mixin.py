"""Holds device traits mixin and related code.

This holds the TraitsMixin class, which is used to provide accessors for
various device traits. Each trait is a class that encapsulates a specific
set of functionality for a device, such as controlling a vacuum or a mop.

The TraitsMixin holds traits across all protocol types. A trait is supported
if it is non-None.
"""

from dataclasses import dataclass, fields
from typing import get_args, get_origin

from . import Trait, a01, b01, v1

__all__ = [
    "TraitsMixin",
]


@dataclass(init=False)
class TraitsMixin:
    """Mixin to provide trait accessors."""

    v1_properties: v1.PropertiesApi | None = None
    """V1 properties trait, if supported."""

    dyad: a01.DyadApi | None = None
    """Dyad API, if supported."""

    zeo: a01.ZeoApi | None = None
    """Zeo API, if supported."""

    b01_q7_properties: b01.Q7PropertiesApi | None = None
    """B01 Q7 properties trait, if supported."""

    def __init__(self, trait: Trait) -> None:
        """Initialize the TraitsMixin with the given trait.

        This will populate the appropriate trait attributes based on the types
        of the traits provided.
        """
        for item in fields(self):
            trait_type = _get_trait_type(item)
            if trait_type is type(trait):
                setattr(self, item.name, trait)
                break


def _get_trait_type(item) -> type[Trait]:
    """Get the trait type from a dataclass field."""
    if get_origin(item.type) is None:
        raise ValueError(f"Trait {item.name} is not an optional type")
    if (args := get_args(item.type)) is None:
        raise ValueError(f"Trait {item.name} is not an optional type")
    if len(args) != 2 or args[1] is not type(None):
        raise ValueError(f"Trait {item.name} is not an optional type")
    trait_type = args[0]
    if not issubclass(trait_type, Trait):
        raise ValueError(f"Trait {item.name} is not a Trait subclass")
    return trait_type

"""Module for device traits.

This package contains the trait definitions for different device protocols supported
by Roborock devices.

Submodules
----------
*   `v1`: Contains traits for standard Roborock vacuums (e.g., S-series, Q-series).
    These devices use the V1 protocol and have rich feature sets split into
    granular traits (e.g., `StatusTrait`, `ConsumableTrait`).
*   `a01`: Contains APIs for A01 protocol devices, such as the Dyad (wet/dry vacuum)
    and Zeo (washing machine). These devices use a different communication structure.
*   `b01`: Contains APIs for B01 protocol devices.
"""

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

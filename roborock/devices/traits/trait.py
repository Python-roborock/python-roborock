"""Trait module for Roborock devices."""

from abc import ABC


class Trait(ABC):
    """API for interacting with Roborock devices."""

    name: str
    """Name of the API."""

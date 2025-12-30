"""Traits for B01 devices."""

from . import q7, q10
from .q7 import Q7PropertiesApi
from .q10 import Q10PropertiesApi

__all__ = [
    "Q7PropertiesApi",
    "Q10PropertiesApi",
    "q7",
    "q10",
]

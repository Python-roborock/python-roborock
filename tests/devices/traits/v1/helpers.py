"""Shared helpers for V1 trait tests."""

from roborock.data import RoborockDockTypeCode
from roborock.device_features import RoborockDockFeatures


def dock_types_with_capability(capability: str, expected: bool = True) -> list[RoborockDockTypeCode]:
    """Return dock types matching a RoborockDockFeatures capability."""
    return [
        dock_type
        for dock_type in RoborockDockTypeCode
        if getattr(RoborockDockFeatures.from_dock_type(dock_type), capability) is expected
    ]

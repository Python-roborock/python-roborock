"""Common utilities for Q10 traits.

This module provides infrastructure for mapping Roborock Data Points (DPS) to
Python dataclass fields and handling the lifecycle of data updates from the
device.
"""

import dataclasses
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import RoborockBase


class DpsDataConverter:
    """Utility to handle the transformation and merging of DPS data into models."""

    def __init__(self, dps_type_map: dict[B01_Q10_DP, type], dps_field_map: dict[B01_Q10_DP, str]):
        """Initialize the converter for a specific RoborockBase-derived class."""
        self._dps_type_map = dps_type_map
        self._dps_field_map = dps_field_map

    @classmethod
    def from_dataclass(cls, dataclass_type: type[RoborockBase]):
        """Initialize the converter for a specific RoborockBase-derived class."""
        dps_type_map: dict[B01_Q10_DP, type] = {}
        dps_field_map: dict[B01_Q10_DP, str] = {}
        for field_obj in dataclasses.fields(dataclass_type):
            if field_obj.metadata and "dps" in field_obj.metadata:
                dps_id = field_obj.metadata["dps"]
                dps_type_map[dps_id] = field_obj.type
                dps_field_map[dps_id] = field_obj.name
        return cls(dps_type_map, dps_field_map)

    def update_from_dps(self, target: RoborockBase, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Convert and merge raw DPS data into the target object."""
        conversions = RoborockBase.convert_dict(self._dps_type_map, decoded_dps)
        for dps_id, value in conversions.items():
            field_name = self._dps_field_map[dps_id]
            setattr(target, field_name, value)

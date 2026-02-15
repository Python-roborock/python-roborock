"""Common utilities for Q10 traits.

This module provides infrastructure for mapping Roborock Data Points (DPS) to
Python dataclass fields and handling the lifecycle of data updates from the
device.

### DPS Metadata Annotation

Classes extending `RoborockBase` can annotate their fields with DPS IDs using
the `field(metadata={"dps": ...})` convention. This creates a declarative
mapping that `DpsDataConverter` uses to automatically route incoming device
data to the correct attribute.

Example:

```python
@dataclass
class MyStatus(RoborockBase):
    battery: int = field(metadata={"dps": B01_Q10_DP.BATTERY})
```

### Update Lifecycle
1. **Raw Data**: The device sends encoded DPS updates over MQTT.
2. **Decoding**: The transport layer decodes these into a dictionary (e.g., `{"101": 80}`).
3. **Conversion**: `DpsDataConverter` uses `RoborockBase.convert_dict` to transform
   raw values into appropriate Python types (e.g., Enums, ints) based on the
   dataclass field types.
4. **Update**: `update_from_dps` maps these converted values to field names and
   updates the target object using `setattr`.

### Usage

Typically, a trait will instantiate a single `DpsDataConverter` for its status class
and call `update_from_dps` whenever new data is received from the device stream.

"""

import dataclasses
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import RoborockBase


class DpsDataConverter:
    """Utility to handle the transformation and merging of DPS data into models.

    This class pre-calculates the mapping between Data Point IDs and dataclass fields
    to optimize repeated updates from device streams.
    """

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
        """Convert and merge raw DPS data into the target object.

        Uses the pre-calculated type mapping to ensure values are converted to the
        correct Python types before being updated on the target.

        Args:
            target: The target object to update.
            decoded_dps: The decoded DPS data to convert.
        """
        conversions = RoborockBase.convert_dict(self._dps_type_map, decoded_dps)
        for dps_id, value in conversions.items():
            field_name = self._dps_field_map[dps_id]
            setattr(target, field_name, value)

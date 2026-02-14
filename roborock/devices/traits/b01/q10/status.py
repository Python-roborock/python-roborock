"""Status trait for Q10 B01 devices."""

from roborock.data.b01_q10.b01_q10_containers import Q10Status

from .common import DpsDataConverter

_CONVERTER = DpsDataConverter.from_dataclass(Q10Status)


class StatusTrait(Q10Status):
    """Trait for managing the status of Q10 Roborock devices.

    This is a thin wrapper around Q10Status that provides the Trait interface.
    The current values reflect the most recently received data from the device.
    New values can be requested through the `Q10PropertiesApi` refresh method.
    """

    def update_from_dps(self, decoded_dps: dict) -> None:
        """Update the trait from raw DPS data."""
        _CONVERTER.update_from_dps(self, decoded_dps)

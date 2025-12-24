"""Common functionality for Q10 traits."""

from abc import ABC
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, TypeAlias

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.b01_q10_channel import send_b01_dp_command
from roborock.devices.mqtt_channel import MqttChannel

Q10DpsValueConverter: TypeAlias = Callable[[Any], Any]
Q10DpsFieldSpec: TypeAlias = str | tuple[str, Q10DpsValueConverter]
Q10DpsFieldMap: TypeAlias = Mapping[B01_Q10_DP, Q10DpsFieldSpec]


@dataclass
class Q10TraitMixin(ABC):
    """Base mixin for Q10 traits."""

    # Note: We can potentially experiment with extracting this map upward and knowing what DP go to what
    # trait to avoid having to call all of them.
    dps_field_map: ClassVar[Q10DpsFieldMap | None] = None
    """Optional mapping of DP enum -> attribute (and optional converter).

    If set on a trait class, `update_from_dps()` will automatically apply
    updates from incoming DP payloads.
    """

    def __post_init__(self) -> None:
        """Initialize the Q10 trait."""
        self._channel: MqttChannel | None = None

    def set_channel(self, channel: MqttChannel) -> None:
        """Bind this trait to a MQTT channel.

        Q10 traits are also used as state containers; we keep construction
        decoupled from transport and inject the channel at the API composition
        layer.
        """
        self._channel = channel

    @property
    def channel(self) -> MqttChannel:
        """Get the MQTT channel."""
        if self._channel is None:
            raise ValueError("Channel not set on Q10 trait")
        return self._channel

    def update_from_dps(self, dps: dict[int, Any]) -> None:
        """Update this trait's state from a DP payload."""
        mapping = self.dps_field_map
        if not mapping:
            return

        for dp, spec in mapping.items():
            if dp.code not in dps:
                continue

            value = dps[dp.code]
            if isinstance(spec, tuple):
                attr, converter = spec
                value = converter(value)
            else:
                attr = spec
            setattr(self, attr, value)

    async def send_dp(self, dp: B01_Q10_DP, value: Any) -> None:
        """Send a direct DP write (no response expected)."""
        await send_b01_dp_command(
            self.channel,
            {dp.code: value},
        )

    async def send_public(self, dp: B01_Q10_DP, value: Any) -> None:
        """Send a public command wrapped in DP 101 (dpCommon) (no response expected)."""
        await send_b01_dp_command(
            self.channel,
            {B01_Q10_DP.COMMON.code: {str(dp.code): value}},
        )

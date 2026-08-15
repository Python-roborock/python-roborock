"""Zeo command trait"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from roborock.data.zeo.zeo_containers import (
    ZeoCustomMode,
    ZeoDryerCustomMode,
    ZeoStartParams,
)
from roborock.devices.rpc.a01_channel import send_decoded_command
from roborock.devices.traits.a01.settings import FeaturesFn, build_param_dps
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.mqtt.session import MqttQos
from roborock.roborock_message import RoborockZeoProtocol

if TYPE_CHECKING:
    from roborock.devices.traits.a01.settings import ZeoSettingTrait

CustomModeFn = Callable[[], Awaitable[ZeoCustomMode | ZeoDryerCustomMode | None]]

_FEATURE_GATED_DPS: dict[RoborockZeoProtocol, tuple[str, str]] = {
    RoborockZeoProtocol.ION_DEODORIZATION: ("ion_deodorization", "ion_deodorization"),
    RoborockZeoProtocol.WASH_DRY_LINKED: ("wash_dry_linkage", "wash_dry_linked"),
}

class ZeoCommandTrait:
    """Trait for sending commands to Zeo devices."""

    def __init__(
        self,
        *,
        channel: MqttChannel,
        settings: Callable[[], "ZeoSettingTrait"],
        features: FeaturesFn,
        custom_mode: CustomModeFn,
    ) -> None:
        """Initialize the command trait.

        ``settings`` returns the shared :class:`ZeoSettingTrait` holding typed
        device state (the single source of truth for auto-dosing and
        feature-gated values). ``features`` returns the (lazily loaded) feature
        bits. ``custom_mode`` reads and decodes the device's saved custom
        programme (DP 222) for :meth:`start_with_custom_mode`.
        """

        self._channel = channel
        self._settings = settings
        self._features = features
        self._custom_mode = custom_mode

    async def start_with(self, params: ZeoStartParams) -> dict[RoborockZeoProtocol, Any]:
        """Start the device with the given programme parameters.

        This is the primary start API: the caller needs to provide the 
        parameters like mode/program/options/etc.

        Returns the DPs that were actually sent.
        """
        dps: dict[RoborockZeoProtocol, Any] = {RoborockZeoProtocol.START: 1}
        dps.update(build_param_dps(params))
        dps.update(self._build_auto_dosing_dps())
        dps.update(self._build_feature_gated_dps(params))
        await send_decoded_command(
            self._channel,
            dps,
            qos=MqttQos.AT_LEAST_ONCE,
            value_encoder=lambda x: x,
        )
        return dps

    def _build_auto_dosing_dps(self) -> dict[RoborockZeoProtocol, Any]:
        """Map the settings' auto-dosing toggles to wire DPs (211/212).

        Both values are integers 1/0;
        ``None`` (e.g. dryers) is omitted.
        """
        settings = self._settings()
        dps: dict[RoborockZeoProtocol, Any] = {}
        if settings.auto_detergent is not None:
            dps[RoborockZeoProtocol.DETERGENT_SET] = 1 if settings.auto_detergent else 0
        if settings.auto_softener is not None:
            dps[RoborockZeoProtocol.SOFTENER_SET] = 1 if settings.auto_softener else 0
        return dps

    def _build_feature_gated_dps(
        self, params: ZeoStartParams, *, include_wash_dry_linked: bool = True
    ) -> dict[RoborockZeoProtocol, Any]:
        """Map caller-supplied feature-gated booleans to wire DPs (255/258).

        The value comes from ``params`` (the programme's config
        ``defaultIonStatus`` / UI ``wash_dry_linked`` state), not from the
        device's echo; ``None`` omits the DP. The feature bit only gates
        whether the DP is sent at all.

        ``include_wash_dry_linked`` defaults to True for ``startWith``.
        """
        features = self._features()
        dps: dict[RoborockZeoProtocol, Any] = {}
        for dp, (feature_name, field_name) in _FEATURE_GATED_DPS.items():
            if dp is RoborockZeoProtocol.WASH_DRY_LINKED and not include_wash_dry_linked:
                continue
            if features is not None and getattr(features, feature_name, False):
                value = getattr(params, field_name)
                if value is not None:
                    dps[dp] = 1 if value else 0
        return dps

    async def start_with_custom_mode(self) -> dict[RoborockZeoProtocol, Any]:
        """Start the device using its saved custom programme.

        Reads the device's custom programme (DP 222, see
        :meth:`ZeoApi.get_custom_mode`) and starts with those parameters. 

        Raises :class:`ValueError` when the device has no saved custom
        programme.
        """
        custom = await self._custom_mode()
        if custom is None:
            raise ValueError("Device has no saved custom programme (DP 222)")
        params = _custom_mode_to_start_params(custom)
        return await self.start_with(params)

    async def preset_with(self, params: ZeoStartParams, minutes: int) -> dict[RoborockZeoProtocol, Any]:
        """Schedule a delayed start with full programme parameters.

        ``COUNTDOWN`` (DP 217) is the **last** DP in the payload,
        and its value is the integer number of minutes.

        When *minutes* is ``<= 0`` only ``COUNTDOWN=0`` is sent to cancel an
        existing schedule (the sole case that is a single-DP command).

        Device behavior note: a ``COUNTDOWN`` value **> 30** is required to
        enter the delay-start countdown state. Smaller values (e.g. 20) cause
        the machine to start immediately instead. The caller is responsible
        for ensuring *minutes* satisfies this constraint.

        Returns the DPs that were sent.
        """
        if minutes <= 0:
            dps: dict[RoborockZeoProtocol, Any] = {RoborockZeoProtocol.COUNTDOWN: 0}
            await send_decoded_command(
                self._channel,
                dps,
                qos=MqttQos.AT_LEAST_ONCE,
                value_encoder=lambda x: x,
            )
            return dps
        dps: dict[RoborockZeoProtocol, Any] = {RoborockZeoProtocol.START: 1}
        dps.update(build_param_dps(params))
        dps.update(self._build_auto_dosing_dps())
        dps.update(self._build_feature_gated_dps(params, include_wash_dry_linked=False))
        dps[RoborockZeoProtocol.COUNTDOWN] = minutes
        await send_decoded_command(
            self._channel,
            dps,
            qos=MqttQos.AT_LEAST_ONCE,
            value_encoder=lambda x: x,
        )
        return dps

    async def pause(self) -> dict[RoborockZeoProtocol, Any]:
        """Pause the current programme (DP 201 = 1).

        Returns the DPs that were actually sent.
        """
        dps = {RoborockZeoProtocol.PAUSE: 1}
        await send_decoded_command(self._channel, dps)
        return dps

    async def resume(self) -> dict[RoborockZeoProtocol, Any]:
        """Start/continue a paused programme (DP 200 = 1).

        Only works while the device is powered on. Returns the DPs sent.
        """
        dps = {RoborockZeoProtocol.START: 1}
        await send_decoded_command(self._channel, dps)
        return dps

    async def stop(self) -> dict[RoborockZeoProtocol, Any]:
        """Stop the current programme (DP 200 = 0)."""
        dps = {RoborockZeoProtocol.START: 0}
        await send_decoded_command(self._channel, dps)
        return dps

    async def shutdown(self) -> dict[RoborockZeoProtocol, Any]:
        """Power off the device (DP 202 = 1).

        Only works while the device is powered on. Returns the DPs sent.
        """
        dps = {RoborockZeoProtocol.SHUTDOWN: 1}
        await send_decoded_command(self._channel, dps)
        return dps


def _custom_mode_to_start_params(
    custom: ZeoCustomMode | ZeoDryerCustomMode,
) -> ZeoStartParams:
    """Convert a decoded custom programme into :class:`ZeoStartParams`.

    Washer and dryer custom modes carry the same fields (program, mode,
    drying_mode, drying_method, steam_volume) plus wash-only fields
    (temperature, rinse, spin, soak, dry_and_care) on the washer layout.
    ``total_time_min`` maps to ``total_time`` (the timed-program duration).
    """
    return ZeoStartParams(
        mode=custom.mode,
        program=custom.program,
        temperature=getattr(custom, "temperature", None),
        rinse=getattr(custom, "rinse", None),
        spin=getattr(custom, "spin", None),
        drying_mode=custom.drying_mode,
        drying_method=getattr(custom, "drying_method", None),
        steam_volume=custom.steam_volume,
        total_time=custom.total_time_min or None,
        soak=getattr(custom, "soak", None),
        dry_and_care=getattr(custom, "dry_and_care", None),
    )

"""Programme-config driven START parameter validation for Zeo appliances.

Every ``(mode, program)`` pair — and the START parameters each one accepts — is
described by the device's *mode data module*.  A device resolves to exactly one
such module, including the fixed ``total_time`` of its programmes, so there is
no device-independent programme table: resolve it with
:func:`roborock.data.zeo.resolve_data_module`, then index it here by
``(mode, program)`` to validate or default a set of START parameters before
sending them.

The structures below are resolved read-only tables.  They are intentionally
plain (non-frozen) dataclasses with :class:`RoborockBase` inheritance, as
required for every domain model in ``roborock.data`` by the conformance suite
(``tests/conformance/test_model_conformance.py``); a frozen dataclass cannot
inherit from the non-frozen ``RoborockBase``.
"""

from dataclasses import dataclass
from functools import cache
from typing import Any

from ..containers import RoborockBase
from .mode_templates import ZeoModeConfig, ZeoModeTemplate, ZeoParamConfig, ZeoTimeOptions, build_mode_templates
from .zeo_code_mappings import ZeoMode, ZeoProgram
from .zeo_containers import ZeoStartParams

__all__ = [
    "ZeoProgramSupports",
    "ZeoProgramConfig",
    "get_program_config",
    "all_program_configs",
    "program_configs",
    "validate_start_params",
    "default_start_params",
]


@dataclass
class ZeoProgramSupports(RoborockBase):
    """Per-programme capability flags from the mode data."""

    reservation: bool
    auto_detergent: bool
    auto_softener: bool
    uvc: bool


@dataclass
class ZeoProgramConfig(RoborockBase):
    """Resolved mode entry for one ``(mode, program)`` pair of one device.

    A ``None`` parameter means the programme does not accept that parameter at
    all (e.g. drying programmes have no ``temperature``).  Each
    :class:`ZeoParamConfig` exposes the accepted levels as protocol enum
    members plus the physical display values behind them.
    """

    mode_id: int
    mode: ZeoMode
    program: ZeoProgram
    priority: int
    program_name: str
    """The programme's name as recorded in the mode data.

    It is stored in Chinese and is not a display string; use :attr:`program`
    (a :class:`ZeoProgram` member) as the stable identifier instead.
    """
    is_in_app: bool
    supports: ZeoProgramSupports
    temperature: ZeoParamConfig | None = None
    rinse: ZeoParamConfig | None = None
    spin: ZeoParamConfig | None = None
    drying_mode: ZeoParamConfig | None = None
    soak: ZeoParamConfig | None = None
    dry_and_care: ZeoParamConfig | None = None
    dry_method: ZeoParamConfig | None = None
    steam_volume: ZeoParamConfig | None = None

    # Timed-programme durations (minutes).  At most one of the option groups is
    # set for a given programme; ``total_time`` is the resolved duration
    # (DP 234) to send when the caller does not pick one.
    smart_time: ZeoTimeOptions | None = None
    timed_program_time: ZeoTimeOptions | None = None
    timed_drying: ZeoTimeOptions | None = None
    total_time: int | None = None


def _parse(template: ZeoModeTemplate) -> ZeoProgramConfig:
    """Turn a resolved mode template into a :class:`ZeoProgramConfig`."""
    config: ZeoModeConfig = template.config
    return ZeoProgramConfig(
        mode_id=template.id,
        mode=template.program_type,
        program=template.dp,
        priority=template.priority,
        program_name=template.program_name,
        is_in_app=template.is_in_app,
        supports=ZeoProgramSupports(
            reservation=config.is_support_reservation,
            auto_detergent=config.is_support_auto_detergent,
            auto_softener=config.is_support_auto_softener,
            uvc=config.is_support_uvc,
        ),
        temperature=config.temperature,
        rinse=config.rinse,
        spin=config.spin,
        drying_mode=config.drying_mode,
        soak=config.soak,
        dry_and_care=config.dry_and_care,
        dry_method=config.dry_method,
        steam_volume=config.steam_volume,
        smart_time=config.smart_time,
        timed_program_time=config.timed_program_time,
        timed_drying=config.timed_drying,
        total_time=config.total_time,
    )


@cache
def program_configs(module_id: int) -> tuple[ZeoProgramConfig, ...]:
    """The programme table of one data module, parsed on first use.

    ``module_id`` comes from :func:`roborock.data.zeo.resolve_data_module`.
    """
    return tuple(_parse(template) for template in build_mode_templates(module_id))


@cache
def _by_mode_program(module_id: int) -> dict[tuple[ZeoMode, ZeoProgram], ZeoProgramConfig]:
    """Index of a module's configs by ``(mode, program)``."""
    return {(config.mode, config.program): config for config in program_configs(module_id)}


def get_program_config(mode: ZeoMode, program: ZeoProgram, *, module_id: int) -> ZeoProgramConfig | None:
    """Return the resolved configuration for a ``(mode, program)`` pair.

    Returns ``None`` when the pair is not present in that device's table.
    """
    return _by_mode_program(module_id).get((mode, program))


def all_program_configs(mode: ZeoMode, *, module_id: int) -> list[ZeoProgramConfig]:
    """Return every program configuration for the given mode."""
    return [config for config in program_configs(module_id) if config.mode == mode]


# :class:`ZeoStartParams` attributes that can be validated, paired with the
# :class:`ZeoProgramConfig` attribute that carries their levels.  The names
# differ where the start parameter is named after its DP
# (``ZeoStartParams.drying_method`` → ``RoborockZeoProtocol.DRYING_METHOD``)
# while the mode data names it after the programme field (``dry_method``).
# Keeping the mapping explicit means a rename on either side cannot silently
# disable a check.
_VALIDATED_FIELDS: tuple[tuple[str, str], ...] = (
    ("temperature", "temperature"),
    ("rinse", "rinse"),
    ("spin", "spin"),
    ("drying_mode", "drying_mode"),
    ("soak", "soak"),
    ("dry_and_care", "dry_and_care"),
    ("drying_method", "dry_method"),
    ("steam_volume", "steam_volume"),
)


@cache
def _modelled_fields(module_id: int) -> frozenset[str]:
    """The :class:`ZeoProgramConfig` attributes this device's table models.

    A parameter that no entry in the device's table exposes is not modelled for
    it (``soak``, ``dry_and_care``, ``dry_method`` and ``steam_volume`` on some
    models, for example).  Treating its absence as "unsupported" would reject
    perfectly valid values, so it is skipped.
    """
    return frozenset(
        config_field
        for _, config_field in _VALIDATED_FIELDS
        if any(getattr(config, config_field) is not None for config in program_configs(module_id))
    )


def _duration_options(config: ZeoProgramConfig) -> ZeoTimeOptions | None:
    """The selectable durations for a programme, if it lists any.

    Ordered as the duration is resolved: ``smart_time`` → ``timed_drying`` →
    ``timed_program_time``.  A given programme only ever carries one of them.
    """
    for group in (config.smart_time, config.timed_drying, config.timed_program_time):
        if group is not None:
            return group
    return None


def _resolved_total_time(config: ZeoProgramConfig) -> int | None:
    """The duration (DP 234) to send for a programme.

    Resolved mode data carries a fixed ``total_time``; a config built from a
    duration list alone falls back to that list's default.  Both paths live
    here so the value used by the default and the list checked by the validator
    cannot drift apart.
    """
    if config.total_time is not None:
        return config.total_time
    durations = _duration_options(config)
    return durations.default if durations is not None else None


def validate_start_params(
    params: ZeoStartParams,
    *,
    module_id: int,
    config: ZeoProgramConfig | None = None,
) -> list[str]:
    """Validate START params against a programme configuration.

    Returns a list of human-readable error strings; an empty list means the
    params are valid.

    Semantics:

    * ``module_id`` is the device's data module
      (:func:`roborock.data.zeo.resolve_data_module`); the table a parameter is
      judged against is the one that device actually uses.
    * A ``None`` param and an enum member whose int value is ``0`` are
      treated as "not set" and skipped, matching the send path (zero-valued
      empty enum members are not emitted by ``build_param_dps``).
    * When ``config`` is omitted it is resolved from ``params.mode`` and
      ``params.program``.  If no configuration exists (pair absent from that
      device's table), no validation is performed and an empty list is
      returned; the caller decides whether to trust the input.
    * A parameter the table does not model at all is not checked either (see
      :func:`_modelled_fields`).  A parameter the table *does* model is always
      checked, even when the passed ``config`` leaves it unset.
    * ``total_time`` (DP 234) is checked against the programme's selectable
      durations when it lists any; durations of ``0`` are "not set".
    """
    if config is None:
        config = get_program_config(params.mode, params.program, module_id=module_id)
    if config is None:
        return []
    modelled = _modelled_fields(module_id)
    errors: list[str] = []
    for param_field, config_field in _VALIDATED_FIELDS:
        param: ZeoParamConfig | None = getattr(config, config_field)
        if param is None and config_field not in modelled:
            # The table never exposes this parameter, so its absence here says
            # nothing about the programme.
            continue
        value = getattr(params, param_field)
        if value is None or int(value) == 0:
            continue
        if param is None or not param.support:
            errors.append(
                f"{param_field}={int(value)} is not supported by programme "
                f"{config.program.name!r} (mode {config.mode.name})"
            )
        elif value not in param.support:
            supported = ", ".join(level.name for level in param.support)
            errors.append(
                f"{param_field}={int(value)} is not supported by programme "
                f"{config.program.name!r}; supported levels: {supported}"
            )
    durations = _duration_options(config)
    if durations is not None and params.total_time and params.total_time not in durations.support:
        supported = ", ".join(str(value) for value in durations.support)
        errors.append(
            f"total_time={params.total_time} is not supported by programme "
            f"{config.program.name!r}; supported durations: {supported}"
        )
    return errors


def default_start_params(
    mode: ZeoMode,
    program: ZeoProgram,
    *,
    module_id: int,
    config: ZeoProgramConfig | None = None,
) -> ZeoStartParams:
    """Build START params with every supported parameter at its default.

    Parameters without a configured default (or without a range at all) are
    left unset.  ``total_time`` (DP 234) is derived from the programme's
    duration config rather than passed by the caller, so callers do not have to
    know whether the programme is timed.  The result is a valid input for
    ``start_with``.

    ``module_id`` is the device's data module
    (:func:`roborock.data.zeo.resolve_data_module`); ``config`` defaults to that
    device's entry for ``(mode, program)``.  Pass one explicitly to override it
    (see :func:`validate_start_params`).
    """
    if config is None:
        config = get_program_config(mode, program, module_id=module_id)
    kwargs: dict[str, Any] = {"mode": mode, "program": program}
    if config is not None:
        for param_field, config_field in _VALIDATED_FIELDS:
            param: ZeoParamConfig | None = getattr(config, config_field)
            if param is None or param.default is None:
                continue
            kwargs[param_field] = param.default
        if (total_time := _resolved_total_time(config)) is not None:
            kwargs["total_time"] = total_time
    return ZeoStartParams(**kwargs)

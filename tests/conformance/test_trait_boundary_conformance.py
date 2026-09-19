"""Conformance tests for trait boundary purity.

As defined in AGENTS.md, Traits receive only abstract communication channels
(e.g., `Channel`, `RpcChannel`) or domain models/feature flags. They must NEVER
accept raw transport sockets, IP addresses, credentials, local keys, or AES encryption keys.
"""

from __future__ import annotations

import asyncio
import inspect
import socket
import typing

import pytest

import roborock.devices.traits
from roborock.devices.traits import Trait
from roborock.devices.traits.v1.common import V1TraitMixin
from roborock.devices.transport.local_channel import LocalChannel, LocalChannelParams
from roborock.devices.transport.mqtt_channel import MqttParams, MqttSession
from tests.conformance.discovery import discover_classes, to_pytest_params

FORBIDDEN_PARAMS = {
    "local_key",
    "token",
    "ip",
    "ip_address",
    "host",
    "socket",
    "transport",
    "aes_key",
    "password",
    "secret",
    "key",
}

FORBIDDEN_TYPES = (
    socket.socket,
    asyncio.BaseTransport,
    LocalChannel,
    LocalChannelParams,
    MqttParams,
    MqttSession,
)


def _extract_types(annotation: typing.Any) -> set[type]:
    """Recursively extract underlying concrete types from type hints and unions."""
    if isinstance(annotation, type):
        return {annotation}
    args = typing.get_args(annotation)
    types_found: set[type] = set()
    for arg in args:
        types_found |= _extract_types(arg)
    return types_found


def _is_trait_class(cls: type) -> bool:
    if cls in (Trait, V1TraitMixin):
        return False
    return issubclass(cls, (Trait, V1TraitMixin)) or cls.__name__.endswith(("Trait", "Api"))


@pytest.mark.parametrize(
    "trait_cls",
    to_pytest_params(discover_classes(roborock.devices.traits, _is_trait_class)),
)
def test_trait_constructor_does_not_leak_transport_or_credentials(trait_cls: type) -> None:
    """Trait constructor parameters must never include transport sockets, IPs, or credentials."""
    sig = inspect.signature(trait_cls)
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "args", "kwargs"):
            continue

        assert param_name not in FORBIDDEN_PARAMS, (
            f"{trait_cls.__module__}.{trait_cls.__name__}.__init__ accepts forbidden transport/credential "
            f"parameter '{param_name}'. Per AGENTS.md, traits must receive only abstract channels or domain models."
        )

        types_found = _extract_types(param.annotation)
        for t in types_found:
            assert not issubclass(t, FORBIDDEN_TYPES), (
                f"{trait_cls.__module__}.{trait_cls.__name__}.__init__ accepts parameter '{param_name}' "
                f"typed with forbidden low-level transport/credential class {t.__name__}. "
                "Traits must depend only on abstract channels (e.g. Channel, RpcChannel)."
            )

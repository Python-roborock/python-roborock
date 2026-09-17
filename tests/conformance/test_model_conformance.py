"""Conformance tests for data model inheritance.

As defined in AGENTS.md, structured domain and wire models in `roborock.data`
MUST inherit from `RoborockBase` to ensure standard `as_dict()` serialization
and `from_dict()` deserialization across consumers.
"""

from __future__ import annotations

import pytest

import roborock.data
from roborock.data.containers import RoborockBase
from tests.conformance.discovery import discover_dataclasses, to_pytest_params


@pytest.mark.parametrize(
    "model_cls",
    to_pytest_params(discover_dataclasses(roborock.data)),
)
def test_data_model_subclasses_roborock_base(model_cls: type) -> None:
    """All domain dataclasses in roborock.data must inherit from RoborockBase."""
    assert issubclass(model_cls, RoborockBase), (
        f"{model_cls.__module__}.{model_cls.__name__} is a dataclass but does not inherit from RoborockBase. "
        "Per AGENTS.md, domain containers must subclass RoborockBase for serialization."
    )

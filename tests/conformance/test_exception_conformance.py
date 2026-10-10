"""Conformance tests for exception hierarchy.

As defined in AGENTS.md, all custom exceptions in python-roborock MUST inherit
from `roborock.exceptions.RoborockException` so downstream consumers (such as
Home Assistant Core) can reliably catch and handle library errors without crashing.
"""

from __future__ import annotations

import pytest

import roborock
from roborock.exceptions import RoborockException
from tests.conformance.discovery import discover_subclasses, to_pytest_params


@pytest.mark.parametrize(
    "exception_cls",
    to_pytest_params(discover_subclasses(roborock, BaseException, exclude=(BaseException, Exception))),
)
def test_all_custom_exceptions_inherit_from_roborock_exception(exception_cls: type[BaseException]) -> None:
    """Every custom exception defined in roborock must inherit from RoborockException."""
    assert issubclass(exception_cls, RoborockException), (
        f"{exception_cls.__module__}.{exception_cls.__name__} does not inherit from RoborockException. "
        "All library exceptions must inherit from RoborockException per AGENTS.md."
    )

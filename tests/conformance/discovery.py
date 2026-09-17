"""Shared discovery utilities for repository conformance tests."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import types
from collections.abc import Callable, Iterator
from dataclasses import is_dataclass
from functools import lru_cache
from typing import Any

import pytest


@lru_cache(maxsize=8)
def walk_modules(package: types.ModuleType) -> list[types.ModuleType]:
    """Recursively walk and import all modules within a package, caching the result."""
    modules: list[types.ModuleType] = [package]
    if not hasattr(package, "__path__"):
        return modules
    for _, modname, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        modules.append(importlib.import_module(modname))
    return modules


def discover_classes(
    package: types.ModuleType,
    predicate: Callable[[type], bool],
    module_prefix: str | None = None,
) -> list[type]:
    """Discover all unique classes within a package that satisfy a given predicate."""
    prefix = module_prefix or package.__name__
    seen: set[type] = set()
    result: list[type] = []
    for mod in walk_modules(package):
        if not mod.__name__.startswith(prefix):
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if not obj.__module__.startswith(prefix):
                continue
            if obj in seen:
                continue
            if predicate(obj):
                seen.add(obj)
                result.append(obj)
    return result


def discover_subclasses(
    package: types.ModuleType,
    base_class: type | tuple[type, ...],
    exclude: tuple[type, ...] = (),
    module_prefix: str | None = None,
) -> list[type]:
    """Discover all unique subclasses of base_class in a package, excluding specific classes."""
    return discover_classes(
        package,
        predicate=lambda cls: issubclass(cls, base_class) and cls not in exclude,
        module_prefix=module_prefix,
    )


def discover_dataclasses(
    package: types.ModuleType,
    module_prefix: str | None = None,
) -> list[type]:
    """Discover all unique dataclasses defined within a package."""
    return discover_classes(
        package,
        predicate=is_dataclass,
        module_prefix=module_prefix,
    )


def to_pytest_params(
    classes: list[type],
    marks_by_fqn: dict[str, pytest.MarkDecorator] | None = None,
) -> Iterator[Any]:
    """Convert a list of classes to parametrized pytest.param objects with fully-qualified IDs."""
    marks_map = marks_by_fqn or {}
    for cls in classes:
        fqn = f"{cls.__module__}.{cls.__name__}"
        if fqn in marks_map:
            yield pytest.param(cls, id=fqn, marks=marks_map[fqn])
        else:
            yield pytest.param(cls, id=fqn)

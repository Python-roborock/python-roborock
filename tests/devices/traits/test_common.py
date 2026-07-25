"""Tests for common trait utilities."""

from dataclasses import dataclass, field
from enum import IntEnum

from roborock.data import RoborockBase
from roborock.devices.traits.common import DpsDataConverter


class FakeDps(IntEnum):
    """Data points for the test model."""

    VALUE = 1


@dataclass
class FakeData(RoborockBase):
    """Small data model for converter tests."""

    value: int | None = field(default=None, metadata={"dps": FakeDps.VALUE})


def test_update_from_dps_reports_only_value_changes() -> None:
    """The converter reports a change only when the target value changes."""
    converter = DpsDataConverter.from_dataclass(FakeData)
    target = FakeData()

    assert converter.update_from_dps(target, {FakeDps.VALUE: 1})
    assert not converter.update_from_dps(target, {FakeDps.VALUE: 1})
    assert converter.update_from_dps(target, {FakeDps.VALUE: 2})

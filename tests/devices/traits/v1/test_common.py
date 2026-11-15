from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from roborock.data.containers import RoborockBase
from roborock.devices.traits.v1.common import DefaultConverter, SingleValueConverter, V1TraitMixin
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand


@dataclass
class FakeTraitData(RoborockBase):
    """Arbitrary data container for testing purposes."""

    fake_field: int | None = None
    other_field: str | None = None


class FakeTrait(FakeTraitData, V1TraitMixin):
    """Arbitrary trait for testing purposes."""

    _rpc_channel: AsyncMock

    # Arbitrary command used for testing.
    command = RoborockCommand.APP_GET_INIT_STATUS

    def __init__(self):
        super().__init__()
        self._rpc_channel = AsyncMock()
        self.converter = DefaultConverter(FakeTraitData)


async def test_fake_trait_bad_payload() -> None:
    """Test that parsing a bad payload throws a helpful parsing error."""
    trait = FakeTrait()
    trait._rpc_channel.send_command.return_value = ["abc"]

    with pytest.raises(
        RoborockParsingException,
        match=r"Failed to parse APP_GET_INIT_STATUS response for FakeTrait. Payload: .*ValueError.*",
    ):
        await trait.refresh()


async def test_valid_payload() -> None:
    """Test that a valid payload is parsed successfully into trait fields."""
    trait = FakeTrait()
    trait._rpc_channel.send_command.return_value = [{"fake_field": 123, "other_field": "abc"}]
    await trait.refresh()
    assert trait.fake_field == 123
    assert trait.other_field == "abc"


async def test_empty_list_payload_keeps_state() -> None:
    """An empty list raises a parsing error and keeps the previous values."""
    trait = FakeTrait()
    trait._rpc_channel.send_command.return_value = [{"fake_field": 123, "other_field": "abc"}]
    await trait.refresh()
    trait._rpc_channel.send_command.return_value = []

    with pytest.raises(
        RoborockParsingException,
        match=r"Failed to parse APP_GET_INIT_STATUS response for FakeTrait. Payload: \[\].*ValueError.*",
    ):
        await trait.refresh()

    assert trait.fake_field == 123
    assert trait.other_field == "abc"


def test_single_value_converter_empty_list() -> None:
    """The single-value converter rejects an empty list with ValueError."""
    converter = SingleValueConverter(FakeTraitData, "fake_field")

    with pytest.raises(ValueError, match="Empty FakeTraitData response"):
        converter.convert([])

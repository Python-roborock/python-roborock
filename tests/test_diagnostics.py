"""Tests for diagnostics module."""

import pytest

from roborock.diagnostics import Diagnostics, redact_device_uid, redact_topic_name


def test_empty_diagnostics():
    """Test that a new Diagnostics object is empty."""

    diag = Diagnostics()
    assert diag.as_dict() == {}


def test_increment_counter():
    """Test incrementing counters in Diagnostics."""

    diag = Diagnostics()
    diag.increment("test_event")
    diag.increment("test_event", 2)

    assert diag.as_dict() == {"test_event": 3}


def test_elapsed_timing():
    """Test elapsed timing in Diagnostics."""

    diag = Diagnostics()
    with diag.timer("test_operation"):
        pass  # Simulate operation

    data = diag.as_dict()
    assert data["test_operation_count"] == 1
    assert data["test_operation_sum"] >= 0

    with diag.timer("test_operation"):
        pass  # Simulate operation

    data = diag.as_dict()
    assert data["test_operation_count"] == 2
    assert data["test_operation_sum"] >= 0


def test_subkey_diagnostics():
    """Test subkey diagnostics in Diagnostics."""

    diag = Diagnostics()
    sub_diag = diag.subkey("submodule")
    sub_diag.increment("sub_event", 5)

    expected = {"submodule": {"sub_event": 5}}
    assert diag.as_dict() == expected


def test_reset_diagnostics():
    """Test resetting diagnostics."""

    diag = Diagnostics()
    diag.increment("event", 10)
    sub_diag = diag.subkey("submodule")
    sub_diag.increment("sub_event", 5)

    assert diag.as_dict() == {"event": 10, "submodule": {"sub_event": 5}}

    diag.reset()

    assert diag.as_dict() == {}


@pytest.mark.parametrize(
    "topic,expected",
    [
        (
            "rr/m/o/1DuR4nbBzz3OPbv0NNamVP/b8632r9e/3zQRtuIfY14BrRTivxxcMd",
            "rr/m/o/1DuR4nbBzz3OPbv0NNamVP/*****32r9e/*****xxcMd",
        ),
        ("rr/m/o/1DuR4nbBzz3OPbv0NNamVP//3zQRtuIfY14BrRTivxxcMd", "rr/m/o/1DuR4nbBzz3OPbv0NNamVP/*****/*****xxcMd"),
        ("rr/m/o//b8632r9e/3zQRtuIfY14BrRTivxxcMd", "rr/m/o//*****32r9e/*****xxcMd"),
        ("roborock/short/updates", "roborock/short/updates"),  # Too short to redact
    ],
)
def test_redact_topic_name(topic: str, expected: str) -> None:
    """Test redacting sensitive information from topic names."""

    redacted = redact_topic_name(topic)
    assert redacted == expected


@pytest.mark.parametrize(
    "duid,expected",
    [
        ("3zQRtuIfY14BrRTivxxcMd", "******xxcMd"),
        ("3zQ", "******3zQ"),
        ("", "******"),
    ],
)
def test_redact_device(duid: str, expected: str) -> None:
    """Test redacting sensitive information from device UIDs."""

    redacted = redact_device_uid(duid)
    assert redacted == expected

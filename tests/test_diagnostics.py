"""Tests for diagnostics module."""

from roborock.diagnostics import Diagnostics


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

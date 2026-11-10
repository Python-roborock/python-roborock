"""Tests for diagnostics module."""

import json
from typing import Any

import pytest

from roborock.diagnostics import REDACTED, Diagnostics, redact_device_data, redact_device_uid, redact_topic_name


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


def test_redact_q10_raw_room_name() -> None:
    """Custom Q10 room labels are private in exported diagnostics."""
    assert redact_device_data(
        {"map": {"rooms": [{"rawName": "Owner’s bedroom"}], "currentRoom": {"rawName": "Salle d’eau"}}}
    ) == {"map": {"rooms": [{"rawName": REDACTED}], "currentRoom": {"rawName": REDACTED}}}


def test_redact_iot_room_name() -> None:
    """Room names reported in the map list are as private as raw room names."""
    assert redact_device_data({"rooms": [{"iotName": "Owner’s bedroom", "tag": 1}]}) == {
        "rooms": [{"iotName": REDACTED, "tag": 1}]
    }


def test_redact_json_string_in_device_status() -> None:
    """Identifiers inside a data point that holds a JSON string are redacted."""
    product_info = json.dumps(
        {
            "sn": "TESTSERIAL",
            "ssid": "test-network",
            "ip": "192.0.2.1",
            "mac": "00:00:5e:00:53:01",
            "rssi": -53,
            "oba": {"bom": "A.01"},
        }
    )

    redacted = redact_device_data({"device": {"deviceStatus": {"10005": product_info, "209": 100}}})

    status: dict[str, Any] = redacted["device"]["deviceStatus"]
    assert status["209"] == 100
    assert json.loads(status["10005"]) == {
        "sn": REDACTED,
        "ssid": REDACTED,
        "ip": REDACTED,
        "mac": REDACTED,
        "rssi": -53,
        "oba": {"bom": "A.01"},
    }


def test_redact_json_string_in_list() -> None:
    """JSON strings inside lists are redacted too."""
    redacted = redact_device_data({"items": ['{"ip": "192.0.2.1"}', "plain"]})

    assert redacted["items"] == [json.dumps({"ip": REDACTED}), "plain"]


@pytest.mark.parametrize(
    "value",
    [
        "plain text",
        "",
        '{"RRPhotoPrivacyVersion":   "1"}',  # Not sensitive, so the formatting is kept
        "[1, 2, 3]",
    ],
)
def test_redact_keeps_strings_without_sensitive_data(value: str) -> None:
    """Strings with nothing to redact are returned unchanged."""
    assert redact_device_data({"value": value}) == {"value": value}


def test_redact_unparsable_json_string() -> None:
    """A string that looks like JSON but cannot be checked is fully redacted."""
    assert redact_device_data({"value": '{"sn": "TESTSERIAL"'}) == {"value": REDACTED}

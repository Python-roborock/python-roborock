"""Tests for camera signaling parsing, hashing, and wire payload serialization."""

import base64
import binascii
import json
from typing import Any

import pytest

from roborock.data.camera import CameraIceCandidate, CameraSdpDescription
from roborock.exceptions import RoborockException, RoborockParsingException
from roborock.protocols.camera_signaling import (
    decode_ice_candidates,
    decode_sdp_answer,
    encode_ice_candidate,
    encode_sdp_offer,
    hash_camera_password,
    parse_ice_candidate,
)
from roborock.roborock_typing import RoborockCommand

HOST_CANDIDATE = "candidate:4234997325 1 udp 2122260223 192.168.1.100 54321 typ host"


def encode_wire_json(payload: Any) -> str:
    """Encode a dynamic device payload independently from the signaling encoder."""
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def test_parse_ice_candidate_host_udp() -> None:
    """Parse the standard host candidate and its media identifiers."""
    candidate = parse_ice_candidate(HOST_CANDIDATE, sdp_mid="video", sdp_mline_index=1)

    assert candidate == CameraIceCandidate(
        foundation="4234997325",
        component=1,
        protocol="udp",
        priority=2122260223,
        ip="192.168.1.100",
        port=54321,
        candidate_type="host",
        sdp_mid="video",
        sdp_mline_index=1,
    )
    assert candidate.to_sdp() == HOST_CANDIDATE


@pytest.mark.parametrize(
    ("candidate_string", "expected"),
    [
        (
            "candidate:123456 1 udp 1686052607 203.0.113.1 54321 typ srflx raddr 192.168.1.100 rport 54321",
            CameraIceCandidate(
                foundation="123456",
                component=1,
                protocol="udp",
                priority=1686052607,
                ip="203.0.113.1",
                port=54321,
                candidate_type="srflx",
                related_address="192.168.1.100",
                related_port=54321,
            ),
        ),
        (
            "candidate:789012 1 udp 33562367 198.51.100.2 3478 typ relay raddr 203.0.113.1 rport 54321",
            CameraIceCandidate(
                foundation="789012",
                component=1,
                protocol="udp",
                priority=33562367,
                ip="198.51.100.2",
                port=3478,
                candidate_type="relay",
                related_address="203.0.113.1",
                related_port=54321,
            ),
        ),
        (
            "candidate:345678 1 tcp 1518280447 192.168.1.100 9 typ host tcptype active",
            CameraIceCandidate(
                foundation="345678",
                component=1,
                protocol="tcp",
                priority=1518280447,
                ip="192.168.1.100",
                port=9,
                candidate_type="host",
                tcp_type="active",
            ),
        ),
    ],
)
def test_parse_ice_candidate_types(candidate_string: str, expected: CameraIceCandidate) -> None:
    """Preserve related address and TCP attributes when parsing and serializing."""
    candidate = parse_ice_candidate(candidate_string)

    assert candidate == expected
    assert candidate.to_sdp() == candidate_string


@pytest.mark.parametrize("address", ["2001:db8::1", "d79c09bf-323e-4610-8f92-5eb3fa7e4a1a.local"])
def test_parse_ice_candidate_addresses(address: str) -> None:
    """Support IPv6 and mDNS names without changing the address."""
    candidate_string = f"candidate:1 1 udp 2122260223 {address} 50000 typ host"
    candidate = parse_ice_candidate(candidate_string)

    assert candidate.ip == address
    assert candidate.to_sdp() == candidate_string


@pytest.mark.parametrize("prefix", ["", "candidate:", "a=candidate:"])
def test_parse_ice_candidate_prefixes_and_extensions(prefix: str) -> None:
    """Allow SDP prefixes and CRLF while preserving extension attributes."""
    candidate = parse_ice_candidate(f"{prefix}1 1 UDP 100 1.2.3.4 5000 typ HOST generation 0 network-id 1\r\n")

    assert candidate.foundation == "1"
    assert candidate.protocol == "udp"
    assert candidate.candidate_type == "host"
    assert candidate.extensions == {"generation": "0", "network-id": "1"}


@pytest.mark.parametrize("component", [1, 256])
@pytest.mark.parametrize("priority", [1, 2147483647])
@pytest.mark.parametrize("port", [0, 65535])
def test_parse_ice_candidate_numeric_bounds(component: int, priority: int, port: int) -> None:
    """Accept the inclusive component, priority, and port limits."""
    candidate = parse_ice_candidate(f"candidate:1 {component} udp {priority} 1.1.1.1 {port} typ host")

    assert candidate.component == component
    assert candidate.priority == priority
    assert candidate.port == port


@pytest.mark.parametrize(
    ("candidate_string", "message"),
    [
        ("", "Empty ICE candidate"),
        (" \r\n", "Empty ICE candidate"),
        ("candidate:1 1 udp", "expected at least 8 tokens"),
        ("candidate:1 0 udp 100 1.1.1.1 200 typ host", "RFC 8839 range"),
        ("candidate:1 257 udp 100 1.1.1.1 200 typ host", "RFC 8839 range"),
        ("candidate:1 +1 udp 100 1.1.1.1 200 typ host", "ASCII decimal digits"),
        ("candidate:1 １ udp 100 1.1.1.1 200 typ host", "ASCII decimal digits"),
        ("candidate:1 1 udp 0 1.1.1.1 200 typ host", "RFC 8445 range"),
        ("candidate:1 1 udp 2147483648 1.1.1.1 200 typ host", "RFC 8445 range"),
        ("candidate:1 1 udp 1_000 1.1.1.1 200 typ host", "ASCII decimal digits"),
        (f"candidate:{'a' * 33} 1 udp 100 1.1.1.1 200 typ host", "Invalid ICE foundation"),
        ("candidate:invalid@char 1 udp 100 1.1.1.1 200 typ host", "Invalid ICE foundation"),
        ("candidate:1 1 udp 100 1.1.1.1 -1 typ host", "ASCII decimal digits"),
        ("candidate:1 1 udp 100 1.1.1.1 65536 typ host", "port.*out of valid range"),
        ("candidate:1 1 udp 100 1.1.1.1 200 other host", "expected 'typ' keyword"),
        ("candidate:1 1 udp 100 1.1.1.1 200 typ host dangling_token", "odd number of tokens"),
        ("candidate:1 1 tcp 100 1.1.1.1 9 typ host", "TCP ICE candidate must specify 'tcptype'"),
        ("candidate:1 1 tcp 100 1.1.1.1 9 typ host tcptype invalid", "Invalid ICE TCP type"),
        ("candidate:1 1 udp 100 1.1.1.1 200 typ srflx raddr 2.2.2.2", "must have both 'raddr' and 'rport'"),
        ("candidate:1 1 udp 100 1.1.1.1 200 typ srflx rport 5000", "must have both 'raddr' and 'rport'"),
        ("candidate:1 1 udp 100 1.1.1.1 200 typ srflx raddr 2.2.2.2 rport x", "ASCII decimal digits"),
        ("candidate:1 1 udp 100 1.1.1.1 200 typ srflx raddr 2.2.2.2 rport 65536", "port.*out of valid range"),
    ],
)
def test_parse_ice_candidate_invalid_values(candidate_string: str, message: str) -> None:
    """Reject invalid candidate values and RFC invariant violations."""
    with pytest.raises(ValueError, match=message):
        parse_ice_candidate(candidate_string)


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("1234", "81dc9bdb52d04dc20036dbd8313ed055"),
        ("9876", "912e79cd13c64069d91da65d62fbb78c"),
        ("0123", "eb62f6b9306db575c2d596b1279627a4"),
        (" 1234 ", "81dc9bdb52d04dc20036dbd8313ed055"),
    ],
)
def test_hash_camera_password_valid(password: str, expected: str) -> None:
    """Hash ASCII PIN digits, preserving leading zeros and trimming whitespace."""
    assert hash_camera_password(password) == expected


@pytest.mark.parametrize("password", ["", "   ", "12a4", "１２３４", "password", "12 34"])
def test_hash_camera_password_invalid(password: str) -> None:
    """Reject empty passwords and non-ASCII PIN digits."""
    with pytest.raises(ValueError):
        hash_camera_password(password)


def test_hash_camera_password_error_redacts_password() -> None:
    """Keep invalid camera passwords out of error messages and logs."""
    password = "private-camera-password"
    with pytest.raises(ValueError) as error:
        hash_camera_password(password)

    assert password not in str(error.value)


def test_encode_sdp_offer_preserves_crlf() -> None:
    """Package the exact SDP string and the offer type as base64 JSON."""
    sdp = "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"

    assert json.loads(base64.b64decode(encode_sdp_offer(sdp))) == {"sdp": sdp, "type": "offer"}


@pytest.mark.parametrize("sdp", ["", "   ", "\r\n"])
def test_encode_sdp_offer_empty(sdp: str) -> None:
    """Reject an offer without SDP content."""
    with pytest.raises(ValueError, match="cannot be empty"):
        encode_sdp_offer(sdp)


@pytest.mark.parametrize("answer_type", ["answer", "pranswer", "ANSWER", "PRANSWER"])
def test_decode_sdp_answer_supported_formats(answer_type: str) -> None:
    """Return a typed description from each supported device response envelope."""
    sdp = "v=0\r\no=- 67890 2 IN IP4 127.0.0.1\r\ns=-\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
    description = {"sdp": sdp, "type": answer_type}
    encoded = encode_wire_json(description)
    expected = CameraSdpDescription(sdp=sdp, type=answer_type.lower())

    assert decode_sdp_answer(encoded) == expected
    assert decode_sdp_answer({"dev_sdp": encoded}) == expected
    assert decode_sdp_answer([{"dev_sdp": encoded}]) == expected
    assert decode_sdp_answer(description) == expected


def test_decode_sdp_answer_default_type() -> None:
    """Use the answer type when it is absent from the device response."""
    assert decode_sdp_answer({"sdp": "v=0\r\n"}) == CameraSdpDescription(sdp="v=0\r\n", type="answer")
    assert decode_sdp_answer(encode_wire_json({"sdp": "v=0\r\n"})) == CameraSdpDescription(sdp="v=0\r\n", type="answer")


@pytest.mark.parametrize("payload", ["retry", {"dev_sdp": "retry"}, [{"dev_sdp": "retry"}]])
def test_decode_sdp_answer_retry(payload: str | dict[str, Any] | list[Any]) -> None:
    """Leave retry handling explicit for the caller."""
    assert decode_sdp_answer(payload) is None


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ([], ValueError),
        (["not_dict"], TypeError),
        ({"invalid_key": "abc"}, ValueError),
        ({"dev_sdp": 12345}, TypeError),
        ("invalid_base64!@#$", binascii.Error),
        (base64.b64encode(b"not json").decode("ascii"), json.JSONDecodeError),
        (base64.b64encode(b"\xff").decode("ascii"), UnicodeDecodeError),
        (encode_wire_json([1, 2, 3]), ValueError),
        (encode_wire_json({"type": "answer"}), ValueError),
        (encode_wire_json({"sdp": ""}), ValueError),
        (encode_wire_json({"sdp": 123}), ValueError),
        (encode_wire_json({"sdp": "v=0", "type": "offer"}), ValueError),
        (encode_wire_json({"sdp": "v=0", "type": 1}), ValueError),
        ({"sdp": "v=0", "type": "offer"}, ValueError),
        ({"sdp": "", "type": "answer"}, ValueError),
    ],
)
def test_decode_sdp_answer_invalid_payloads(payload: str | dict[str, Any] | list[Any], error: type[Exception]) -> None:
    """Normalize malformed responses while preserving command context and the cause."""
    with pytest.raises(RoborockParsingException) as raised:
        decode_sdp_answer(payload)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, error)
    assert RoborockCommand.GET_DEVICE_SDP.name in str(raised.value)
    assert "CameraSignaling" in str(raised.value)
    assert f"'type': '{type(payload).__name__}'" in str(raised.value)


@pytest.mark.parametrize("encoded", [False, True])
def test_decode_sdp_answer_error_redacts_response(encoded: bool, caplog: pytest.LogCaptureFixture) -> None:
    """Do not put SDP credentials or malformed type values in public errors."""
    secret = "private-camera-secret"
    description = {"sdp": f"v=0\r\na=ice-pwd:{secret}\r\n", "type": secret}
    encoded_description = encode_wire_json(description)
    payload: str | dict[str, Any] = encoded_description if encoded else description

    with pytest.raises(RoborockParsingException) as raised:
        decode_sdp_answer(payload)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, ValueError)
    assert RoborockCommand.GET_DEVICE_SDP.name in str(raised.value)
    assert secret not in str(raised.value)
    assert secret not in repr(raised.value)
    assert secret not in caplog.text
    assert encoded_description not in str(raised.value)


def test_encode_ice_candidate_roundtrip() -> None:
    """Package a typed candidate and decode each supported response envelope."""
    candidate = parse_ice_candidate(HOST_CANDIDATE, sdp_mid="video", sdp_mline_index=1)
    encoded = encode_ice_candidate(candidate)

    assert json.loads(base64.b64decode(encoded)) == {
        "candidate": HOST_CANDIDATE,
        "sdpMid": "video",
        "sdpMLineIndex": 1,
    }
    assert decode_ice_candidates(encoded) == [candidate]
    assert decode_ice_candidates([encoded]) == [candidate]
    assert decode_ice_candidates({"dev_ice": [encoded]}) == [candidate]
    assert decode_ice_candidates([{"dev_ice": [encoded]}]) == [candidate]


def test_encode_ice_candidate_default_media_identifiers() -> None:
    """Use the protocol's default media identifiers when the model omits them."""
    encoded = encode_ice_candidate(parse_ice_candidate(HOST_CANDIDATE))

    assert json.loads(base64.b64decode(encoded)) == {
        "candidate": HOST_CANDIDATE,
        "sdpMid": "0",
        "sdpMLineIndex": 0,
    }


def test_decode_ice_candidates_empty_or_multiple() -> None:
    """Preserve order and support empty candidate responses."""
    assert decode_ice_candidates([]) == []
    assert decode_ice_candidates({"dev_ice": []}) == []
    assert decode_ice_candidates([{"dev_ice": []}]) == []

    first = parse_ice_candidate(HOST_CANDIDATE, sdp_mid="0", sdp_mline_index=0)
    second = parse_ice_candidate("candidate:2 1 udp 200 10.0.0.2 5000 typ host", sdp_mid="0", sdp_mline_index=0)
    encoded = [encode_ice_candidate(first), encode_ice_candidate(second)]

    assert decode_ice_candidates([{"dev_ice": encoded}]) == [first, second]


def test_decode_ice_candidates_no_base64_prefix_heuristic() -> None:
    """Decode valid base64 JSON even when its first bytes are whitespace."""
    wire_json = " \n" + json.dumps({"candidate": HOST_CANDIDATE, "sdpMid": "video", "sdpMLineIndex": 1})
    encoded = base64.b64encode(wire_json.encode("utf-8")).decode("ascii")
    assert not encoded.startswith("ey")

    assert decode_ice_candidates(encoded) == [parse_ice_candidate(HOST_CANDIDATE, sdp_mid="video", sdp_mline_index=1)]


def test_decode_ice_candidates_optional_media_identifiers() -> None:
    """Leave omitted media identifiers unset when receiving candidates."""
    encoded = encode_wire_json({"candidate": HOST_CANDIDATE})

    assert decode_ice_candidates(encoded) == [parse_ice_candidate(HOST_CANDIDATE)]
    encoded_nulls = encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMid": None, "sdpMLineIndex": None})
    assert decode_ice_candidates(encoded_nulls) == [parse_ice_candidate(HOST_CANDIDATE)]


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        pytest.param("invalid_base64!@#$", binascii.Error, id="invalid-base64"),
        pytest.param("YWJjZA", binascii.Error, id="missing-base64-padding"),
        pytest.param(HOST_CANDIDATE, ValueError, id="raw-sdp"),
        pytest.param("", ValueError, id="empty-string"),
        pytest.param("   ", ValueError, id="whitespace-string"),
        pytest.param(base64.b64encode(b"\xff").decode("ascii"), UnicodeDecodeError, id="invalid-utf8"),
        pytest.param(base64.b64encode(b"not json").decode("ascii"), json.JSONDecodeError, id="invalid-json"),
        pytest.param(base64.b64encode(b'{"candidate":').decode("ascii"), json.JSONDecodeError, id="truncated-json"),
        pytest.param(encode_wire_json([1, 2, 3]), ValueError, id="json-list"),
        pytest.param(encode_wire_json(None), ValueError, id="json-null"),
        pytest.param(encode_wire_json({"sdpMid": "0"}), ValueError, id="missing-candidate"),
        pytest.param(encode_wire_json({"candidate": None}), ValueError, id="null-candidate"),
        pytest.param(encode_wire_json({"candidate": ""}), ValueError, id="empty-candidate"),
        pytest.param(encode_wire_json({"candidate": "not a candidate"}), ValueError, id="malformed-candidate"),
        pytest.param(encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMid": 1}), TypeError, id="numeric-mid"),
        pytest.param(encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMid": ["0"]}), TypeError, id="list-mid"),
        pytest.param(
            encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": "1"}), TypeError, id="string-mline"
        ),
        pytest.param(encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": [1]}), TypeError, id="list-mline"),
        pytest.param(
            encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": True}), TypeError, id="bool-mline"
        ),
        pytest.param(
            encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": 1.5}), TypeError, id="float-mline"
        ),
        pytest.param(
            encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": -1}), ValueError, id="negative-mline"
        ),
    ],
)
def test_decode_ice_candidates_invalid_wire_data(payload: str, error: type[Exception]) -> None:
    """Normalize invalid base64, UTF-8, JSON, schema, and candidate errors."""
    with pytest.raises(RoborockParsingException) as raised:
        decode_ice_candidates(payload)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, error)
    assert RoborockCommand.GET_DEVICE_ICE.name in str(raised.value)
    assert "CameraSignaling" in str(raised.value)
    assert "'type': 'str'" in str(raised.value)
    assert "'candidate_index': 0" in str(raised.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"candidate": HOST_CANDIDATE},
        [{"candidate": HOST_CANDIDATE, "sdpMid": "0", "sdpMLineIndex": 0}],
        {"dev_ice": "not_a_list"},
        {"dev_ice": [123]},
        [123],
        [parse_ice_candidate(HOST_CANDIDATE)],
        [{"dev_ice": []}, {"dev_ice": []}],
    ],
)
def test_decode_ice_candidates_rejects_non_wire_inputs(payload: dict[str, Any] | list[Any]) -> None:
    """Do not accept unencoded models, candidate dictionaries, or malformed envelopes."""
    with pytest.raises(RoborockParsingException) as raised:
        decode_ice_candidates(payload)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, (ValueError, TypeError))
    assert RoborockCommand.GET_DEVICE_ICE.name in str(raised.value)
    assert f"'type': '{type(payload).__name__}'" in str(raised.value)


def test_decode_ice_candidates_ignore_invalid(caplog: pytest.LogCaptureFixture) -> None:
    """Skip malformed candidate items and retain all valid candidates in order."""
    first = parse_ice_candidate(HOST_CANDIDATE, sdp_mid="video", sdp_mline_index=1)
    second = parse_ice_candidate("candidate:2 1 udp 200 10.0.0.2 5000 typ host", sdp_mid="video", sdp_mline_index=1)
    payload = [
        "not base64!",
        encode_ice_candidate(first),
        base64.b64encode(b"\xff").decode("ascii"),
        encode_wire_json([1, 2, 3]),
        encode_wire_json({"sdpMid": "0"}),
        encode_wire_json({"candidate": "not a candidate"}),
        encode_wire_json({"candidate": HOST_CANDIDATE, "sdpMLineIndex": [1]}),
        encode_ice_candidate(second),
    ]

    assert decode_ice_candidates({"dev_ice": payload}, ignore_invalid=True) == [first, second]
    assert any("Skipping" in record.message for record in caplog.records)


def test_decode_ice_candidates_ignore_invalid_does_not_hide_envelope_errors() -> None:
    """Candidate leniency does not allow an invalid RPC response structure."""
    with pytest.raises(RoborockParsingException) as raised:
        decode_ice_candidates({"dev_ice": "not_a_list"}, ignore_invalid=True)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, TypeError)
    assert RoborockCommand.GET_DEVICE_ICE.name in str(raised.value)
    assert "'type': 'dict'" in str(raised.value)


def test_decode_ice_candidates_error_identifies_candidate_and_redacts_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Locate a malformed candidate without exposing its raw SDP in the error."""
    secret = "private-camera-secret"
    invalid = encode_wire_json({"candidate": f"{HOST_CANDIDATE} {secret}"})
    payload = [encode_wire_json({"candidate": HOST_CANDIDATE}), invalid]

    with pytest.raises(RoborockParsingException) as raised:
        decode_ice_candidates(payload)

    assert isinstance(raised.value, RoborockException)
    assert isinstance(raised.value.__cause__, ValueError)
    assert RoborockCommand.GET_DEVICE_ICE.name in str(raised.value)
    assert "'type': 'list'" in str(raised.value)
    assert "'candidate_index': 1" in str(raised.value)
    assert secret not in str(raised.value)
    assert secret not in repr(raised.value)
    assert invalid not in str(raised.value)
    assert secret not in caplog.text


def test_decode_ice_candidates_ignore_invalid_log_redacts_response(caplog: pytest.LogCaptureFixture) -> None:
    """Keep skipped candidate diagnostics useful without logging candidate secrets."""
    secret = "private-camera-secret"
    invalid = encode_wire_json({"candidate": f"{HOST_CANDIDATE} {secret}"})
    valid = encode_wire_json({"candidate": HOST_CANDIDATE})

    assert decode_ice_candidates([invalid, valid], ignore_invalid=True) == [parse_ice_candidate(HOST_CANDIDATE)]
    assert any("Skipping" in record.message for record in caplog.records)
    assert secret not in caplog.text
    assert invalid not in caplog.text

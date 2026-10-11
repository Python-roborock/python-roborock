"""Unit tests for camera signaling models, ICE parsing utilities, and payload serialization."""

from __future__ import annotations

import base64
import json

import pytest

from roborock.camera_signaling import (
    CameraIceCandidate,
    CameraQuality,
    CameraTurnServer,
    decode_ice_candidates,
    decode_sdp_answer,
    encode_ice_candidate,
    encode_sdp_offer,
    hash_camera_password,
    parse_ice_candidate,
)
from roborock.data import (
    CameraIceCandidate as DataCameraIceCandidate,
)
from roborock.data import (
    CameraQuality as DataCameraQuality,
)
from roborock.data import (
    CameraTurnServer as DataCameraTurnServer,
)
from roborock.data.camera import (
    CameraIceCandidate as CameraModIceCandidate,
)
from roborock.data.camera import (
    CameraQuality as CameraModQuality,
)
from roborock.data.camera import (
    CameraTurnServer as CameraModTurnServer,
)

# ============================================================================
# Re-export and import smoke tests
# ============================================================================


def test_reexports_match() -> None:
    """Verify camera signaling items are correctly re-exported across modules."""
    assert DataCameraQuality is CameraQuality
    assert DataCameraTurnServer is CameraTurnServer
    assert DataCameraIceCandidate is CameraIceCandidate

    assert CameraModQuality is CameraQuality
    assert CameraModTurnServer is CameraTurnServer
    assert CameraModIceCandidate is CameraIceCandidate


# ============================================================================
# CameraQuality tests
# ============================================================================


def test_camera_quality_values() -> None:
    """Test CameraQuality enum values and string behavior."""
    assert CameraQuality.HD == "HD"
    assert CameraQuality.SD == "SD"
    assert str(CameraQuality.HD) == "HD"
    assert CameraQuality("HD") is CameraQuality.HD
    assert CameraQuality("SD") is CameraQuality.SD


def test_camera_quality_from_str() -> None:
    """Test CameraQuality.from_str case insensitivity and error handling."""
    assert CameraQuality.from_str("hd") is CameraQuality.HD
    assert CameraQuality.from_str("HD") is CameraQuality.HD
    assert CameraQuality.from_str("sd") is CameraQuality.SD
    assert CameraQuality.from_str("  SD  ") is CameraQuality.SD

    with pytest.raises(ValueError, match="Invalid camera quality"):
        CameraQuality.from_str("4K")

    with pytest.raises(TypeError, match="Expected str"):
        CameraQuality.from_str(123)  # type: ignore[arg-type]


# ============================================================================
# CameraTurnServer tests
# ============================================================================


def test_camera_turn_server_from_device_rpc_list() -> None:
    """Test parsing get_turn_server response from single-item list."""
    payload = [{"url": "turn:turn-us.roborock.com:3478", "user": "roborock_user", "pwd": "secret_password"}]
    turn = CameraTurnServer.from_dict(payload)

    assert turn.urls == ["turn:turn-us.roborock.com:3478"]
    assert turn.username == "roborock_user"
    assert turn.credential == "secret_password"

    # Verify credential redaction in repr
    assert "secret_password" not in repr(turn)

    rtc_dict = turn.to_dict()
    assert rtc_dict == {
        "urls": ["turn:turn-us.roborock.com:3478"],
        "username": "roborock_user",
        "credential": "secret_password",
    }


def test_camera_turn_server_from_device_rpc_dict() -> None:
    """Test parsing get_turn_server response from bare dict."""
    payload = {"url": "turn:turn-eu.roborock.com:3478", "user": "eu_user", "pwd": "eu_password"}
    turn = CameraTurnServer.from_dict(payload)

    assert turn.urls == ["turn:turn-eu.roborock.com:3478"]
    assert turn.username == "eu_user"
    assert turn.credential == "eu_password"
    assert "eu_password" not in repr(turn)


def test_camera_turn_server_from_standard_webrtc_dict() -> None:
    """Test parsing standard WebRTC RTCIceServer dict format."""
    payload = {
        "urls": ["stun:stun.l.google.com:19302", "turns:turn.example.com:443"],
        "username": "user123",
        "credential": "pass123",
    }
    turn = CameraTurnServer.from_dict(payload)

    assert turn.urls == ["stun:stun.l.google.com:19302", "turns:turn.example.com:443"]
    assert turn.username == "user123"
    assert turn.credential == "pass123"


def test_camera_turn_server_without_credentials() -> None:
    """Test TURN server with optional credentials absent."""
    payload = {"urls": "turn:turn.example.com:3478"}
    turn = CameraTurnServer.from_dict(payload)

    assert turn.urls == ["turn:turn.example.com:3478"]
    assert turn.username is None
    assert turn.credential is None
    assert turn.to_dict() == {"urls": ["turn:turn.example.com:3478"]}


def test_camera_turn_server_invalid_payloads() -> None:
    """Test invalid payloads raise appropriate errors."""
    with pytest.raises(ValueError, match="Empty TURN server data list"):
        CameraTurnServer.from_dict([])

    with pytest.raises(TypeError, match="Expected dict inside TURN server list"):
        CameraTurnServer.from_dict(["not_a_dict"])  # type: ignore[list-item]

    with pytest.raises(TypeError, match="Expected dict or list"):
        CameraTurnServer.from_dict("not_a_dict_or_list")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Missing 'url' or 'urls'"):
        CameraTurnServer.from_dict({"user": "user_only"})

    with pytest.raises(TypeError, match="Expected str or list for urls"):
        CameraTurnServer.from_dict({"urls": 12345})  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="non-empty string"):
        CameraTurnServer.from_dict({"urls": [""]})

    with pytest.raises(ValueError, match="non-empty string"):
        CameraTurnServer.from_dict({"urls": [None]})  # type: ignore[list-item]

    with pytest.raises(ValueError, match="Invalid ICE server URL scheme"):
        CameraTurnServer.from_dict({"url": "http://invalidscheme.com"})


# ============================================================================
# parse_ice_candidate tests
# ============================================================================


def test_parse_ice_candidate_host_udp() -> None:
    """Test parsing standard host UDP candidate."""
    cand_str = "candidate:4234997325 1 udp 2122260223 192.168.1.100 54321 typ host"
    cand = parse_ice_candidate(cand_str, sdp_mid="0", sdp_mline_index=0)

    assert cand.foundation == "4234997325"
    assert cand.component == 1
    assert cand.protocol == "udp"
    assert cand.priority == 2122260223
    assert cand.ip == "192.168.1.100"
    assert cand.port == 54321
    assert cand.candidate_type == "host"
    assert cand.related_address is None
    assert cand.related_port is None
    assert cand.tcp_type is None
    assert cand.sdp_mid == "0"
    assert cand.sdp_mline_index == 0
    assert cand.to_sdp() == cand_str
    assert str(cand) == cand_str


def test_parse_ice_candidate_srflx_with_raddr() -> None:
    """Test parsing srflx candidate with raddr and rport."""
    cand_str = "candidate:123456 1 udp 1686052607 203.0.113.1 54321 typ srflx raddr 192.168.1.100 rport 54321"
    cand = parse_ice_candidate(cand_str)

    assert cand.foundation == "123456"
    assert cand.component == 1
    assert cand.protocol == "udp"
    assert cand.priority == 1686052607
    assert cand.ip == "203.0.113.1"
    assert cand.port == 54321
    assert cand.candidate_type == "srflx"
    assert cand.related_address == "192.168.1.100"
    assert cand.related_port == 54321
    assert cand.tcp_type is None
    assert cand.to_sdp() == cand_str


def test_parse_ice_candidate_relay() -> None:
    """Test parsing relay candidate."""
    cand_str = "candidate:789012 1 udp 33562367 198.51.100.2 3478 typ relay raddr 203.0.113.1 rport 54321"
    cand = parse_ice_candidate(cand_str)

    assert cand.foundation == "789012"
    assert cand.protocol == "udp"
    assert cand.candidate_type == "relay"
    assert cand.ip == "198.51.100.2"
    assert cand.port == 3478
    assert cand.related_address == "203.0.113.1"
    assert cand.related_port == 54321
    assert cand.to_sdp() == cand_str


def test_parse_ice_candidate_tcp_with_tcptype() -> None:
    """Test parsing TCP candidate with tcptype."""
    cand_str = "candidate:345678 1 tcp 1518280447 192.168.1.100 9 typ host tcptype active"
    cand = parse_ice_candidate(cand_str)

    assert cand.foundation == "345678"
    assert cand.protocol == "tcp"
    assert cand.candidate_type == "host"
    assert cand.port == 9
    assert cand.tcp_type == "active"
    assert cand.to_sdp() == cand_str


def test_parse_ice_candidate_ipv6() -> None:
    """Test parsing IPv6 candidate."""
    cand_str = "candidate:1 1 udp 2122260223 2001:db8::1 50000 typ host"
    cand = parse_ice_candidate(cand_str)

    assert cand.ip == "2001:db8::1"
    assert cand.port == 50000
    assert cand.to_sdp() == cand_str


def test_parse_ice_candidate_mdns_hostname() -> None:
    """Test parsing mDNS .local hostname candidate from modern browsers."""
    cand_str = "candidate:1 1 udp 2122260223 d79c09bf-323e-4610-8f92-5eb3fa7e4a1a.local 50000 typ host"
    cand = parse_ice_candidate(cand_str)

    assert cand.ip == "d79c09bf-323e-4610-8f92-5eb3fa7e4a1a.local"
    assert cand.to_sdp() == cand_str


def test_parse_ice_candidate_prefixes_and_extra_attrs() -> None:
    """Test candidate with a= prefix, no prefix, CRLF, and extra SDP attributes like generation."""
    # a=candidate: prefix and trailing CRLF
    cand1 = parse_ice_candidate("a=candidate:1 1 udp 100 1.2.3.4 5000 typ host generation 0 network-id 1\r\n")
    assert cand1.foundation == "1"
    assert cand1.candidate_type == "host"
    assert cand1.ip == "1.2.3.4"
    assert cand1.extensions == {"generation": "0", "network-id": "1"}

    # Bare tokens without candidate: prefix
    cand2 = parse_ice_candidate("1 1 udp 100 1.2.3.4 5000 typ host")
    assert cand2.foundation == "1"
    assert cand2.candidate_type == "host"


def test_parse_ice_candidate_numeric_and_lexical_bounds() -> None:
    """Test strict RFC 8839 / RFC 8445 component, priority, and foundation bounds."""
    # Component: valid boundary 1 and 256
    c1 = parse_ice_candidate("candidate:1 1 udp 100 1.1.1.1 200 typ host")
    assert c1.component == 1
    c256 = parse_ice_candidate("candidate:1 256 udp 100 1.1.1.1 200 typ host")
    assert c256.component == 256

    # Component: out of bounds (0 or 257)
    with pytest.raises(ValueError, match="RFC 8839 range"):
        parse_ice_candidate("candidate:1 0 udp 100 1.1.1.1 200 typ host")
    with pytest.raises(ValueError, match="RFC 8839 range"):
        parse_ice_candidate("candidate:1 257 udp 100 1.1.1.1 200 typ host")

    # Priority: valid boundary 1 and 2147483647
    p1 = parse_ice_candidate("candidate:1 1 udp 1 1.1.1.1 200 typ host")
    assert p1.priority == 1
    p_max = parse_ice_candidate("candidate:1 1 udp 2147483647 1.1.1.1 200 typ host")
    assert p_max.priority == 2147483647

    # Priority: out of bounds (0 or 2147483648)
    with pytest.raises(ValueError, match="RFC 8445 range"):
        parse_ice_candidate("candidate:1 1 udp 0 1.1.1.1 200 typ host")
    with pytest.raises(ValueError, match="RFC 8445 range"):
        parse_ice_candidate("candidate:1 1 udp 2147483648 1.1.1.1 200 typ host")

    # Non-decimal syntax: plus signs or underscores rejected
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        parse_ice_candidate("candidate:1 +1 udp 100 1.1.1.1 200 typ host")
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        parse_ice_candidate("candidate:1 1 udp 1_000 1.1.1.1 200 typ host")

    # Foundation: must be 1-32 ice characters
    with pytest.raises(ValueError, match="Invalid ICE foundation"):
        parse_ice_candidate(f"candidate:{'a' * 33} 1 udp 100 1.1.1.1 200 typ host")
    with pytest.raises(ValueError, match="Invalid ICE foundation"):
        parse_ice_candidate("candidate:invalid@char 1 udp 100 1.1.1.1 200 typ host")


def test_parse_ice_candidate_invariants() -> None:
    """Test RFC 6544 TCP and RFC 8839 related address invariants."""
    # TCP candidate requires tcptype
    with pytest.raises(ValueError, match="TCP ICE candidate must specify 'tcptype'"):
        parse_ice_candidate("candidate:1 1 tcp 100 1.1.1.1 9 typ host")

    # Invalid tcptype
    with pytest.raises(ValueError, match="Invalid ICE TCP type"):
        parse_ice_candidate("candidate:1 1 tcp 100 1.1.1.1 9 typ host tcptype invalid")

    # raddr without rport
    with pytest.raises(ValueError, match="must have both 'raddr' and 'rport' specified together"):
        parse_ice_candidate("candidate:1 1 udp 100 1.1.1.1 200 typ srflx raddr 2.2.2.2")

    # rport without raddr
    with pytest.raises(ValueError, match="must have both 'raddr' and 'rport' specified together"):
        parse_ice_candidate("candidate:1 1 udp 100 1.1.1.1 200 typ srflx rport 5000")


def test_candidate_to_signaling_dict() -> None:
    """Test converting CameraIceCandidate to signaling dict."""
    cand = CameraIceCandidate(
        foundation="1",
        component=1,
        protocol="udp",
        priority=100,
        ip="1.2.3.4",
        port=5000,
        candidate_type="host",
        sdp_mid="video",
        sdp_mline_index=1,
    )
    sig_dict = cand.to_signaling_dict()
    assert sig_dict == {
        "candidate": "candidate:1 1 udp 100 1.2.3.4 5000 typ host",
        "sdpMid": "video",
        "sdpMLineIndex": 1,
    }


# ============================================================================
# hash_camera_password tests
# ============================================================================


def test_hash_camera_password_valid() -> None:
    """Test deriving lowercase hex MD5 of digits."""
    # 1234 -> 81dc9bdb52d04dc20036dbd8313ed055
    assert hash_camera_password("1234") == "81dc9bdb52d04dc20036dbd8313ed055"
    assert hash_camera_password(1234) == "81dc9bdb52d04dc20036dbd8313ed055"

    # 9876 -> 912e79cd13c64069d91da65d62fbb78c
    assert hash_camera_password("9876") == "912e79cd13c64069d91da65d62fbb78c"

    # Leading zero in digits preserved
    assert hash_camera_password("0123") == "eb62f6b9306db575c2d596b1279627a4"


def test_hash_camera_password_invalid() -> None:
    """Test invalid password formats raise ValueError or TypeError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        hash_camera_password("")

    with pytest.raises(ValueError, match="only ASCII digits"):
        hash_camera_password("12a4")

    # Full-width digits should be rejected
    with pytest.raises(ValueError, match="only ASCII digits"):
        hash_camera_password("１２３４")

    with pytest.raises(ValueError, match="only ASCII digits"):
        hash_camera_password("password")

    with pytest.raises(TypeError, match="must be a str or int"):
        hash_camera_password(None)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="must be a str or int"):
        hash_camera_password(["1", "2", "3", "4"])  # type: ignore[arg-type]


# ============================================================================
# SDP offer/answer packaging tests
# ============================================================================


def test_encode_sdp_offer_and_decode_sdp_answer_roundtrip() -> None:
    """Test round-trip SDP offer encoding and answer decoding."""
    raw_sdp = "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
    encoded_offer = encode_sdp_offer(raw_sdp)

    # Offer decoded from base64 JSON
    decoded_json = json.loads(base64.b64decode(encoded_offer).decode("utf-8"))
    assert decoded_json == {"sdp": raw_sdp, "type": "offer"}

    # Simulate device answer payload
    answer_payload = {
        "sdp": "v=0\r\no=- 67890 2 IN IP4 127.0.0.1\r\ns=-\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n",
        "type": "answer",
    }
    answer_b64 = base64.b64encode(json.dumps(answer_payload).encode("utf-8")).decode("ascii")

    # Decode from bare string
    res_str = decode_sdp_answer(answer_b64)
    assert res_str == answer_payload

    # Decode from device dict response: {"dev_sdp": "..."}
    res_dict = decode_sdp_answer({"dev_sdp": answer_b64})
    assert res_dict == answer_payload

    # Decode from device single-item list response: [{"dev_sdp": "..."}]
    res_list = decode_sdp_answer([{"dev_sdp": answer_b64}])
    assert res_list == answer_payload


def test_encode_sdp_offer_from_dict() -> None:
    """Test encoding SDP offer from dictionary."""
    offer_dict = {"sdp": "v=0\r\no=- 1 1 IN IP4 0.0.0.0", "type": "offer"}
    b64_str = encode_sdp_offer(offer_dict)
    decoded = json.loads(base64.b64decode(b64_str).decode("utf-8"))
    assert decoded["sdp"] == offer_dict["sdp"]
    assert decoded["type"] == "offer"


def test_decode_sdp_answer_retry() -> None:
    """Test that retry string returns None."""
    assert decode_sdp_answer("retry") is None
    assert decode_sdp_answer({"dev_sdp": "retry"}) is None
    assert decode_sdp_answer([{"dev_sdp": "retry"}]) is None


def test_encode_sdp_offer_errors() -> None:
    """Test error handling in encode_sdp_offer."""
    with pytest.raises(ValueError, match="cannot be empty"):
        encode_sdp_offer("")

    with pytest.raises(ValueError, match="must contain a non-empty string 'sdp' key"):
        encode_sdp_offer({})

    with pytest.raises(ValueError, match="must contain a non-empty string 'sdp' key"):
        encode_sdp_offer({"sdp": None})  # type: ignore[dict-item]

    with pytest.raises(ValueError, match="cannot be empty"):
        encode_sdp_offer({"sdp": "   "})

    with pytest.raises(ValueError, match="type must be 'offer'"):
        encode_sdp_offer({"sdp": "v=0...", "type": "answer"})

    with pytest.raises(TypeError, match="Expected str or dict"):
        encode_sdp_offer(12345)  # type: ignore[arg-type]


def test_decode_sdp_answer_already_decoded_dict() -> None:
    """Test decoding when already a dict with sdp key."""
    res = decode_sdp_answer({"sdp": "v=0...", "type": "answer"})
    assert res == {"sdp": "v=0...", "type": "answer"}

    with pytest.raises(ValueError, match="invalid 'type'"):
        decode_sdp_answer({"sdp": "v=0...", "type": "offer"})

    with pytest.raises(ValueError, match="missing or empty 'sdp'"):
        decode_sdp_answer({"sdp": "", "type": "answer"})


def test_decode_sdp_answer_errors_and_edge_cases() -> None:
    """Test invalid payloads in decode_sdp_answer raise ValueError or TypeError."""
    with pytest.raises(ValueError, match="Empty response list"):
        decode_sdp_answer([])

    with pytest.raises(TypeError, match="Expected dict inside SDP answer list"):
        decode_sdp_answer(["not_dict"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="missing 'dev_sdp' or 'sdp'"):
        decode_sdp_answer({"invalid_key": "abc"})

    with pytest.raises(TypeError, match="Expected str for 'dev_sdp'"):
        decode_sdp_answer({"dev_sdp": 12345})  # type: ignore[dict-item]

    with pytest.raises(TypeError, match="Expected str, dict, or list"):
        decode_sdp_answer(12345)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Failed to decode base64 JSON"):
        decode_sdp_answer("invalid_base64!@#$")

    # Valid base64, but invalid JSON
    invalid_json_b64 = base64.b64encode(b"not json").decode("ascii")
    with pytest.raises(ValueError, match="Failed to decode base64 JSON"):
        decode_sdp_answer(invalid_json_b64)

    # Valid JSON, but not an object
    not_obj_b64 = base64.b64encode(b"[1, 2, 3]").decode("ascii")
    with pytest.raises(ValueError, match="must be an object"):
        decode_sdp_answer(not_obj_b64)

    # Valid JSON object, but missing 'sdp'
    missing_sdp_b64 = base64.b64encode(b'{"type": "answer"}').decode("ascii")
    with pytest.raises(ValueError, match="missing or empty 'sdp' field"):
        decode_sdp_answer(missing_sdp_b64)


# ============================================================================
# ICE candidate packaging tests
# ============================================================================


def test_encode_ice_candidate_and_decode_roundtrip() -> None:
    """Test round-trip encoding and decoding of ICE candidates."""
    cand = CameraIceCandidate(
        foundation="cand1",
        component=1,
        protocol="udp",
        priority=2122260223,
        ip="192.168.1.50",
        port=55555,
        candidate_type="host",
        sdp_mid="0",
        sdp_mline_index=0,
    )

    encoded = encode_ice_candidate(cand)

    # Verify JSON structure inside base64
    obj = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert obj["candidate"] == cand.to_sdp()
    assert obj["sdpMid"] == "0"
    assert obj["sdpMLineIndex"] == 0

    # Decode from list of base64 strings
    decoded_list = decode_ice_candidates([encoded])
    assert len(decoded_list) == 1
    assert decoded_list[0] == cand

    # Decode from get_device_ice dict: {"dev_ice": [...]}
    decoded_dict = decode_ice_candidates({"dev_ice": [encoded]})
    assert len(decoded_dict) == 1
    assert decoded_dict[0] == cand

    # Decode from get_device_ice single-item list: [{"dev_ice": [...]}]
    decoded_resp = decode_ice_candidates([{"dev_ice": [encoded]}])
    assert len(decoded_resp) == 1
    assert decoded_resp[0] == cand


def test_encode_ice_candidate_from_str_and_dict() -> None:
    """Test encoding from raw candidate string and dictionary."""
    raw_sdp = "candidate:1 1 udp 100 1.1.1.1 200 typ host"
    b64_str = encode_ice_candidate(raw_sdp, sdp_mid="1", sdp_mline_index=1)
    obj = json.loads(base64.b64decode(b64_str).decode("utf-8"))
    assert obj["candidate"] == raw_sdp
    assert obj["sdpMid"] == "1"
    assert obj["sdpMLineIndex"] == 1

    # From string without candidate: prefix
    b64_str2 = encode_ice_candidate("1 1 udp 100 1.1.1.1 200 typ host")
    obj2 = json.loads(base64.b64decode(b64_str2).decode("utf-8"))
    assert obj2["candidate"] == raw_sdp

    # From dict
    dict_cand = {"candidate": raw_sdp, "sdpMid": "0", "sdpMLineIndex": 0}
    b64_dict = encode_ice_candidate(dict_cand)
    obj3 = json.loads(base64.b64decode(b64_dict).decode("utf-8"))
    assert obj3["candidate"] == raw_sdp


def test_decode_ice_candidates_empty_or_multiple() -> None:
    """Test decoding empty list and multiple candidates."""
    assert decode_ice_candidates([]) == []
    assert decode_ice_candidates({"dev_ice": []}) == []
    assert decode_ice_candidates([{"dev_ice": []}]) == []

    cand1 = "candidate:1 1 udp 100 10.0.0.1 5000 typ host"
    cand2 = "candidate:2 1 udp 200 10.0.0.2 5000 typ host"
    enc1 = encode_ice_candidate(cand1, sdp_mid="0", sdp_mline_index=0)
    enc2 = encode_ice_candidate(cand2, sdp_mid="0", sdp_mline_index=0)

    results = decode_ice_candidates([{"dev_ice": [enc1, enc2]}])
    assert len(results) == 2
    assert results[0].foundation == "1"
    assert results[1].foundation == "2"


def test_decode_ice_candidates_errors() -> None:
    """Test invalid payloads in decode_ice_candidates raise TypeError or ValueError."""
    with pytest.raises(TypeError, match="Expected str, list, or dict"):
        decode_ice_candidates(12345)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected list in 'dev_ice'"):
        decode_ice_candidates({"dev_ice": "not_a_list"})

    with pytest.raises(TypeError, match="Unexpected candidate item type"):
        decode_ice_candidates([12345])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="missing 'candidate' string"):
        decode_ice_candidates([{"sdpMid": "0"}])

    with pytest.raises(TypeError, match="Expected list in 'dev_ice'"):
        decode_ice_candidates([{"dev_ice": "not_a_list"}])


def test_encode_ice_candidate_errors() -> None:
    """Test error handling in encode_ice_candidate."""
    with pytest.raises(ValueError, match="cannot be empty"):
        encode_ice_candidate("")

    with pytest.raises(ValueError, match="missing or invalid 'candidate'"):
        encode_ice_candidate({})

    with pytest.raises(TypeError, match="Expected CameraIceCandidate, dict, or str"):
        encode_ice_candidate(12345)  # type: ignore[arg-type]


def test_decode_ice_candidates_edge_cases() -> None:
    """Test edge cases in decode_ice_candidates."""
    # Single string directly
    cand_str = "candidate:1 1 udp 100 1.2.3.4 5000 typ host"
    res1 = decode_ice_candidates(cand_str)
    assert len(res1) == 1
    assert res1[0].foundation == "1"

    # Dict without dev_ice (single candidate dict)
    res2 = decode_ice_candidates({"candidate": cand_str, "sdpMid": "0", "sdpMLineIndex": 0})
    assert len(res2) == 1
    assert res2[0].foundation == "1"

    # Item is already CameraIceCandidate
    existing_cand = parse_ice_candidate(cand_str)
    res3 = decode_ice_candidates([existing_cand])
    assert res3 == [existing_cand]

    # Item is raw dict
    res4 = decode_ice_candidates([{"candidate": cand_str, "sdpMid": "video", "sdpMLineIndex": 1}])
    assert len(res4) == 1
    assert res4[0].sdp_mid == "video"
    assert res4[0].sdp_mline_index == 1

    # Empty string in list ignored
    res5 = decode_ice_candidates(["", "   "])
    assert res5 == []

    # Non-base64 raw candidate string in list
    res6 = decode_ice_candidates([cand_str])
    assert len(res6) == 1
    assert res6[0].foundation == "1"

    # Corrupted base64 payload starting with ey raises ValueError
    bad_base64_json = "eyJjYW5kaWRhdGUiOiA="  # incomplete json
    with pytest.raises(ValueError, match="Failed to decode base64 JSON"):
        decode_ice_candidates([bad_base64_json])

    # ignore_invalid skips bad candidate
    res7 = decode_ice_candidates([bad_base64_json, cand_str], ignore_invalid=True)
    assert len(res7) == 1
    assert res7[0].foundation == "1"


def test_parse_ice_candidate_dangling_token() -> None:
    """Test candidate with an odd trailing token (dangling attribute name)."""
    cand = parse_ice_candidate("candidate:1 1 udp 100 1.2.3.4 5000 typ host dangling_token")
    assert cand.foundation == "1"
    assert cand.candidate_type == "host"


def test_candidate_to_sdp_manual_without_raw() -> None:
    """Test to_sdp formatting when candidate is manually constructed without raw."""
    cand = CameraIceCandidate(
        foundation="1",
        component=1,
        protocol="udp",
        priority=100,
        ip="1.2.3.4",
        port=5000,
        candidate_type="srflx",
        related_address="10.0.0.1",
        related_port=5000,
        extensions={"generation": "0"},
        raw=None,
    )
    assert cand.to_sdp() == "candidate:1 1 udp 100 1.2.3.4 5000 typ srflx raddr 10.0.0.1 rport 5000 generation 0"


def test_camera_turn_server_empty_urls_error() -> None:
    """Test empty URL string or empty list in CameraTurnServer raises ValueError."""
    with pytest.raises(ValueError, match="Missing 'url' or 'urls'"):
        CameraTurnServer.from_dict({"url": ""})

    with pytest.raises(ValueError, match="Missing 'url' or 'urls'"):
        CameraTurnServer.from_dict({"urls": []})


def test_encode_ice_candidate_mline_string_and_errors() -> None:
    """Test sdp_mline_index coercion and error handling."""
    raw_sdp = "candidate:1 1 udp 100 1.1.1.1 200 typ host"
    # string integer
    b64_str = encode_ice_candidate(raw_sdp, sdp_mline_index="1")  # type: ignore[arg-type]
    obj = json.loads(base64.b64decode(b64_str).decode("utf-8"))
    assert obj["sdpMLineIndex"] == 1

    # invalid string
    with pytest.raises(ValueError, match="Invalid sdpMLineIndex"):
        encode_ice_candidate(raw_sdp, sdp_mline_index="not_a_number")  # type: ignore[arg-type]


def test_decode_ice_candidates_ignore_invalid_variations() -> None:
    """Test ignore_invalid handles bad candidate dicts and bad strings."""
    # Dict missing candidate string with ignore_invalid=True
    res1 = decode_ice_candidates([{"sdpMid": "0"}], ignore_invalid=True)
    assert res1 == []

    # Dict with invalid candidate string with ignore_invalid=True
    res2 = decode_ice_candidates([{"candidate": "not a candidate"}], ignore_invalid=True)
    assert res2 == []

    # Raw string with invalid candidate and ignore_invalid=True
    res3 = decode_ice_candidates(["not a candidate"], ignore_invalid=True)
    assert res3 == []

    # Base64 JSON missing candidate key
    no_cand_json = base64.b64encode(b'{"sdpMid": "0"}').decode("ascii")
    with pytest.raises(ValueError, match="missing 'candidate' string"):
        decode_ice_candidates([no_cand_json])

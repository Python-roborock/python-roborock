"""Tests for camera data models."""

import pytest

from roborock.data.camera import CameraIceCandidate, CameraQuality, CameraSdpDescription, CameraTurnServer
from roborock.data.containers import RoborockBase


def test_camera_quality_values() -> None:
    """Test CameraQuality enum values and string behavior."""
    assert CameraQuality.HD == "HD"
    assert CameraQuality.SD == "SD"
    assert CameraQuality.FHD == "FHD"
    assert CameraQuality.AUTO == "auto"
    assert str(CameraQuality.HD) == "HD"
    assert CameraQuality("HD") is CameraQuality.HD
    assert CameraQuality("SD") is CameraQuality.SD
    assert CameraQuality("FHD") is CameraQuality.FHD
    assert CameraQuality("auto") is CameraQuality.AUTO


@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ("hd", CameraQuality.HD),
        ("HD", CameraQuality.HD),
        ("sd", CameraQuality.SD),
        ("  SD  ", CameraQuality.SD),
        ("fhd", CameraQuality.FHD),
        ("FHD", CameraQuality.FHD),
        ("auto", CameraQuality.AUTO),
        ("AUTO", CameraQuality.AUTO),
        ("  auto  ", CameraQuality.AUTO),
    ],
)
def test_camera_quality_from_str(input_str: str, expected: CameraQuality) -> None:
    """Test CameraQuality.from_str case insensitivity and whitespace trimming."""
    assert CameraQuality.from_str(input_str) is expected


def test_camera_quality_from_str_invalid() -> None:
    """Test CameraQuality.from_str error handling for invalid values."""
    with pytest.raises(ValueError, match="Invalid camera quality"):
        CameraQuality.from_str("4K")


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

    rtc_dict = turn.as_dict()
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
    assert turn.as_dict() == {"urls": ["turn:turn.example.com:3478"]}


def test_camera_turn_server_empty_response_list() -> None:
    """An empty RPC response list is rejected."""
    with pytest.raises(ValueError, match="Empty TURN server data list"):
        CameraTurnServer.from_dict([])


def test_camera_turn_server_missing_urls() -> None:
    """A response without URL fields is rejected."""
    with pytest.raises(ValueError, match="Missing 'url' or 'urls'"):
        CameraTurnServer.from_dict({"user": "user_only"})


def test_camera_turn_server_invalid_urls_type() -> None:
    """URLs must be a string or a list."""
    with pytest.raises(TypeError, match="Expected str or list for urls"):
        CameraTurnServer.from_dict({"urls": 12345})


def test_camera_turn_server_empty_url_in_list() -> None:
    """URL lists cannot contain empty strings."""
    with pytest.raises(ValueError, match="non-empty string"):
        CameraTurnServer.from_dict({"urls": [""]})


def test_camera_turn_server_null_url_in_list() -> None:
    """URL lists cannot contain null values."""
    with pytest.raises(ValueError, match="non-empty string"):
        CameraTurnServer.from_dict({"urls": [None]})


def test_camera_turn_server_invalid_url_scheme() -> None:
    """ICE server URLs must use a supported scheme."""
    with pytest.raises(ValueError, match="Invalid ICE server URL scheme"):
        CameraTurnServer.from_dict({"url": "http://invalidscheme.com"})


def test_camera_turn_server_empty_url() -> None:
    """A single URL cannot be empty."""
    with pytest.raises(ValueError, match="TURN server URL cannot be empty"):
        CameraTurnServer.from_dict({"url": ""})


def test_camera_turn_server_empty_urls_list() -> None:
    """The URL list must contain at least one server."""
    with pytest.raises(ValueError, match="TURN server 'urls' list cannot be empty"):
        CameraTurnServer.from_dict({"urls": []})


def test_camera_turn_server_invalid_username_type() -> None:
    """Usernames must be strings."""
    with pytest.raises(TypeError, match="Expected str for username"):
        CameraTurnServer.from_dict({"url": "turn:example.com", "user": 123})


def test_camera_turn_server_invalid_credential_type() -> None:
    """Credentials must be strings."""
    with pytest.raises(TypeError, match="Expected str for credential"):
        CameraTurnServer.from_dict({"url": "turn:example.com", "pwd": 456})


@pytest.mark.parametrize("model", [CameraIceCandidate, CameraQuality, CameraSdpDescription, CameraTurnServer])
def test_camera_models_defined_in_data_module(model: type) -> None:
    """Camera models are defined in their discoverable data module."""
    assert model.__module__ == "roborock.data.camera"


@pytest.mark.parametrize("include_optional_fields", [False, True])
def test_camera_ice_candidate_model_roundtrip(include_optional_fields: bool) -> None:
    """The inherited serializer preserves optional values and arbitrary ICE extensions."""
    candidate = CameraIceCandidate(
        foundation="1",
        component=1,
        protocol="tcp" if include_optional_fields else "udp",
        priority=100,
        ip="1.2.3.4",
        port=5000,
        candidate_type="srflx" if include_optional_fields else "host",
        related_address="10.0.0.1" if include_optional_fields else None,
        related_port=4000 if include_optional_fields else None,
        tcp_type="active" if include_optional_fields else None,
        sdp_mid="video" if include_optional_fields else None,
        sdp_mline_index=0 if include_optional_fields else None,
        extensions={"generation": "0", "network-id": "1"} if include_optional_fields else {},
    )
    serialized = candidate.as_dict()
    assert isinstance(candidate, RoborockBase)
    assert serialized["candidateType"] == candidate.candidate_type
    assert serialized["extensions"] == candidate.extensions
    if include_optional_fields:
        assert serialized["relatedAddress"] == "10.0.0.1"
        assert serialized["relatedPort"] == 4000
        assert serialized["tcpType"] == "active"
        assert serialized["sdpMid"] == "video"
        assert serialized["sdpMlineIndex"] == 0
    else:
        assert "relatedAddress" not in serialized
        assert "relatedPort" not in serialized
        assert "tcpType" not in serialized
        assert "sdpMid" not in serialized
        assert "sdpMlineIndex" not in serialized
    assert CameraIceCandidate.from_dict(serialized) == candidate


def test_camera_ice_candidate_from_dict_converts_field_types() -> None:
    """Inherited deserialization uses concrete annotations for nested and optional values."""
    candidate = CameraIceCandidate.from_dict(
        {
            "foundation": "1",
            "component": "1",
            "protocol": "udp",
            "priority": "100",
            "ip": "1.2.3.4",
            "port": "5000",
            "candidateType": "host",
            "sdpMlineIndex": "0",
            "extensions": {"generation": 0},
        }
    )
    assert candidate.component == 1
    assert candidate.priority == 100
    assert candidate.port == 5000
    assert candidate.sdp_mline_index == 0
    assert candidate.extensions == {"generation": "0"}


@pytest.mark.parametrize("sdp_mid, sdp_mline_index", [(None, None), ("video", 1)])
def test_camera_ice_candidate_signaling_dict(sdp_mid: str | None, sdp_mline_index: int | None) -> None:
    """Signaling uses protocol field names and default media identifiers."""
    candidate = CameraIceCandidate(
        foundation="1",
        component=1,
        protocol="UDP",
        priority=100,
        ip="1.2.3.4",
        port=5000,
        candidate_type="HOST",
        sdp_mid=sdp_mid,
        sdp_mline_index=sdp_mline_index,
    )
    assert candidate.to_sdp() == "candidate:1 1 udp 100 1.2.3.4 5000 typ host"
    assert str(candidate) == candidate.to_sdp()
    assert candidate.to_signaling_dict() == {
        "candidate": candidate.to_sdp(),
        "sdpMid": sdp_mid if sdp_mid is not None else "0",
        "sdpMLineIndex": sdp_mline_index if sdp_mline_index is not None else 0,
    }


def test_camera_ice_candidate_sdp_optional_attributes() -> None:
    """Formatting preserves related address, TCP type, and extension attributes."""
    candidate = CameraIceCandidate(
        foundation="1",
        component=1,
        protocol="tcp",
        priority=100,
        ip="1.2.3.4",
        port=5000,
        candidate_type="srflx",
        related_address="10.0.0.1",
        related_port=4000,
        tcp_type="ACTIVE",
        extensions={"generation": "0", "network-id": "1"},
    )
    assert candidate.to_sdp() == (
        "candidate:1 1 tcp 100 1.2.3.4 5000 typ srflx "
        "raddr 10.0.0.1 rport 4000 tcptype active generation 0 network-id 1"
    )
    candidate.port = 9999
    assert "1.2.3.4 9999 typ srflx" in candidate.to_sdp()


@pytest.mark.parametrize("description_type", ["offer", "answer"])
def test_camera_sdp_description_roundtrip(description_type: str) -> None:
    """SDP results use the common typed model serialization contract."""
    description = CameraSdpDescription(sdp="v=0\r\n", type=description_type)
    assert isinstance(description, RoborockBase)
    assert description.as_dict() == {"sdp": "v=0\r\n", "type": description_type}
    assert CameraSdpDescription.from_dict(description.as_dict()) == description


def test_camera_turn_server_as_dict_roundtrip() -> None:
    """The inherited serializer exports standard WebRTC configuration without alias helpers."""
    server = CameraTurnServer(
        urls=["turn:turn.example.com:3478"],
        username="user",
        credential="secret_password",
    )
    serialized = server.as_dict()
    assert serialized == {
        "urls": ["turn:turn.example.com:3478"],
        "username": "user",
        "credential": "secret_password",
    }
    assert CameraTurnServer.from_dict(serialized) == server
    assert "secret_password" not in repr(server)
    serialized["urls"].append("stun:stun.example.com:3478")
    assert server.urls == ["turn:turn.example.com:3478"]

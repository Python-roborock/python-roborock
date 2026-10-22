"""Data models for Roborock camera live view."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self

from .containers import RoborockBase

__all__ = ["CameraIceCandidate", "CameraQuality", "CameraSdpDescription", "CameraTurnServer"]

_VALID_TURN_SCHEMES = ("turn:", "turns:", "stun:", "stuns:")


class CameraQuality(StrEnum):
    """Camera video streaming resolution setting."""

    HD = "HD"
    SD = "SD"
    FHD = "FHD"
    AUTO = "auto"

    @classmethod
    def from_str(cls, value: str) -> Self:
        """Parse CameraQuality case-insensitively."""
        normalized = value.strip()
        # "auto" is lowercase in the Roborock app enum, while HD/SD/FHD are uppercase
        for member in cls:
            if member.value.lower() == normalized.lower():
                return member
        valid = ", ".join(repr(m.value) for m in cls)
        raise ValueError(f"Invalid camera quality: {value!r}. Expected one of {valid}.")


@dataclass
class CameraTurnServer(RoborockBase):
    """Ephemeral TURN server credentials for WebRTC peer connection relay."""

    urls: list[str]
    username: str | None = None
    credential: str | None = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | list[dict[str, Any]]) -> Self:
        """Create CameraTurnServer from get_turn_server response or dict.

        Handles both device RPC responses (single-item list or dict with 'url', 'user', 'pwd')
        and standard WebRTC configuration dicts ('urls', 'username', 'credential').
        """
        if isinstance(data, list):
            if not data:
                raise ValueError("Empty TURN server data list")
            item = data[0]
            if not isinstance(item, dict):
                raise TypeError(f"Expected dict inside TURN server list, got {type(item).__name__}")
            data = item
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict or list of dicts for TURN server, got {type(data).__name__}")

        if "urls" in data:
            urls_val = data["urls"]
        elif "url" in data:
            urls_val = data["url"]
        else:
            raise ValueError("Missing 'url' or 'urls' in TURN server response")

        urls: list[str] = []
        if isinstance(urls_val, str):
            urls_clean = urls_val.strip()
            if not urls_clean:
                raise ValueError("TURN server URL cannot be empty")
            urls = [urls_clean]
        elif isinstance(urls_val, list):
            if not urls_val:
                raise ValueError("TURN server 'urls' list cannot be empty")
            for u in urls_val:
                if not isinstance(u, str) or not u.strip():
                    raise ValueError(f"Each URL in 'urls' must be a non-empty string, got {u!r}")
                urls.append(u.strip())
        else:
            raise TypeError(f"Expected str or list for urls, got {type(urls_val).__name__}")

        # Validate URL scheme (stun:, stuns:, turn:, turns:)
        for u in urls:
            if not any(u.lower().startswith(scheme) for scheme in _VALID_TURN_SCHEMES):
                raise ValueError(f"Invalid ICE server URL scheme in {u!r}. Expected turn:, turns:, stun:, or stuns:")

        user_val = data.get("username") if "username" in data else data.get("user")
        pwd_val = data.get("credential") if "credential" in data else data.get("pwd")

        if user_val is not None and not isinstance(user_val, str):
            raise TypeError(f"Expected str for username, got {type(user_val).__name__}")
        if pwd_val is not None and not isinstance(pwd_val, str):
            raise TypeError(f"Expected str for credential, got {type(pwd_val).__name__}")

        return cls(
            urls=urls,
            username=user_val,
            credential=pwd_val,
        )


@dataclass
class CameraIceCandidate(RoborockBase):
    """Parsed WebRTC ICE candidate representation (RFC 5245 / RFC 8839)."""

    foundation: str
    component: int
    protocol: str
    priority: int
    ip: str
    port: int
    candidate_type: str
    related_address: str | None = None
    related_port: int | None = None
    tcp_type: str | None = None
    sdp_mid: str | None = None
    sdp_mline_index: int | None = None
    extensions: dict[str, str] = field(default_factory=dict)

    def to_sdp(self) -> str:
        """Format candidate as an SDP attribute line value (RFC 5245 / RFC 8839)."""
        parts = [
            f"candidate:{self.foundation}",
            str(self.component),
            self.protocol.lower(),
            str(self.priority),
            self.ip,
            str(self.port),
            "typ",
            self.candidate_type.lower(),
        ]
        if self.related_address is not None and self.related_port is not None:
            parts.extend(["raddr", self.related_address, "rport", str(self.related_port)])
        if self.tcp_type is not None:
            parts.extend(["tcptype", self.tcp_type.lower()])
        for ext_k, ext_v in self.extensions.items():
            parts.extend([ext_k, ext_v])
        return " ".join(parts)

    def to_signaling_dict(self) -> dict[str, str | int]:
        """Convert to Roborock camera signaling dictionary format."""
        return {
            "candidate": self.to_sdp(),
            "sdpMid": self.sdp_mid if self.sdp_mid is not None else "0",
            "sdpMLineIndex": self.sdp_mline_index if self.sdp_mline_index is not None else 0,
        }

    def __str__(self) -> str:
        """Return the SDP candidate string."""
        return self.to_sdp()


@dataclass
class CameraSdpDescription(RoborockBase):
    """WebRTC session description exchanged during camera signaling."""

    sdp: str
    type: str

"""Camera signaling models, ICE parsing utilities, and payload serialization for Roborock vacuums.

This module provides data models and helpers for Roborock camera live view WebRTC
signaling, including TURN server mapping, ICE candidate parsing/formatting,
password hashing, and base64-JSON payload encoding/decoding.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self

from .data.containers import RoborockBase

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "CameraIceCandidate",
    "CameraQuality",
    "CameraTurnServer",
    "decode_ice_candidates",
    "decode_sdp_answer",
    "encode_ice_candidate",
    "encode_sdp_offer",
    "hash_camera_password",
    "parse_ice_candidate",
]

# RFC 5245 / RFC 8839: foundation is 1 to 32 ice-char (ALPHA / DIGIT / "+" / "/" / "-" / "_")
_ICE_FOUNDATION_PATTERN = re.compile(r"^[A-Za-z0-9+/_\-]{1,32}$")
_VALID_TCP_TYPES = frozenset({"active", "passive", "so"})
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
        if not isinstance(value, str):
            raise TypeError(f"Expected str for camera quality, got {type(value).__name__}")
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to standard WebRTC RTCIceServer configuration dictionary."""
        result: dict[str, Any] = {"urls": list(self.urls)}
        if self.username is not None:
            result["username"] = self.username
        if self.credential is not None:
            result["credential"] = self.credential
        return result


@dataclass
class CameraIceCandidate:
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

    def to_signaling_dict(self) -> dict[str, Any]:
        """Convert to Roborock camera signaling dictionary format."""
        return {
            "candidate": self.to_sdp(),
            "sdpMid": self.sdp_mid if self.sdp_mid is not None else "0",
            "sdpMLineIndex": self.sdp_mline_index if self.sdp_mline_index is not None else 0,
        }

    def __str__(self) -> str:
        """Return the SDP candidate string."""
        return self.to_sdp()


def parse_ice_candidate(
    candidate_str: str,
    sdp_mid: str | None = None,
    sdp_mline_index: int | None = None,
) -> CameraIceCandidate:
    """Parse a raw SDP candidate string into a CameraIceCandidate object.

    Handles standard candidate strings with optional 'a=' or 'candidate:' prefixes,
    IPv4, IPv6, and FQDN/mDNS addresses, transport protocols, candidate types, and
    optional extension attributes such as raddr, rport, tcptype, generation, etc.
    """
    if not isinstance(candidate_str, str):
        raise TypeError(f"Expected str for ICE candidate, got {type(candidate_str).__name__}")

    cand_clean = candidate_str.rstrip("\r\n").strip()
    if not cand_clean:
        raise ValueError("Empty ICE candidate string")

    tokens_str = cand_clean
    if tokens_str.startswith("a="):
        tokens_str = tokens_str[2:].strip()
    if tokens_str.startswith("candidate:"):
        tokens_str = tokens_str[10:].strip()

    tokens = tokens_str.split()
    if len(tokens) < 8:
        raise ValueError(f"Malformed ICE candidate string (expected at least 8 tokens): {candidate_str!r}")

    foundation = tokens[0]
    if not _ICE_FOUNDATION_PATTERN.match(foundation):
        raise ValueError(f"Invalid ICE foundation {foundation!r}: must be 1-32 ice characters")

    component_str = tokens[1]
    if not (component_str.isascii() and component_str.isdigit()):
        raise ValueError(f"Invalid ICE component {component_str!r}: must be ASCII decimal digits")
    component = int(component_str)
    if not (1 <= component <= 256):
        raise ValueError(f"ICE component {component} out of valid RFC 8839 range [1, 256]")

    protocol = tokens[2].lower()

    priority_str = tokens[3]
    if not (priority_str.isascii() and priority_str.isdigit()):
        raise ValueError(f"Invalid ICE priority {priority_str!r}: must be ASCII decimal digits")
    priority = int(priority_str)
    if not (1 <= priority <= 2147483647):
        raise ValueError(f"ICE priority {priority} out of valid RFC 8445 range [1, 2147483647]")

    ip = tokens[4]

    port_str = tokens[5]
    if not (port_str.isascii() and port_str.isdigit()):
        raise ValueError(f"Invalid ICE port {port_str!r}: must be ASCII decimal digits")
    port = int(port_str)
    if not (0 <= port <= 65535):
        raise ValueError(f"ICE port {port} out of valid range [0, 65535]")

    typ_keyword = tokens[6].lower()
    if typ_keyword != "typ":
        raise ValueError(
            f"Malformed ICE candidate string (expected 'typ' keyword at position 7, got {tokens[6]!r}): "
            f"{candidate_str!r}"
        )

    cand_type = tokens[7].lower()

    related_address: str | None = None
    related_port: int | None = None
    tcp_type: str | None = None
    extensions: dict[str, str] = {}

    if (len(tokens) - 8) % 2 != 0:
        raise ValueError(
            f"Malformed ICE candidate extension attributes: odd number of tokens ({len(tokens) - 8}) "
            f"after candidate type: {candidate_str!r}"
        )

    i = 8
    while i < len(tokens):
        attr_name = tokens[i].lower()
        attr_val = tokens[i + 1]
        if attr_name == "raddr":
            related_address = attr_val
        elif attr_name == "rport":
            if not (attr_val.isascii() and attr_val.isdigit()):
                raise ValueError(f"Invalid ICE related port {attr_val!r}: must be ASCII decimal digits")
            related_port = int(attr_val)
            if not (0 <= related_port <= 65535):
                raise ValueError(f"ICE related port {related_port} out of valid range [0, 65535]")
        elif attr_name == "tcptype":
            tcp_type = attr_val.lower()
            if tcp_type not in _VALID_TCP_TYPES:
                raise ValueError(f"Invalid ICE TCP type {attr_val!r}: expected 'active', 'passive', or 'so'")
        else:
            extensions[tokens[i]] = attr_val
        i += 2

    # Invariants for related address / related port:
    if (related_address is not None and related_port is None) or (related_address is None and related_port is not None):
        raise ValueError("ICE candidate must have both 'raddr' and 'rport' specified together")

    # Invariants for TCP candidates:
    if protocol == "tcp" and tcp_type is None:
        raise ValueError("TCP ICE candidate must specify 'tcptype' attribute (RFC 6544)")

    return CameraIceCandidate(
        foundation=foundation,
        component=component,
        protocol=protocol,
        priority=priority,
        ip=ip,
        port=port,
        candidate_type=cand_type,
        related_address=related_address,
        related_port=related_port,
        tcp_type=tcp_type,
        sdp_mid=sdp_mid,
        sdp_mline_index=sdp_mline_index,
        extensions=extensions,
    )


def hash_camera_password(password: str) -> str:
    """Derive the lowercase hexadecimal MD5 digest of camera password digits.

    The Roborock camera password is a PIN or 3x3 pattern lock represented as
    a sequence of numeric ASCII digits (e.g. '1234').
    """
    if not isinstance(password, str):
        raise TypeError(f"Camera password must be a str, got {type(password).__name__}")

    password_str = password.strip()
    if not password_str:
        raise ValueError("Camera password cannot be empty")
    if not (password_str.isascii() and password_str.isdigit()):
        raise ValueError(f"Camera password must contain only ASCII digits, got {password!r}")

    return hashlib.md5(password_str.encode("utf-8"), usedforsecurity=False).hexdigest()


def encode_sdp_offer(sdp: str | dict[str, Any]) -> str:
    """Package an SDP offer into a base64-encoded UTF-8 JSON payload for send_sdp_to_robot.

    Accepts an SDP description string or a dict containing an 'sdp' key.
    Returns the base64-encoded string to be passed under the 'app_sdp' parameter.
    """
    sdp_str: str
    if isinstance(sdp, str):
        if not sdp.strip():
            raise ValueError("SDP offer string cannot be empty")
        sdp_str = sdp
    elif isinstance(sdp, dict):
        if "sdp" not in sdp or not isinstance(sdp["sdp"], str):
            raise ValueError("SDP dictionary must contain a non-empty string 'sdp' key")
        if not sdp["sdp"].strip():
            raise ValueError("SDP offer string cannot be empty")
        offer_type = sdp.get("type", "offer")
        if not isinstance(offer_type, str) or offer_type.lower() != "offer":
            raise ValueError(f"SDP offer payload type must be 'offer', got {offer_type!r}")
        sdp_str = sdp["sdp"]
    else:
        raise TypeError(f"Expected str or dict for SDP offer, got {type(sdp).__name__}")

    payload = {"sdp": sdp_str, "type": "offer"}
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def decode_sdp_answer(payload: str | dict[str, Any] | list[Any]) -> dict[str, str] | None:
    """Unpackage a base64-encoded UTF-8 JSON SDP answer payload from get_device_sdp.

    Accepts the raw device response list/dict (e.g. [{'dev_sdp': '...'}]) or a base64 string.
    Returns a dictionary with 'sdp' and 'type' keys, or None if the device returned 'retry'.
    """
    raw_b64: str
    if isinstance(payload, list):
        if not payload:
            raise ValueError("Empty response list for SDP answer")
        item = payload[0]
        if not isinstance(item, dict):
            raise TypeError(f"Expected dict inside SDP answer list, got {type(item).__name__}")
        payload = item
    if isinstance(payload, dict):
        if "dev_sdp" in payload:
            val = payload["dev_sdp"]
            if not isinstance(val, str):
                raise TypeError(f"Expected str for 'dev_sdp', got {type(val).__name__}")
            raw_b64 = val
        elif "sdp" in payload:
            sdp_val = payload["sdp"]
            if not isinstance(sdp_val, str) or not sdp_val.strip():
                raise ValueError(f"SDP dictionary missing or empty 'sdp' string: {payload}")
            ans_type = payload.get("type", "answer")
            if not isinstance(ans_type, str) or ans_type.lower() not in ("answer", "pranswer"):
                raise ValueError(f"SDP answer has invalid 'type': {ans_type!r}")
            return {"sdp": sdp_val, "type": ans_type.lower()}
        else:
            raise ValueError(f"Dictionary missing 'dev_sdp' or 'sdp' key: {payload}")
    elif isinstance(payload, str):
        raw_b64 = payload
    else:
        raise TypeError(f"Expected str, dict, or list for SDP answer payload, got {type(payload).__name__}")

    raw_b64 = raw_b64.strip()
    if raw_b64 == "retry":
        return None

    try:
        json_bytes = base64.b64decode(raw_b64, validate=True)
        data = json.loads(json_bytes.decode("utf-8"))
    except (binascii.Error, ValueError, json.JSONDecodeError, UnicodeDecodeError) as err:
        raise ValueError(f"Failed to decode base64 JSON SDP answer: {err}") from err

    if not isinstance(data, dict):
        raise ValueError(f"Decoded SDP answer JSON must be an object, got {type(data).__name__}")

    if "sdp" not in data or not isinstance(data["sdp"], str) or not data["sdp"].strip():
        raise ValueError(f"Decoded SDP answer missing or empty 'sdp' field: {data}")

    answer_type = data.get("type", "answer")
    if not isinstance(answer_type, str) or answer_type.lower() not in ("answer", "pranswer"):
        raise ValueError(f"Decoded SDP answer has invalid 'type': {answer_type!r}")

    return {
        "sdp": data["sdp"],
        "type": answer_type.lower(),
    }


def encode_ice_candidate(
    candidate: CameraIceCandidate | str | dict[str, Any],
    sdp_mid: str | None = None,
    sdp_mline_index: int | None = None,
) -> str:
    """Package an ICE candidate into a base64-encoded UTF-8 JSON payload for send_ice_to_robot.

    Accepts a CameraIceCandidate, raw candidate string, or dict.
    Returns the base64-encoded string to be passed under the 'app_ice' parameter.
    """
    if isinstance(candidate, CameraIceCandidate):
        # Override mid/mline if explicitly passed to encode_ice_candidate
        payload = candidate.to_signaling_dict()
        if sdp_mid is not None:
            payload["sdpMid"] = str(sdp_mid)
        if sdp_mline_index is not None:
            if not isinstance(sdp_mline_index, int):
                try:
                    sdp_mline_index = int(sdp_mline_index)
                except (ValueError, TypeError) as err:
                    raise ValueError(f"Invalid sdpMLineIndex {sdp_mline_index!r}: must be an integer") from err
            payload["sdpMLineIndex"] = sdp_mline_index
    elif isinstance(candidate, dict):
        cand_val = candidate.get("candidate")
        if not isinstance(cand_val, str) or not cand_val.strip():
            raise ValueError(f"Candidate dict missing or invalid 'candidate' string: {candidate}")
        candidate_str = cand_val.strip()
        mid = sdp_mid if sdp_mid is not None else candidate.get("sdpMid")
        mline = sdp_mline_index if sdp_mline_index is not None else candidate.get("sdpMLineIndex")
        if not candidate_str.startswith("candidate:"):
            candidate_str = f"candidate:{candidate_str}"
        if mline is not None and not isinstance(mline, int):
            try:
                mline = int(mline)
            except (ValueError, TypeError) as err:
                raise ValueError(f"Invalid sdpMLineIndex {mline!r}: must be an integer") from err
        payload = {
            "candidate": candidate_str,
            "sdpMid": str(mid) if mid is not None else "0",
            "sdpMLineIndex": mline if mline is not None else 0,
        }
    elif isinstance(candidate, str):
        candidate_str = candidate.strip()
        if not candidate_str:
            raise ValueError("ICE candidate string cannot be empty")
        if not candidate_str.startswith("candidate:"):
            candidate_str = f"candidate:{candidate_str}"
        mline = sdp_mline_index
        if mline is not None and not isinstance(mline, int):
            try:
                mline = int(mline)
            except (ValueError, TypeError) as err:
                raise ValueError(f"Invalid sdpMLineIndex {mline!r}: must be an integer") from err
        payload = {
            "candidate": candidate_str,
            "sdpMid": str(sdp_mid) if sdp_mid is not None else "0",
            "sdpMLineIndex": mline if mline is not None else 0,
        }
    else:
        raise TypeError(f"Expected CameraIceCandidate, dict, or str, got {type(candidate).__name__}")

    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def decode_ice_candidates(
    payload: str | list[Any] | dict[str, Any],
    *,
    ignore_invalid: bool = False,
) -> list[CameraIceCandidate]:
    """Unpackage base64-encoded UTF-8 JSON remote ICE candidates from get_device_ice.

    Accepts the raw device response list/dict (e.g. [{'dev_ice': ['...']}]) or a list of base64 strings.
    Returns a list of parsed CameraIceCandidate objects.
    If ignore_invalid is True, invalid candidates are logged and skipped rather than raising ValueError or TypeError.
    """
    raw_list: list[Any]
    if isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict) and "dev_ice" in payload[0]:
            dev_ice_val = payload[0]["dev_ice"]
            if not isinstance(dev_ice_val, list):
                raise TypeError(f"Expected list in 'dev_ice', got {type(dev_ice_val).__name__}")
            raw_list = dev_ice_val
        else:
            raw_list = payload
    elif isinstance(payload, dict):
        if "dev_ice" in payload:
            dev_ice_val = payload["dev_ice"]
            if not isinstance(dev_ice_val, list):
                raise TypeError(f"Expected list in 'dev_ice', got {type(dev_ice_val).__name__}")
            raw_list = dev_ice_val
        else:
            raw_list = [payload]
    elif isinstance(payload, str):
        raw_list = [payload]
    else:
        raise TypeError(f"Expected str, list, or dict for ICE candidates payload, got {type(payload).__name__}")

    candidates: list[CameraIceCandidate] = []
    for item in raw_list:
        if isinstance(item, CameraIceCandidate):
            candidates.append(item)
            continue
        if isinstance(item, dict):
            cand_val = item.get("candidate")
            if not isinstance(cand_val, str) or not cand_val.strip():
                if ignore_invalid:
                    _LOGGER.warning("Skipping candidate dict missing 'candidate' string: %s", item)
                    continue
                raise ValueError(f"Candidate dict missing 'candidate' string: {item}")
            mid = item.get("sdpMid")
            mline = item.get("sdpMLineIndex")
            try:
                mline_int: int | None = None
                if mline is not None:
                    mline_int = int(mline)
                candidates.append(
                    parse_ice_candidate(
                        cand_val,
                        sdp_mid=str(mid) if mid is not None else None,
                        sdp_mline_index=mline_int,
                    )
                )
            except (ValueError, TypeError) as err:
                if ignore_invalid:
                    _LOGGER.warning("Skipping invalid ICE candidate: %s", err)
                    continue
                raise
            continue
        if isinstance(item, str):
            item_str = item.strip()
            if not item_str:
                continue
            cand_str_to_parse: str = item_str
            sdp_mid_to_parse: str | None = None
            sdp_mline_to_parse: int | None = None
            try:
                decoded_bytes = base64.b64decode(item_str, validate=True)
                data = json.loads(decoded_bytes.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(f"Decoded candidate JSON must be a dict object, got {type(data).__name__}")
                if "candidate" not in data or not isinstance(data["candidate"], str):
                    raise ValueError(f"Decoded candidate JSON missing 'candidate' string: {data}")
                cand_str_to_parse = data["candidate"]
                mid = data.get("sdpMid")
                mline = data.get("sdpMLineIndex")
                sdp_mid_to_parse = str(mid) if mid is not None else None
                sdp_mline_to_parse = int(mline) if mline is not None else None
            except (binascii.Error, ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError) as err:
                # If this was clearly an attempted base64 JSON payload (starts with 'ey'),
                # or valid base64 that decoded to non-dict, do not fall back to treating it as raw candidate
                if item_str.startswith("ey") or (
                    not isinstance(err, binascii.Error) and not isinstance(err, UnicodeDecodeError)
                ):
                    if ignore_invalid:
                        _LOGGER.warning("Skipping invalid base64 JSON ICE candidate payload: %s", err)
                        continue
                    raise ValueError(f"Failed to decode base64 JSON ICE candidate: {err}") from err
                cand_str_to_parse = item_str

            try:
                candidates.append(
                    parse_ice_candidate(
                        cand_str_to_parse,
                        sdp_mid=sdp_mid_to_parse,
                        sdp_mline_index=sdp_mline_to_parse,
                    )
                )
            except (ValueError, TypeError) as err:
                if ignore_invalid:
                    _LOGGER.warning("Skipping invalid ICE candidate: %s", err)
                    continue
                raise
            continue

        raise TypeError(f"Unexpected candidate item type: {type(item).__name__}")

    return candidates

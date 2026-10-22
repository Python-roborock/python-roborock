"""V1 camera WebRTC signaling, ICE parsing, and payload serialization."""

import base64
import hashlib
import json
import logging
import re
from typing import Any

from roborock.data.camera import CameraIceCandidate, CameraSdpDescription
from roborock.exceptions import RoborockParsingException
from roborock.roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "decode_ice_candidates",
    "decode_sdp_answer",
    "encode_ice_candidate",
    "encode_sdp_offer",
    "hash_camera_password",
    "parse_ice_candidate",
]

# RFC 5245 / RFC 8839: foundation is 1 to 32 ice characters.
_ICE_FOUNDATION_PATTERN = re.compile(r"^[A-Za-z0-9+/_\-]{1,32}$")
_VALID_TCP_TYPES = frozenset({"active", "passive", "so"})


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
    password_str = password.strip()
    if not password_str:
        raise ValueError("Camera password cannot be empty")
    if not (password_str.isascii() and password_str.isdigit()):
        raise ValueError("Camera password must contain only ASCII digits")

    return hashlib.md5(password_str.encode("utf-8"), usedforsecurity=False).hexdigest()


def encode_sdp_offer(sdp: str) -> str:
    """Encode an SDP offer for the ``send_sdp_to_robot`` app_sdp parameter."""
    if not sdp.strip():
        raise ValueError("SDP offer string cannot be empty")
    payload = CameraSdpDescription(sdp=sdp, type="offer")
    json_bytes = json.dumps(payload.as_dict(), separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def decode_sdp_answer(payload: str | dict[str, Any] | list[Any]) -> CameraSdpDescription | None:
    """Decode a get_device_sdp response, returning None for a pending ``retry``.

    Accept a base64 JSON string, its dev_sdp RPC envelope, or an already decoded
    description. Preserve the SDP exactly, including CRLF line endings.
    Malformed responses raise RoborockParsingException with redacted context.
    """
    context = {"type": type(payload).__name__}
    stage = "response envelope"
    try:
        if isinstance(payload, list):
            if not payload:
                raise ValueError("Empty response list for SDP answer")
            item = payload[0]
            if not isinstance(item, dict):
                raise TypeError(f"Expected dict inside SDP answer list, got {type(item).__name__}")
            payload = item

        data: Any
        if isinstance(payload, dict) and "sdp" in payload and "dev_sdp" not in payload:
            data = payload
        else:
            raw_b64: str
            if isinstance(payload, dict):
                if "dev_sdp" not in payload:
                    raise ValueError("Dictionary missing 'dev_sdp' or 'sdp' key")
                raw = payload["dev_sdp"]
                if not isinstance(raw, str):
                    raise TypeError(f"Expected str for 'dev_sdp', got {type(raw).__name__}")
                raw_b64 = raw
            elif isinstance(payload, str):
                raw_b64 = payload
            else:
                raise TypeError(f"Expected str, dict, or list for SDP answer payload, got {type(payload).__name__}")

            raw_b64 = raw_b64.strip()
            if raw_b64 == "retry":
                return None
            stage = "base64 JSON payload"
            data = json.loads(base64.b64decode(raw_b64, validate=True).decode("utf-8"))

        stage = "SDP description fields"
        if not isinstance(data, dict):
            raise ValueError(f"Decoded SDP answer JSON must be an object, got {type(data).__name__}")
        sdp = data.get("sdp")
        if not isinstance(sdp, str) or not sdp.strip():
            raise ValueError("SDP answer missing or empty 'sdp' field")
        answer_type = data.get("type", "answer")
        if not isinstance(answer_type, str) or answer_type.lower() not in ("answer", "pranswer"):
            raise ValueError("SDP answer has invalid 'type': expected answer or pranswer")
        return CameraSdpDescription(sdp=sdp, type=answer_type.lower())
    except (ValueError, TypeError) as err:
        raise RoborockParsingException(
            trait_name="CameraSignaling",
            command=RoborockCommand.GET_DEVICE_SDP,
            payload=context,
            inner_error=f"Invalid {stage} ({type(err).__name__})",
        ) from err


def encode_ice_candidate(candidate: CameraIceCandidate) -> str:
    """Encode a candidate for the ``send_ice_to_robot`` app_ice parameter.

    Set SDP media identifiers on the candidate before encoding. Missing identifiers
    use the device defaults, sdpMid="0" and sdpMLineIndex=0.
    """
    json_bytes = json.dumps(candidate.to_signaling_dict(), separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def decode_ice_candidates(
    payload: str | list[Any] | dict[str, Any],
    *,
    ignore_invalid: bool = False,
) -> list[CameraIceCandidate]:
    """Decode get_device_ice base64 JSON candidates or their dev_ice RPC envelope.

    Raw SDP belongs in parse_ice_candidate(). With ignore_invalid=True, skip
    malformed candidate entries; malformed response envelopes still raise.
    Malformed responses raise RoborockParsingException with redacted context.
    """
    context: dict[str, str | int] = {"type": type(payload).__name__}
    stage = "response envelope"
    try:
        if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict) and "dev_ice" in payload[0]:
            payload = payload[0]

        raw_list: list[Any]
        if isinstance(payload, dict):
            if "dev_ice" not in payload:
                raise ValueError("ICE response dictionary missing 'dev_ice' list")
            entries = payload["dev_ice"]
            if not isinstance(entries, list):
                raise TypeError(f"Expected list in 'dev_ice', got {type(entries).__name__}")
            raw_list = entries
        elif isinstance(payload, list):
            raw_list = payload
        elif isinstance(payload, str):
            raw_list = [payload]
        else:
            raise TypeError(f"Expected str, list, or dict for ICE candidates payload, got {type(payload).__name__}")

        candidates: list[CameraIceCandidate] = []
        for index, item in enumerate(raw_list):
            context["candidate_index"] = index
            stage = "base64 JSON candidate"
            try:
                if not isinstance(item, str):
                    raise TypeError(f"Expected base64 JSON ICE candidate string, got {type(item).__name__}")
                data = json.loads(base64.b64decode(item.strip(), validate=True).decode("utf-8"))
                stage = "ICE candidate fields"
                if not isinstance(data, dict):
                    raise ValueError("Decoded ICE candidate JSON must be an object")
                candidate = data.get("candidate")
                if not isinstance(candidate, str) or not candidate.strip():
                    raise ValueError("Decoded ICE candidate JSON missing or empty 'candidate' string")
                mid = data.get("sdpMid")
                if mid is not None and not isinstance(mid, str):
                    raise TypeError("ICE candidate sdpMid must be a string or null")
                mline = data.get("sdpMLineIndex")
                if mline is not None and (not isinstance(mline, int) or isinstance(mline, bool)):
                    raise TypeError("ICE candidate sdpMLineIndex must be an integer or null")
                if mline is not None and mline < 0:
                    raise ValueError("ICE candidate sdpMLineIndex cannot be negative")
                stage = "SDP candidate string"
                candidates.append(parse_ice_candidate(candidate, sdp_mid=mid, sdp_mline_index=mline))
            except (ValueError, TypeError) as err:
                if not ignore_invalid:
                    raise
                _LOGGER.warning("Skipping invalid ICE candidate at index %d (%s)", index, type(err).__name__)

        return candidates
    except (ValueError, TypeError) as err:
        raise RoborockParsingException(
            trait_name="CameraSignaling",
            command=RoborockCommand.GET_DEVICE_ICE,
            payload=context,
            inner_error=f"Invalid {stage} ({type(err).__name__})",
        ) from err

"""Roborock B01 Protocol encoding and decoding."""

import base64
import binascii
import hashlib
import json
import logging
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock import RoborockB01Q7Methods
from roborock.exceptions import RoborockException
from roborock.protocol import Utils
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)
from roborock.util import get_next_int

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
B01_Q7_DPS = 10000
CommandType = RoborockB01Q7Methods | str
ParamsType = list | dict | int | None


@dataclass
class Q7RequestMessage:
    """Data class for B01 Q7 request message."""

    dps: int
    command: CommandType
    params: ParamsType
    msg_id: int = field(default_factory=lambda: get_next_int(100000000000, 999999999999))

    def to_dps_value(self) -> dict[int, Any]:
        """Return the 'dps' payload dictionary."""
        return {
            self.dps: {
                "method": str(self.command),
                "msgId": str(self.msg_id),
                # Important: some B01 methods use an empty object `{}` (not `[]`) for
                # "no params", and some setters legitimately send `0` which is falsy.
                # Only default to `[]` when params is actually None.
                "params": self.params if self.params is not None else [],
            }
        }


def encode_mqtt_payload(request: Q7RequestMessage) -> RoborockMessage:
    """Encode payload for B01 commands over MQTT."""
    dps_data = {"dps": request.to_dps_value()}
    payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=payload,
    )


def decode_rpc_response(message: RoborockMessage) -> dict[int, Any]:
    """Decode a B01 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid B01 message format: missing payload")
    try:
        unpadded = unpad(message.payload, AES.block_size)
    except ValueError:
        # It would be better to fail down the line.
        unpadded = message.payload

    try:
        payload = json.loads(unpadded.decode())
    except (json.JSONDecodeError, TypeError) as e:
        raise RoborockException(f"Invalid B01 message payload: {e} for {message.payload!r}") from e

    datapoints = payload.get("dps", {})
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid B01 message format: 'dps' should be a dictionary for {message.payload!r}")
    try:
        return {int(key): value for key, value in datapoints.items()}
    except ValueError as err:
        raise RoborockException(
            f"Invalid B01 message format: 'dps' key should be an integer for {message.payload!r}"
        ) from err


@dataclass
class MapKey:
    """Data class for holding a B01 map decryption key."""

    key: bytes


def create_map_key(serial: str, model: str) -> MapKey:
    """Derive the B01/Q7 map decrypt key from serial + model."""
    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = Utils.encrypt_ecb(material, model_key)
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return MapKey(key=md5[8:24].encode())


def decode_map_payload(raw_payload: bytes, map_key: MapKey) -> bytes:
    """Decode raw B01 `MAP_RESPONSE` payload into inflated SCMap bytes."""
    encrypted_payload = _decode_base64_payload(raw_payload)
    payload_len = len(encrypted_payload)
    if payload_len % AES.block_size != 0:
        raise RoborockException(
            f"Unexpected encrypted B01 map payload length: {payload_len} (not a multiple of AES block size)"
        )

    try:
        compressed_hex = Utils.decrypt_ecb(encrypted_payload, token=map_key.key).decode("ascii")
        compressed_payload = bytes.fromhex(compressed_hex)
        return zlib.decompress(compressed_payload)
    except (ValueError, UnicodeDecodeError, zlib.error) as err:
        raise RoborockException("Failed to decode B01 map payload") from err


def _decode_base64_payload(raw_payload: bytes) -> bytes:
    """Decode base64 payload."""

    blob = raw_payload.strip()
    padded = blob + b"=" * (-len(blob) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except binascii.Error as err:
        raise RoborockException("Failed to decode B01 map payload") from err


# Number of incomplete multi-part map responses kept while waiting for missing parts.
_MAX_PENDING_MAP_RESPONSES = 4


def create_map_response_assembler() -> Callable[[RoborockMessage], bytes | None]:
    """Create an assembler for B01 map response messages.

    Large maps are split into multiple messages that share the same ``random``
    and ``timestamp`` and are numbered by ``seq``. All parts except the last
    one use protocol ``MAP_RESPONSE_PART`` (300), the last one uses
    ``MAP_RESPONSE`` (301). Parts may arrive out of order, so they are buffered
    until complete. A lone final part whose decoded length is not a multiple of
    the AES block size is a trailing fragment of a split frame, not a complete
    frame, so it is buffered too. This ports the V1 reassembly from #1004.
    """
    # (random, timestamp) -> seq -> (is last part, raw payload)
    pending: dict[tuple[int, int], dict[int, tuple[bool, bytes]]] = {}

    def _decoded_length(raw_payload: bytes) -> int | None:
        try:
            return len(_decode_base64_payload(raw_payload))
        except RoborockException:
            return None

    def _remember(key: tuple[int, int], parts: dict[int, tuple[bool, bytes]]) -> None:
        pending[key] = parts
        while len(pending) > _MAX_PENDING_MAP_RESPONSES:
            del pending[next(iter(pending))]

    def _complete_payload(parts: dict[int, tuple[bool, bytes]]) -> bytes | None:
        seqs = sorted(parts)
        if not parts[seqs[-1]][0]:
            return None
        if seqs != list(range(seqs[0], seqs[-1] + 1)):
            return None
        joined = b"".join(parts[seq][1] for seq in seqs)
        length = _decoded_length(joined)
        if length is None or length % AES.block_size != 0:
            return None
        return joined

    def assemble(message: RoborockMessage) -> bytes | None:
        """Return the complete raw payload once all parts of a frame arrived."""
        if not message.payload:
            return None
        key = (message.random, message.timestamp)
        is_last = message.protocol == RoborockMessageProtocol.MAP_RESPONSE
        if message.protocol == RoborockMessageProtocol.MAP_RESPONSE_PART or (is_last and key in pending):
            parts = pending.pop(key, {})
            parts[message.seq] = (is_last, message.payload)
            if (joined := _complete_payload(parts)) is not None:
                return joined
            _remember(key, parts)
            return None
        if is_last:
            length = _decoded_length(message.payload)
            if length is not None and length % AES.block_size != 0:
                # Trailing fragment of a split frame whose earlier parts have
                # not arrived yet; wait for them instead of failing the decode.
                _remember(key, {message.seq: (True, message.payload)})
                return None
            return message.payload
        return None

    return assemble

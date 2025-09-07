from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from asyncio import BaseTransport, Lock

from construct import (  # type: ignore
    Bytes,
    Checksum,
    GreedyBytes,
    Int16ub,
    Int32ub,
    Prefixed,
    RawCopy,
    Struct,
)
from Crypto.Cipher import AES

from roborock import RoborockException
from roborock.containers import BroadcastMessage
from roborock.protocol import EncryptionAdapter, Utils, _Parser

_LOGGER = logging.getLogger(__name__)

BROADCAST_TOKEN = b"qWKYcdQWrbm9hPqe"


class RoborockProtocol(asyncio.DatagramProtocol):
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.transport: BaseTransport | None = None
        self.devices_found: list[BroadcastMessage] = []
        self._mutex = Lock()

    def datagram_received(self, data: bytes, _):
        """Handle incoming broadcast datagrams."""
        try:
            version = data[:3]
            if version == b"L01":
                [parsed_msg], _ = L01Parser.parse(data)
                encrypted_payload = parsed_msg.payload
                if encrypted_payload is None:
                    raise RoborockException("No encrypted payload found in broadcast message")
                ciphertext = encrypted_payload[:-16]
                tag = encrypted_payload[-16:]

                key = hashlib.sha256(BROADCAST_TOKEN).digest()
                iv_digest_input = data[:9]
                digest = hashlib.sha256(iv_digest_input).digest()
                iv = digest[:12]

                cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                decrypted_payload_bytes = cipher.decrypt_and_verify(ciphertext, tag)
                json_payload = json.loads(decrypted_payload_bytes)
                parsed_message = BroadcastMessage(duid=json_payload["duid"], ip=json_payload["ip"], version=version)
                _LOGGER.debug(f"Received L01 broadcast: {parsed_message}")
                self.devices_found.append(parsed_message)
            else:
                # Fallback to the original protocol parser for other versions
                [broadcast_message], _ = BroadcastParser.parse(data)
                if broadcast_message.payload:
                    json_payload = json.loads(broadcast_message.payload)
                    parsed_message = BroadcastMessage(duid=json_payload["duid"], ip=json_payload["ip"], version=version)
                    _LOGGER.debug(f"Received broadcast: {parsed_message}")
                    self.devices_found.append(parsed_message)
        except Exception as e:
            _LOGGER.warning(f"Failed to decode message: {data!r}. Error: {e}")

    async def discover(self) -> list[BroadcastMessage]:
        async with self._mutex:
            try:
                loop = asyncio.get_event_loop()
                self.transport, _ = await loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 58866))
                await asyncio.sleep(self.timeout)
                return self.devices_found
            finally:
                self.close()
                self.devices_found = []

    def close(self):
        self.transport.close() if self.transport else None


_BroadcastMessage = Struct(
    "message"
    / RawCopy(
        Struct(
            "version" / Bytes(3),
            "seq" / Int32ub,
            "protocol" / Int16ub,
            "payload" / EncryptionAdapter(lambda ctx: BROADCAST_TOKEN),
        )
    ),
    "checksum" / Checksum(Int32ub, Utils.crc, lambda ctx: ctx.message.data),
)

_L01BroadcastMessage = Struct(
    "message"
    / RawCopy(
        Struct(
            "version" / Bytes(3),
            "field1" / Bytes(4),  # Unknown field
            "field2" / Bytes(2),  # Unknown field
            "payload" / Prefixed(Int16ub, GreedyBytes),  # Encrypted payload with length prefix
        )
    ),
    "checksum" / Checksum(Int32ub, Utils.crc, lambda ctx: ctx.message.data),
)


BroadcastParser: _Parser = _Parser(_BroadcastMessage, False)
L01Parser: _Parser = _Parser(_L01BroadcastMessage, False)

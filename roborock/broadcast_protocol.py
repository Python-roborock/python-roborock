from __future__ import annotations

import asyncio
import json
import logging
from asyncio import BaseTransport, Lock

from construct import (  # type: ignore
    Bytes,
    Checksum,
    Int16ub,
    Int32ub,
    RawCopy,
    Struct,
)

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

    def datagram_received(self, data, _):
        [broadcast_message], _ = BroadcastParser.parse(data)
        if broadcast_message.payload:
            parsed_message = BroadcastMessage.from_dict(json.loads(broadcast_message.payload))
            _LOGGER.debug(f"Received broadcast: {parsed_message}")
            self.devices_found.append(parsed_message)

    async def discover(self):
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


BroadcastParser: _Parser = _Parser(_BroadcastMessage, False)

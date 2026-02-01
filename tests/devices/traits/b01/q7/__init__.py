import json
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


class B01MessageBuilder:
    """Helper class to build B01 RPC response messages for tests."""

    def __init__(self) -> None:
        self.msg_id = 123456789
        self.seq = 2020

    def build(self, data: dict[str, Any] | str, code: int | None = None) -> RoborockMessage:
        """Build an encoded B01 RPC response message."""
        message: dict[str, Any] = {
            "msgId": str(self.msg_id),
            "data": data,
        }
        if code is not None:
            message["code"] = code
        return self._build_dps(message)

    def _build_dps(self, message: dict[str, Any] | str) -> RoborockMessage:
        """Build an encoded B01 RPC response message."""
        dps_payload = {"dps": {"10000": json.dumps(message)}}
        self.seq += 1
        return RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=pad(
                json.dumps(dps_payload).encode(),
                AES.block_size,
            ),
            version=b"B01",
            seq=self.seq,
        )

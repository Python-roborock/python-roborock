"""Common test utils for the protocols package."""

import json
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol


def build_a01_message(message: dict[Any, Any], seq: int = 2020) -> RoborockMessage:
    """Build an encoded A01 RPC response message."""
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=pad(
            json.dumps(
                {
                    "dps": message,  # {10000: json.dumps(message)},
                }
            ).encode(),
            AES.block_size,
        ),
        version=b"A01",
        seq=seq,
    )

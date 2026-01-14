from collections.abc import Generator
from unittest.mock import patch

import pytest

from .logging import CapturedRequestLog

# Fixed timestamp for deterministic tests for asserting on message contents
FAKE_TIMESTAMP = 1755750946.721395


@pytest.fixture
def deterministic_message_fixtures() -> Generator[None, None, None]:
    """Fixture to use predictable get_next_int and timestamp values for each test.

    This test mocks out the functions used to generate requests that have some
    entropy such as the nonces, timestamps, and request IDs. This makes the
    generated messages deterministic so we can snapshot them in a test.
    """

    # Pick an arbitrary sequence number used for outgoing requests
    next_int = 9090

    def get_next_int(min_value: int, max_value: int) -> int:
        nonlocal next_int
        result = next_int
        next_int += 1
        if next_int > max_value:
            next_int = min_value
        return result

    # Pick an arbitrary timestamp used for the message encryption
    timestamp = FAKE_TIMESTAMP

    def get_timestamp() -> int:
        """Get a monotonically increasing timestamp for testing."""
        nonlocal timestamp
        timestamp += 1
        return int(timestamp)

    # Use predictable seeds for token_bytes
    token_chr = "A"

    def get_token_bytes(n: int) -> bytes:
        nonlocal token_chr
        result = token_chr.encode() * n
        # Cycle to the next character
        token_chr = chr(ord(token_chr) + 1)
        if token_chr > "Z":
            token_chr = "A"
        return result

    with (
        patch("roborock.devices.transport.local_channel.get_next_int", side_effect=get_next_int),
        patch("roborock.protocols.b01_q7_protocol.get_next_int", side_effect=get_next_int),
        patch("roborock.protocols.v1_protocol.get_next_int", side_effect=get_next_int),
        patch("roborock.protocols.v1_protocol.get_timestamp", side_effect=get_timestamp),
        patch("roborock.protocols.v1_protocol.secrets.token_bytes", side_effect=get_token_bytes),
        patch("roborock.roborock_message.get_next_int", side_effect=get_next_int),
        patch("roborock.roborock_message.get_timestamp", side_effect=get_timestamp),
    ):
        yield


@pytest.fixture(name="log")
def log_fixture(deterministic_message_fixtures: None) -> CapturedRequestLog:
    """Fixture that creates a captured request log."""
    return CapturedRequestLog()

import json

from freezegun import freeze_time

from roborock.roborock_message import MAX_PAYLOAD_REPR_LEN, RoborockMessage, RoborockMessageProtocol


def test_roborock_message() -> None:
    """Test the RoborockMessage class is initialized."""
    with freeze_time("2025-01-20T12:00:00"):
        message1 = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_REQUEST,
            payload=json.dumps({"dps": {"101": json.dumps({"id": 4321})}}).encode(),
        )

    with freeze_time("2025-01-20T11:00:00"):  # Back in time 1hr to test timestamp
        message2 = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=json.dumps({"dps": {"94": json.dumps({"id": 444}), "102": json.dumps({"id": 333})}}).encode(),
        )

    # Ensure the sequence, random numbers, etc are initialized properly
    assert message1.seq != message2.seq
    assert message1.random != message2.random
    assert message1.timestamp > message2.timestamp


def test_roborock_message_repr() -> None:
    """Test custom __repr__ of RoborockMessage truncates long payloads."""
    # 1. Payload is None
    msg_none = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=None,
        seq=123456,
        version=b"1.0",
        random=12345,
        timestamp=1700000000,
    )
    assert repr(msg_none) == (
        "RoborockMessage(protocol=101, payload=None, seq=123456, version=b'1.0', random=12345, timestamp=1700000000)"
    )

    # 2. Payload is short (<= MAX_PAYLOAD_REPR_LEN bytes)
    short_payload = b"a" * MAX_PAYLOAD_REPR_LEN
    msg_short = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=short_payload,
        seq=123456,
        version=b"1.0",
        random=12345,
        timestamp=1700000000,
    )
    assert repr(msg_short) == (
        f"RoborockMessage(protocol=101, payload={repr(short_payload)}, seq=123456, "
        "version=b'1.0', random=12345, timestamp=1700000000)"
    )

    # 3. Payload is long (> MAX_PAYLOAD_REPR_LEN bytes)
    long_payload = b"a" * (MAX_PAYLOAD_REPR_LEN + 10)
    msg_long = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=long_payload,
        seq=123456,
        version=b"1.0",
        random=12345,
        timestamp=1700000000,
    )
    expected_payload_repr = f"b'{'a' * MAX_PAYLOAD_REPR_LEN}...' (length: {MAX_PAYLOAD_REPR_LEN + 10})"
    assert repr(msg_long) == (
        f"RoborockMessage(protocol=101, payload={expected_payload_repr}, seq=123456, "
        "version=b'1.0', random=12345, timestamp=1700000000)"
    )

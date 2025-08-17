import json

from freezegun import freeze_time

from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol


def test_roborock_message() -> None:
    """Test the RoborockMessage class is initialized."""
    with freeze_time("2025-01-20T12:00:00"):
        message1 = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_REQUEST,
            payload=json.dumps({"dps": {"101": json.dumps({"id": 4321})}}).encode(),
        )
        assert message1.get_request_id() == 4321

    with freeze_time("2025-01-20T11:00:00"):  # Back in time 1hr to test timestamp
        message2 = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=json.dumps({"dps": {"94": json.dumps({"id": 444}), "102": json.dumps({"id": 333})}}).encode(),
        )
        assert message2.get_request_id() == 333

    # Ensure the sequence, random numbers, etc are initialized properly
    assert message1.seq != message2.seq
    assert message1.random != message2.random
    assert message1.timestamp > message2.timestamp

import pytest

from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TEST_LOCAL_KEY = "local_key"


@pytest.mark.parametrize(
    ("garbage"),
    [
        b"",
        b"\x00\x00\x05\xa1",
        b"\x00\x00\x05\xa1\xff\xff",
    ],
)
def test_decoder_clean_message(garbage: bytes):
    encoder = create_local_encoder(TEST_LOCAL_KEY)
    decoder = create_local_decoder(TEST_LOCAL_KEY)
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b"test_payload",
        version=b"1.0",
        seq=1,
        random=123,
    )
    encoded = encoder(msg)
    decoded = decoder(garbage + encoded)
    assert len(decoded) == 1
    assert decoded[0].payload == b"test_payload"


def test_decoder_split_padding_variable():
    """Test variable padding split across chunks."""
    encoder = create_local_encoder(TEST_LOCAL_KEY, connect_nonce=123, ack_nonce=456)
    decoder = create_local_decoder(TEST_LOCAL_KEY, connect_nonce=123, ack_nonce=456)

    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b"test_payload",
        version=b"L01",
    )
    encoded = encoder(msg)

    garbage = b"\x00\x00\x05\xa1\xff\xff"  # 6 bytes

    # Send garbage
    decoded1 = decoder(garbage)
    assert len(decoded1) == 0

    # Send message
    decoded2 = decoder(encoded)

    assert len(decoded2) == 1
    assert decoded2[0].payload == b"test_payload"

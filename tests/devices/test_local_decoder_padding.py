from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TEST_LOCAL_KEY = "local_key"


def test_decoder_clean_message():
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

    decoded = decoder(encoded)
    assert len(decoded) == 1
    assert decoded[0].payload == b"test_payload"


def test_decoder_4byte_padding():
    """Test existing behavior: 4 byte padding should be skipped."""
    encoder = create_local_encoder(TEST_LOCAL_KEY)
    decoder = create_local_decoder(TEST_LOCAL_KEY)

    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b"test_payload",
        version=b"1.0",
    )
    encoded = encoder(msg)

    # Prepend 4 bytes of garbage
    garbage = b"\x00\x00\x05\xa1"
    data = garbage + encoded

    decoded = decoder(data)
    assert len(decoded) == 1
    assert decoded[0].payload == b"test_payload"


def test_decoder_variable_padding():
    """Test proposed fix: variable length padding should be skipped."""
    encoder = create_local_encoder(TEST_LOCAL_KEY, connect_nonce=123, ack_nonce=456)
    decoder = create_local_decoder(TEST_LOCAL_KEY, connect_nonce=123, ack_nonce=456)

    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b"test_payload",
        version=b"L01",
    )
    encoded = encoder(msg)

    # Prepend 6 bytes of garbage
    garbage = b"\x00\x00\x05\xa1\xff\xff"
    data = garbage + encoded

    decoded = decoder(data)
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

from roborock.protocol import Utils


def test_encryption():
    """Tests the L01 GCM encryption logic."""
    local_key = "b8Hj5mFk3QzT7rLp"
    timestamp = 1753606905
    sequence = 1
    nonce = 304251
    connect_nonce = 893563
    ack_nonce = 485592656
    payload_str = (
        '{"dps":{"101":"{\\"id\\":1806,\\"method\\":\\"get_prop\\",\\"params\\":[\\"get_status\\"]}"},"t":1753606905}'
    )
    payload = payload_str.encode("utf-8")

    encrypted_data = Utils.encrypt_gcm_l01(
        plaintext=payload,
        local_key=local_key,
        timestamp=timestamp,
        sequence=sequence,
        nonce=nonce,
        connect_nonce=connect_nonce,
        ack_nonce=ack_nonce,
    )

    expected_data = bytes.fromhex(
        "fd60c8daca1ccae67f6077477bfa9d37189a38d75b3c4a907c2435d3c146ee84d8f99597e3e1571a015961ceaa4d64bc3695fae024c341"
        "6737d77150341de29cad2f95bfaf532358f12bbff89f140fef5b1ee284c3abfe3b83a577910a72056dab4d5a75b182d1a0cba145e3e450"
        "f3927443"
    )

    assert encrypted_data == expected_data


def test_decryption():
    """Tests the L01 GCM decryption logic."""
    local_key = "b8Hj5mFk3QzT7rLp"
    timestamp = 1753606905
    sequence = 1
    nonce = 304251
    connect_nonce = 893563
    ack_nonce = 485592656
    payload = bytes.fromhex(
        "fd60c8daca1ccae67f6077477bfa9d37189a38d75b3c4a907c2435d3c146ee84d8f99597e3e1571a015961ceaa4d64bc3695fae024c341"
        "6737d77150341de29cad2f95bfaf532358f12bbff89f140fef5b1ee284c3abfe3b83a577910a72056dab4d5a75b182d1a0cba145e3e450"
        "f3927443"
    )
    decrypted_data = Utils.decrypt_gcm_l01(
        payload=payload,
        local_key=local_key,
        timestamp=timestamp,
        sequence=sequence,
        nonce=nonce,
        connect_nonce=connect_nonce,
        ack_nonce=ack_nonce,
    )
    decrypted_str = decrypted_data.decode("utf-8")

    expected_str = (
        '{"dps":{"101":"{\\"id\\":1806,\\"method\\":\\"get_prop\\",\\"params\\":[\\"get_status\\"]}"},"t":1753606905}'
    )
    assert decrypted_str == expected_str

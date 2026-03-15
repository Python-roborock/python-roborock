import base64
import gzip
import hashlib
import io
import zlib
from pathlib import Path

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PIL import Image

from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import B01MapParser, _parse_scmap_payload

FIXTURE = Path(__file__).resolve().parent / "testdata" / "raw-mqtt-map301.bin.inflated.bin.gz"


def _derive_map_key(serial: str, model: str) -> bytes:
    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = AES.new(model_key, AES.MODE_ECB).encrypt(pad(material, AES.block_size))
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


def _encode_varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            encoded.append(to_write | 0x80)
        else:
            encoded.append(to_write)
            return bytes(encoded)


def _field_varint(field_no: int, value: int) -> bytes:
    return _encode_varint((field_no << 3) | 0) + _encode_varint(value)


def _field_len(field_no: int, value: bytes) -> bytes:
    return _encode_varint((field_no << 3) | 2) + _encode_varint(len(value)) + value


def test_b01_map_parser_decodes_and_renders_fixture() -> None:
    serial = "testsn012345"
    model = "roborock.vacuum.sc05"
    inflated = gzip.decompress(FIXTURE.read_bytes())

    compressed = zlib.compress(inflated)
    map_key = _derive_map_key(serial, model)
    encrypted = AES.new(map_key, AES.MODE_ECB).encrypt(pad(compressed.hex().encode(), AES.block_size))
    payload = base64.b64encode(encrypted)

    parser = B01MapParser()
    parsed = parser.parse(payload, serial=serial, model=model)

    assert parsed.image_content is not None
    assert parsed.image_content.startswith(b"\x89PNG\r\n\x1a\n")
    assert parsed.map_data is not None

    # The fixture includes 10 rooms with names room1..room10.
    assert parsed.map_data.additional_parameters["room_names"] == {
        10: "room1",
        11: "room2",
        12: "room3",
        13: "room4",
        14: "room5",
        15: "room6",
        16: "room7",
        17: "room8",
        18: "room9",
        19: "room10",
    }

    # Image should be scaled by default.
    img = Image.open(io.BytesIO(parsed.image_content))
    assert img.size == (340 * 4, 300 * 4)


def test_b01_scmap_parser_maps_selected_reverse_engineered_fields() -> None:
    room_one = b"".join([
        _field_varint(1, 42),
        _field_len(2, b"Kitchen"),
        _field_varint(5, 1),
    ])
    room_two = b"".join([
        _field_varint(1, 99),
    ])

    map_head = b"".join([
        _field_varint(1, 7),
        _field_varint(2, 2),
        _field_varint(3, 2),
        _field_varint(9, 999),
    ])
    map_data = _field_len(1, zlib.compress(bytes([0, 127, 128, 128])))
    payload = b"".join(
        [
            _field_varint(1, 1),
            _field_len(2, b"ignored map ext info"),
            _field_len(3, map_head),
            _field_len(4, map_data),
            _field_len(12, room_one),
            _field_len(12, room_two),
        ]
    )

    size_x, size_y, grid, room_names = _parse_scmap_payload(payload)

    assert size_x == 2
    assert size_y == 2
    assert grid == bytes([0, 127, 128, 128])
    assert room_names == {
        42: "Kitchen",
        99: "Room 99",
    }


def test_b01_map_parser_rejects_invalid_payload() -> None:
    parser = B01MapParser()
    with pytest.raises(RoborockException, match="Failed to decode B01 map payload"):
        parser.parse(b"not a map", serial="testsn012345", model="roborock.vacuum.sc05")

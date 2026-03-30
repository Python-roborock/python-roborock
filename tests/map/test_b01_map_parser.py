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
from roborock.map.proto.b01_scmap_pb2 import RobotMap  # type: ignore[attr-defined]

FIXTURE = Path(__file__).resolve().parent / "testdata" / "raw-mqtt-map301.bin.inflated.bin.gz"


def _derive_map_key(serial: str, model: str) -> bytes:
    model_suffix = model.split(".")[-1]
    model_key = (model_suffix + "0" * 16)[:16].encode()
    material = f"{serial}+{model_suffix}+{serial}".encode()
    encrypted = AES.new(model_key, AES.MODE_ECB).encrypt(pad(material, AES.block_size))
    md5 = hashlib.md5(base64.b64encode(encrypted), usedforsecurity=False).hexdigest()
    return md5[8:24].encode()


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


def test_b01_scmap_parser_maps_observed_schema_fields() -> None:
    payload = RobotMap()
    payload.mapType = 1
    payload.mapExtInfo.taskBeginDate = 100
    payload.mapExtInfo.mapUploadDate = 200
    payload.mapExtInfo.mapValid = 1
    payload.mapExtInfo.mapVersion = 3
    payload.mapExtInfo.boudaryInfo.mapMd5 = "md5"
    payload.mapExtInfo.boudaryInfo.vMinX = 10
    payload.mapExtInfo.boudaryInfo.vMaxX = 20
    payload.mapExtInfo.boudaryInfo.vMinY = 30
    payload.mapExtInfo.boudaryInfo.vMaxY = 40
    payload.mapHead.mapHeadId = 7
    payload.mapHead.sizeX = 2
    payload.mapHead.sizeY = 2
    payload.mapHead.minX = 1.5
    payload.mapHead.minY = 2.5
    payload.mapHead.maxX = 3.5
    payload.mapHead.maxY = 4.5
    payload.mapHead.resolution = 0.05
    payload.mapData.mapData = bytes([0, 127, 128, 128])

    room_one = payload.roomDataInfo.add()
    room_one.roomId = 42
    room_one.roomName = "Kitchen"
    room_one.cleanState = 1
    room_one.roomNamePost.x = 11.25
    room_one.roomNamePost.y = 22.5
    room_one.colorId = 7
    room_one.global_seq = 9

    room_two = payload.roomDataInfo.add()
    room_two.roomId = 99
    room_two.cleanState = 0

    parsed = _parse_scmap_payload(payload.SerializeToString())

    assert parsed.mapType == 1
    assert parsed.HasField("mapExtInfo")
    assert parsed.mapExtInfo.taskBeginDate == 100
    assert parsed.mapExtInfo.mapUploadDate == 200
    assert parsed.mapExtInfo.HasField("boudaryInfo")
    assert parsed.mapExtInfo.boudaryInfo.vMaxY == 40
    assert parsed.HasField("mapHead")
    assert parsed.mapHead.mapHeadId == 7
    assert parsed.mapHead.sizeX == 2
    assert parsed.mapHead.sizeY == 2
    assert parsed.mapHead.resolution == pytest.approx(0.05)
    assert parsed.HasField("mapData")
    assert parsed.mapData.HasField("mapData")
    assert parsed.mapData.mapData == bytes([0, 127, 128, 128])
    assert parsed.roomDataInfo[0].roomId == 42
    assert parsed.roomDataInfo[0].roomName == "Kitchen"
    assert parsed.roomDataInfo[0].HasField("roomNamePost")
    assert parsed.roomDataInfo[0].roomNamePost.x == pytest.approx(11.25)
    assert parsed.roomDataInfo[0].roomNamePost.y == pytest.approx(22.5)
    assert parsed.roomDataInfo[0].colorId == 7
    assert parsed.roomDataInfo[0].global_seq == 9
    assert parsed.roomDataInfo[1].roomId == 99
    assert not parsed.roomDataInfo[1].HasField("roomName")


def test_b01_map_parser_rejects_invalid_payload() -> None:
    parser = B01MapParser()
    with pytest.raises(RoborockException, match="Failed to decode B01 map payload"):
        parser.parse(b"not a map", serial="testsn012345", model="roborock.vacuum.sc05")

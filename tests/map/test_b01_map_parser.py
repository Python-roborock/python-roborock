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
from roborock.protocols.b01_q7_protocol import create_map_key, decode_map_payload

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
    map_key = create_map_key(serial, model)
    encrypted = AES.new(map_key.key, AES.MODE_ECB).encrypt(pad(compressed.hex().encode(), AES.block_size))
    payload = base64.b64encode(encrypted)

    parser = B01MapParser()
    inflated_payload = decode_map_payload(payload, map_key=map_key)
    parsed = parser.parse(inflated_payload)

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
    with pytest.raises(RoborockException, match="Failed to parse B01 SCMap"):
        parser.parse(b"not a map")


def _pose_map_payload() -> RobotMap:
    """A minimal 4x4 map with pose, path and room-outline data."""
    payload = RobotMap()
    payload.mapType = 0
    payload.mapHead.mapHeadId = 1
    payload.mapHead.sizeX = 4
    payload.mapHead.sizeY = 4
    payload.mapHead.minX = -0.1
    payload.mapHead.minY = -0.1
    payload.mapHead.maxX = 0.1
    payload.mapHead.maxY = 0.1
    payload.mapHead.resolution = 0.05
    payload.mapData.mapData = bytes([127] * 16)
    return payload


def test_b01_map_parser_projects_poses_and_path() -> None:
    payload = _pose_map_payload()
    payload.chargeStation.x = 0.0
    payload.chargeStation.y = 0.0
    payload.chargeStation.phi = 0.0
    payload.currentPose.poseId = 2
    payload.currentPose.update = 6
    payload.currentPose.x = 0.05
    payload.currentPose.y = -0.05
    payload.currentPose.phi = 0.0
    for x, y in [(0.0, 0.0), (0.05, 0.0)]:
        point = payload.historyPose.points.add()
        point.x = x
        point.y = y

    parsed = B01MapParser().parse(payload.SerializeToString())
    map_data = parsed.map_data

    # World (0, 0) with min (-0.1, -0.1) at 0.05 m/px is pixel (2, 2),
    # flipped top-down to row sizeY - 1 - 2 = 1.
    assert map_data.charger is not None
    assert (map_data.charger.x, map_data.charger.y) == pytest.approx((2.0, 1.0))
    assert map_data.vacuum_position is not None
    assert (map_data.vacuum_position.x, map_data.vacuum_position.y) == pytest.approx((3.0, 2.0))
    assert map_data.path is not None
    assert [(p.x, p.y) for p in map_data.path.path[0]] == [
        pytest.approx((2.0, 1.0)),
        pytest.approx((3.0, 1.0)),
    ]


def test_b01_map_parser_rejects_placeholder_pose() -> None:
    """Saved maps carry a placeholder (1100, 1100) pose that must not render."""
    payload = _pose_map_payload()
    payload.chargeStation.x = 0.0
    payload.chargeStation.y = 0.0
    payload.chargeStation.phi = 0.5
    payload.currentPose.x = 1100.0
    payload.currentPose.y = 1100.0

    parsed = B01MapParser().parse(payload.SerializeToString())
    map_data = parsed.map_data

    # The out-of-bounds pose is ignored; the robot is shown at its dock.
    assert map_data.vacuum_position is not None
    assert (map_data.vacuum_position.x, map_data.vacuum_position.y) == pytest.approx((2.0, 1.0))


def test_b01_map_parser_extracts_rooms_from_outlines() -> None:
    payload = _pose_map_payload()
    room = payload.roomDataInfo.add()
    room.roomId = 10
    room.roomName = "Kitchen"
    room.roomNamePost.x = 0.0
    room.roomNamePost.y = 0.0
    outline = payload.roomOutline.add()
    outline.roomId = 10
    for x, y in [(1, 1), (2, 2)]:
        point = outline.points.add()
        point.x = x
        point.y = y

    parsed = B01MapParser().parse(payload.SerializeToString())
    rooms = parsed.map_data.rooms

    assert rooms is not None
    assert set(rooms) == {10}
    kitchen = rooms[10]
    assert kitchen.name == "Kitchen"
    # Outline grid rows flip top-down: y=1 -> 2, y=2 -> 1.
    assert (kitchen.x0, kitchen.y0, kitchen.x1, kitchen.y1) == (1, 1, 2, 2)
    assert (kitchen.pos_x, kitchen.pos_y) == pytest.approx((2.0, 1.0))


def test_b01_map_parser_colors_enclosed_room_pixels() -> None:
    """Floor pixels inside a room outline are tinted with the room color."""
    import io

    from PIL import Image

    payload = RobotMap()
    payload.mapHead.mapHeadId = 1
    payload.mapHead.sizeX = 6
    payload.mapHead.sizeY = 6
    payload.mapHead.minX = 0.0
    payload.mapHead.minY = 0.0
    payload.mapHead.maxX = 6.0
    payload.mapHead.maxY = 6.0
    payload.mapHead.resolution = 1.0
    grid = bytearray([128] * 36)
    for row in range(1, 5):
        for col in range(1, 5):
            grid[row * 6 + col] = 127
    payload.mapData.mapData = bytes(grid)

    room = payload.roomDataInfo.add()
    room.roomId = 10
    room.roomName = "Kitchen"
    room.roomNamePost.x = 3.2
    room.roomNamePost.y = 3.2
    outline = payload.roomOutline.add()
    outline.roomId = 10
    for row in range(1, 5):
        for col in range(1, 5):
            if row in (1, 4) or col in (1, 4):
                point = outline.points.add()
                point.x = col
                point.y = row

    parsed = B01MapParser().parse(payload.SerializeToString())
    img = Image.open(io.BytesIO(parsed.image_content)).convert("RGB")

    # Raw (3, 3) flips to display row 2; scale 4 puts it at (12..15, 8..11).
    room_pixel = img.getpixel((13, 9))
    assert room_pixel != (32, 115, 185)  # not the plain MAP_INSIDE floor color
    # Walls/obstacles render with the shared V1 grey wall color.
    assert img.getpixel((1, 1)) == (93, 109, 126)

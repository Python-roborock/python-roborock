"""Tests for the B01 protocol message encoding and decoding."""

import base64
import json
import logging
import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP, YXWaterLevel
from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint
from roborock.data.code_mappings import completed_warnings
from roborock.exceptions import RoborockException
from roborock.map.b01_q10_map_parser import Q10MapPacket, Q10MapPacketKind, Q10TracePacket
from roborock.map.b01_q10_overlays import Q10RestrictedZone, Q10RestrictionType, Q10VirtualWall
from roborock.protocols.b01_q10_protocol import (
    Q10DpsUpdate,
    decode_message,
    decode_rpc_response,
    encode_mqtt_payload,
    encode_restricted_zones,
    encode_room_name,
    encode_virtual_walls,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_q10_protocol/")
TESTDATA_FILES = list(TESTDATA_PATH.glob("*.json"))
TESTDATA_IDS = [x.stem for x in TESTDATA_FILES]

MAP_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = pathlib.Path("tests/map/testdata/b01_q10_trace.bin")


def _point(x: int, y: int) -> Q10RoborockPoint:
    """Build a public-coordinate point from a captured Q10 wire vector."""
    return Q10RoborockPoint.from_vector(x, y)


def _zone(zone_type: Q10RestrictionType, *vertices: tuple[int, int]) -> Q10RestrictedZone:
    return Q10RestrictedZone(zone_type, tuple(_point(*vertex) for vertex in vertices))  # type: ignore[arg-type]


def _wall(start: tuple[int, int], end: tuple[int, int]) -> Q10VirtualWall:
    return Q10VirtualWall(_point(*start), _point(*end))


def test_encode_restricted_zones_real_three_zone_capture_byte_exact() -> None:
    """Encoding is the exact inverse of a real three-zone DP 55 capture."""
    captured = (
        "AQMABP9A9ToAEPU6ABDzzv9A884AAAAAAAAAAAAAAAAAAAAAAAAAAAAE/Rb/mv5z/5r+c/3L/Rb9ywAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAQDpADEB3UAxAd1/GMDpPxjAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    )
    zones = [
        _zone(Q10RestrictionType.NO_GO, (-192, -2758), (16, -2758), (16, -3122), (-192, -3122)),
        _zone(Q10RestrictionType.NO_GO, (-746, -102), (-397, -102), (-397, -565), (-746, -565)),
        _zone(Q10RestrictionType.NO_GO, (932, 196), (1909, 196), (1909, -925), (932, -925)),
    ]

    assert encode_restricted_zones(zones) == captured


def test_encode_restricted_zones_empty_is_device_canonical_payload() -> None:
    assert encode_restricted_zones([]) == "AQA="


def test_encode_restricted_zones_mixed_types_and_padding_byte_exact() -> None:
    """Multiple restriction kinds retain order and fixed 38-byte padding."""
    zones = [
        _zone(Q10RestrictionType.NO_MOP, (-1, 2), (3, 4), (5, 6), (7, 8)),
        _zone(Q10RestrictionType.THRESHOLD, (-32_768, 32_767), (0, 1), (2, 3), (4, 5)),
    ]
    record_one = bytes.fromhex("0204ffff0002000300040005000600070008") + bytes(20)
    record_two = bytes.fromhex("030480007fff000000010002000300040005") + bytes(20)

    assert base64.b64decode(encode_restricted_zones(zones)) == b"\x01\x02" + record_one + record_two


def test_encode_virtual_walls_real_mixed_capture_byte_exact() -> None:
    """Encoding preserves the proven x/y order for real horizontal and vertical walls."""
    captured = "AgNyBGMFsARjAf8FAAH7CnE="
    walls = [_wall((882, 1123), (1456, 1123)), _wall((511, 1280), (507, 2673))]

    assert encode_virtual_walls(walls) == captured


def test_encode_virtual_walls_empty_is_device_canonical_payload() -> None:
    assert encode_virtual_walls([]) == "AA=="


def test_encode_virtual_walls_signed_boundaries_byte_exact() -> None:
    walls = [_wall((-32_768, 32_767), (32_767, -32_768))]

    assert base64.b64decode(encode_virtual_walls(walls)) == bytes.fromhex("0180007fff7fff8000")


@pytest.mark.parametrize("collection", ["not-zones", b"not-zones", [object()]])
def test_encode_restricted_zones_rejects_wrong_collection_values(collection: Any) -> None:
    with pytest.raises(ValueError, match="zones"):
        encode_restricted_zones(collection)


def test_encode_restricted_zones_rejects_more_than_wire_count() -> None:
    zone = _zone(Q10RestrictionType.NO_GO, (0, 0), (1, 0), (1, 1), (0, 1))

    with pytest.raises(ValueError, match="at most 255"):
        encode_restricted_zones([zone] * 256)


def test_encode_restricted_zones_rejects_wrong_type() -> None:
    zone = Q10RestrictedZone(
        "no-go",  # type: ignore[arg-type]
        (_point(0, 0), _point(1, 0), _point(1, 1), _point(0, 1)),
    )

    with pytest.raises(ValueError, match="restricted-zone type"):
        encode_restricted_zones([zone])


def test_encode_restricted_zones_preserves_unknown_wire_type() -> None:
    zone = Q10RestrictedZone(42, (_point(0, 0), _point(1, 0), _point(1, 1), _point(0, 1)))

    assert base64.b64decode(encode_restricted_zones([zone]))[2] == 42


@pytest.mark.parametrize(
    "vertices",
    [
        ((0, 0), (1, 0), (1, 1)),
        ((0, 0), (1, 0), (1, 1), (0, 1), (-1, 0)),
    ],
)
def test_encode_restricted_zones_rejects_wrong_cardinality(vertices: tuple[tuple[int, int], ...]) -> None:
    zone = Q10RestrictedZone(
        Q10RestrictionType.NO_GO,
        tuple(_point(*vertex) for vertex in vertices),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="exactly four"):
        encode_restricted_zones([zone])


def test_encode_restricted_zones_rejects_duplicate_vertices() -> None:
    duplicate = _point(0, 0)
    zone = Q10RestrictedZone(
        Q10RestrictionType.NO_GO,
        (duplicate, _point(1, 0), _point(1, 1), duplicate),
    )

    with pytest.raises(ValueError, match="distinct"):
        encode_restricted_zones([zone])


@pytest.mark.parametrize(
    ("vertices", "message"),
    [
        (((0, 0), (1, 0), (2, 0), (3, 0)), "enclose an area"),
        (((0, 0), (2, 2), (0, 2), (2, 0)), "enclose an area|must not cross"),
    ],
)
def test_encode_restricted_zones_rejects_invalid_geometry(
    vertices: tuple[tuple[int, int], ...],
    message: str,
) -> None:
    zone = _zone(Q10RestrictionType.NO_GO, *vertices)

    with pytest.raises(ValueError, match=message):
        encode_restricted_zones([zone])


@pytest.mark.parametrize("collection", ["not-walls", b"not-walls", [object()]])
def test_encode_virtual_walls_rejects_wrong_collection_values(collection: Any) -> None:
    with pytest.raises(ValueError, match="walls"):
        encode_virtual_walls(collection)


def test_encode_virtual_walls_rejects_more_than_wire_count() -> None:
    wall = _wall((0, 0), (1, 1))

    with pytest.raises(ValueError, match="at most 255"):
        encode_virtual_walls([wall] * 256)


def test_encode_virtual_walls_rejects_duplicate_endpoints() -> None:
    point = _point(0, 0)

    with pytest.raises(ValueError, match="distinct"):
        encode_virtual_walls([Q10VirtualWall(point, point)])


@pytest.mark.parametrize(
    "point",
    [
        Q10RoborockPoint(True, 25_500),
        Q10RoborockPoint(25_500.0, 25_500),  # type: ignore[arg-type]
        Q10RoborockPoint(25_501, 25_500),
        Q10RoborockPoint(-138_345, 25_500),
    ],
)
def test_zone_and_wall_encoders_reject_invalid_coordinates(point: Q10RoborockPoint) -> None:
    valid = (_point(10, 10), _point(11, 10), _point(11, 11))
    zone = Q10RestrictedZone(Q10RestrictionType.NO_GO, (point, *valid))
    wall = Q10VirtualWall(point, _point(2, 2))

    with pytest.raises(ValueError, match="coordinates"):
        encode_restricted_zones([zone])
    with pytest.raises(ValueError, match="coordinates"):
        encode_virtual_walls([wall])


def test_overlay_encoders_do_not_mutate_callers() -> None:
    zones = [_zone(Q10RestrictionType.NO_MOP, (0, 0), (2, 0), (2, 2), (0, 2))]
    walls = [_wall((-1, -1), (1, 1))]
    original_zones = list(zones)
    original_walls = list(walls)

    encode_restricted_zones(zones)
    encode_virtual_walls(walls)

    assert zones == original_zones
    assert walls == original_walls


def test_encode_room_name_uses_fixed_utf8_field() -> None:
    assert base64.b64decode(encode_room_name(7, "Café")) == bytes((1, 7, 0, 5)) + "Café".encode() + bytes(14)


@pytest.mark.parametrize("room_id", [True, -1, 256, 1.0, "1"])
def test_encode_room_name_rejects_invalid_room_id(room_id: Any) -> None:
    with pytest.raises(ValueError, match="room_id"):
        encode_room_name(room_id, "Study")


@pytest.mark.parametrize("name", ["", "a\x00b", "x" * 20, "é" * 10, 1])
def test_encode_room_name_rejects_invalid_name(name: Any) -> None:
    with pytest.raises(ValueError, match="name"):
        encode_room_name(7, name)


def _message(payload: bytes, protocol: RoborockMessageProtocol) -> RoborockMessage:
    return RoborockMessage(protocol=protocol, payload=payload, version=b"B01")


def test_decode_message_dps_update() -> None:
    """A non-MAP_RESPONSE message decodes into a Q10DpsUpdate."""
    message = _message(b'{"dps": {"122": 100}}', RoborockMessageProtocol.RPC_RESPONSE)
    decoded = decode_message(message)
    assert decoded == Q10DpsUpdate(dps={B01_Q10_DP.BATTERY: 100})


def test_decode_message_common_multi_map_list() -> None:
    """A nested dpCommon map-list response is flattened into dpMultiMap."""
    message = _message(
        b'{"dps":{"101":{"61":{"data":[{"id":"12345","name":"Map","timestamp":1}],"op":"list","result":1}}}}',
        RoborockMessageProtocol.RPC_RESPONSE,
    )

    decoded = decode_message(message)

    assert decoded == Q10DpsUpdate(
        dps={
            B01_Q10_DP.MULTI_MAP: {
                "data": [{"id": "12345", "name": "Map", "timestamp": 1}],
                "op": "list",
                "result": 1,
            }
        }
    )


def test_decode_message_map_packet() -> None:
    """A MAP_RESPONSE 01 01 payload decodes into a Q10MapPacket."""
    message = _message(MAP_FIXTURE.read_bytes(), RoborockMessageProtocol.MAP_RESPONSE)
    decoded = decode_message(message)
    assert isinstance(decoded, Q10MapPacket)
    assert {room.id: room.name for room in decoded.rooms} == {2: "Living Room", 3: "bedroom"}


@pytest.mark.parametrize(
    ("marker", "kind"),
    [
        (b"\x03\x01", Q10MapPacketKind.CLEAN_RECORD_DETAIL),
        (b"\x04\x01", Q10MapPacketKind.SAVED_MAP_DETAIL),
    ],
)
def test_decode_message_archived_map_packet(marker: bytes, kind: Q10MapPacketKind) -> None:
    """The decoder recognizes both archived map-detail markers."""
    fixture = MAP_FIXTURE.read_bytes()
    decoded = decode_message(_message(marker + fixture[2:], RoborockMessageProtocol.MAP_RESPONSE))

    assert isinstance(decoded, Q10MapPacket)
    assert decoded.kind is kind


def test_decode_message_trace_packet() -> None:
    """A MAP_RESPONSE 02 01 payload decodes into a Q10TracePacket."""
    message = _message(TRACE_FIXTURE.read_bytes(), RoborockMessageProtocol.MAP_RESPONSE)
    decoded = decode_message(message)
    assert isinstance(decoded, Q10TracePacket)
    # This docked capture carries only a heading (no path points); see the
    # parser tests for the full byte-level decode.
    assert decoded.points == []
    assert decoded.heading == 169


def test_decode_message_unknown_map_marker_returns_none() -> None:
    """A MAP_RESPONSE with an unrecognized marker is skipped (returns None)."""
    assert decode_message(_message(b"\x09\x09junk", RoborockMessageProtocol.MAP_RESPONSE)) is None
    assert decode_message(_message(b"", RoborockMessageProtocol.MAP_RESPONSE)) is None


@pytest.fixture(autouse=True)
def fixed_time_fixture() -> Generator[None, None, None]:
    """Fixture to freeze time for predictable request IDs."""
    with freeze_time("2025-01-20T12:00:00"):
        yield


@pytest.mark.parametrize("filename", TESTDATA_FILES, ids=TESTDATA_IDS)
def test_decode_rpc_payload(filename: str, snapshot: SnapshotAssertion) -> None:
    """Test decoding a B01 RPC response protocol message."""
    with open(filename, "rb") as f:
        payload = f.read()

    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    decoded_message = decode_rpc_response(message)
    assert json.dumps(decoded_message, indent=2) == snapshot


@pytest.mark.parametrize(
    ("payload", "expected_error_message"),
    [
        (b"", "missing payload"),
        (b"n", "Invalid B01 json payload"),
        (b"{}", "missing 'dps'"),
        (b'{"dps": []}', "'dps' should be a dictionary"),
        (b'{"dps": {"not_a_number": 123}}', "dps key is not a valid integer"),
        (b'{"dps": {"101": 123}}', "Invalid dpCommon format: expected dict"),
        (b'{"dps": {"101": {"not_a_number": 123}}}', "Invalid dpCommon format: dps key is not a valid intege"),
    ],
)
def test_decode_invalid_rpc_payload(payload: bytes, expected_error_message: str) -> None:
    """Test decoding a B01 RPC response protocol message."""
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )
    with pytest.raises(RoborockException, match=expected_error_message):
        decode_rpc_response(message)


def test_decode_unknown_dps_code(caplog: pytest.LogCaptureFixture) -> None:
    """Unknown data points are dropped silently, without logging warnings.

    ss07 hardware pushes DPs 112 and 113 (and occasionally others) that this
    library does not model. They must be ignored without emitting "not a valid
    code" warnings, which previously spammed the log on every status push.
    """
    completed_warnings.discard("112 is not a valid code for B01_Q10_DP")
    completed_warnings.discard("113 is not a valid code for B01_Q10_DP")
    completed_warnings.discard("909090 is not a valid code for B01_Q10_DP")
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"dps": {"909090": 123, "112": 0, "113": 0, "122": 100}}',
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    with caplog.at_level(logging.WARNING):
        decoded_message = decode_rpc_response(message)
    assert decoded_message == {
        B01_Q10_DP.BATTERY: 100,
    }
    assert "not a valid code" not in caplog.text


@pytest.mark.parametrize(
    ("command", "params"),
    [
        (B01_Q10_DP.REQUEST_DPS, {}),
        (B01_Q10_DP.REQUEST_DPS, None),
        (B01_Q10_DP.START_CLEAN, {"cmd": 1}),
        (B01_Q10_DP.WATER_LEVEL, YXWaterLevel.MEDIUM.code),
    ],
)
def test_encode_mqtt_payload(command: B01_Q10_DP, params: dict[str, Any], snapshot) -> None:
    """Test encoding of MQTT payload for B01 Q10 commands."""

    message = encode_mqtt_payload(command, params)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"B01"
    assert message.payload is not None

    # Snapshot the raw payload to ensure stable encoding. We verify it is
    # valid json
    assert snapshot == message.payload

    json.loads(message.payload.decode())

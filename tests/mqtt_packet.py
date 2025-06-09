"""Module for crafting MQTT packets.

This library is copied from the paho mqtt client library tests, with just the
parts needed for some roborock messages. This message format in this file is
not specific to roborock.
"""

import struct

PROP_RECEIVE_MAXIMUM = 33
PROP_TOPIC_ALIAS_MAXIMUM = 34


def gen_uint16_prop(identifier: int, word: int) -> bytes:
    """Generate a property with a uint16_t value."""
    prop = struct.pack("!BH", identifier, word)
    return prop


def pack_varint(varint: int) -> bytes:
    """Pack a variable integer."""
    s = b""
    while True:
        byte = varint % 128
        varint = varint // 128
        # If there are more digits to encode, set the top bit of this digit
        if varint > 0:
            byte = byte | 0x80

        s = s + struct.pack("!B", byte)
        if varint == 0:
            return s


def prop_finalise(props: bytes) -> bytes:
    """Finalise the properties."""
    if props is None:
        return pack_varint(0)
    else:
        return pack_varint(len(props)) + props


def gen_connack(flags=0, rc=0, properties=b"", property_helper=True):
    """Generate a CONNACK packet."""
    if property_helper:
        if properties is not None:
            properties = (
                gen_uint16_prop(PROP_TOPIC_ALIAS_MAXIMUM, 10) + properties + gen_uint16_prop(PROP_RECEIVE_MAXIMUM, 20)
            )
        else:
            properties = b""
    properties = prop_finalise(properties)

    packet = struct.pack("!BBBB", 32, 2 + len(properties), flags, rc) + properties

    return packet


def gen_suback(mid: int, qos: int = 0) -> bytes:
    """Generate a SUBACK packet."""
    return struct.pack("!BBHBB", 144, 2 + 1 + 1, mid, 0, qos)


def _gen_short(cmd: int, reason_code: int) -> bytes:
    return struct.pack("!BBB", cmd, 1, reason_code)


def gen_disconnect(reason_code: int = 0) -> bytes:
    """Generate a DISCONNECT packet."""
    return _gen_short(0xE0, reason_code)


def _gen_command_with_mid(cmd: int, mid: int, reason_code: int = 0) -> bytes:
    return struct.pack("!BBHB", cmd, 3, mid, reason_code)


def gen_puback(mid: int, reason_code: int = 0) -> bytes:
    """Generate a PUBACK packet."""
    return _gen_command_with_mid(64, mid, reason_code)


def _pack_remaining_length(remaining_length: int) -> bytes:
    """Pack a remaining length."""
    s = b""
    while True:
        byte = remaining_length % 128
        remaining_length = remaining_length // 128
        # If there are more digits to encode, set the top bit of this digit
        if remaining_length > 0:
            byte = byte | 0x80

        s = s + struct.pack("!B", byte)
        if remaining_length == 0:
            return s


def gen_publish(
    topic: str,
    payload: bytes | None = None,
    retain: bool = False,
    dup: bool = False,
    mid: int = 0,
    properties: bytes = b"",
) -> bytes:
    """Generate a PUBLISH packet."""
    if isinstance(topic, str):
        topic_b = topic.encode("utf-8")
    rl = 2 + len(topic_b)
    pack_format = "H" + str(len(topic_b)) + "s"

    properties = prop_finalise(properties)
    rl += len(properties)
    # This will break if len(properties) > 127
    pack_format = f"{pack_format}{len(properties)}s"

    if payload is not None:
        # payload = payload.encode("utf-8")
        rl = rl + len(payload)
        pack_format = pack_format + str(len(payload)) + "s"
    else:
        payload = b""
        pack_format = pack_format + "0s"

    rlpacked = _pack_remaining_length(rl)
    cmd = 48
    if retain:
        cmd = cmd + 1
    if dup:
        cmd = cmd + 8

    return struct.pack(
        "!B" + str(len(rlpacked)) + "s" + pack_format, cmd, rlpacked, len(topic_b), topic_b, properties, payload
    )

from __future__ import annotations

import binascii
import gzip
import hashlib
import logging
from collections.abc import Callable
from urllib.parse import urlparse

from construct import (  # type: ignore
    Bytes,
    Checksum,
    ChecksumError,
    Construct,
    Container,
    GreedyBytes,
    GreedyRange,
    Int16ub,
    Int32ub,
    Optional,
    Peek,
    RawCopy,
    Struct,
    bytestringtype,
    stream_seek,
    stream_tell,
)
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.containers import RRiot
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams
from roborock.roborock_message import RoborockMessage

_LOGGER = logging.getLogger(__name__)
SALT = b"TXdfu$jyZ#TZHsg4"
A01_HASH = "726f626f726f636b2d67a6d6da"
B01_HASH = "5wwh9ikChRjASpMU8cxg7o1d2E"
AP_CONFIG = 1
SOCK_DISCOVERY = 2


def md5hex(message: str) -> str:
    md5 = hashlib.md5()
    md5.update(message.encode())
    return md5.hexdigest()


class Utils:
    """Util class for protocol manipulation."""

    @staticmethod
    def verify_token(token: bytes):
        """Checks if the given token is of correct type and length."""
        if not isinstance(token, bytes):
            raise TypeError("Token must be bytes")
        if len(token) != 16:
            raise ValueError("Wrong token length")

    @staticmethod
    def ensure_bytes(msg: bytes | str) -> bytes:
        if isinstance(msg, str):
            return msg.encode()
        return msg

    @staticmethod
    def encode_timestamp(_timestamp: int) -> bytes:
        hex_value = f"{_timestamp:x}".zfill(8)
        return "".join(list(map(lambda idx: hex_value[idx], [5, 6, 3, 7, 1, 2, 0, 4]))).encode()

    @staticmethod
    def md5(data: bytes) -> bytes:
        """Calculates a md5 hashsum for the given bytes object."""
        checksum = hashlib.md5()  # nosec
        checksum.update(data)
        return checksum.digest()

    @staticmethod
    def encrypt_ecb(plaintext: bytes, token: bytes) -> bytes:
        """Encrypt plaintext with a given token using ecb mode.

        :param bytes plaintext: Plaintext (json) to encrypt
        :param bytes token: Token to use
        :return: Encrypted bytes
        """
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext requires bytes")
        Utils.verify_token(token)
        cipher = AES.new(token, AES.MODE_ECB)
        if plaintext:
            plaintext = pad(plaintext, AES.block_size)
            return cipher.encrypt(plaintext)
        return plaintext

    @staticmethod
    def decrypt_ecb(ciphertext: bytes, token: bytes) -> bytes:
        """Decrypt ciphertext with a given token using ecb mode.

        :param bytes ciphertext: Ciphertext to decrypt
        :param bytes token: Token to use
        :return: Decrypted bytes object
        """
        if not isinstance(ciphertext, bytes):
            raise TypeError("ciphertext requires bytes")
        if ciphertext:
            Utils.verify_token(token)

            aes_key = token
            decipher = AES.new(aes_key, AES.MODE_ECB)
            return unpad(decipher.decrypt(ciphertext), AES.block_size)
        return ciphertext

    @staticmethod
    def encrypt_cbc(plaintext: bytes, token: bytes) -> bytes:
        """Encrypt plaintext with a given token using cbc mode.

        This is currently used for testing purposes only.

        :param bytes plaintext: Plaintext (json) to encrypt
        :param bytes token: Token to use
        :return: Encrypted bytes
        """
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext requires bytes")
        Utils.verify_token(token)
        iv = bytes(AES.block_size)
        cipher = AES.new(token, AES.MODE_CBC, iv)
        if plaintext:
            plaintext = pad(plaintext, AES.block_size)
            return cipher.encrypt(plaintext)
        return plaintext

    @staticmethod
    def decrypt_cbc(ciphertext: bytes, token: bytes) -> bytes:
        """Decrypt ciphertext with a given token using cbc mode.

        :param bytes ciphertext: Ciphertext to decrypt
        :param bytes token: Token to use
        :return: Decrypted bytes object
        """
        if not isinstance(ciphertext, bytes):
            raise TypeError("ciphertext requires bytes")
        if ciphertext:
            Utils.verify_token(token)

            iv = bytes(AES.block_size)
            decipher = AES.new(token, AES.MODE_CBC, iv)
            return unpad(decipher.decrypt(ciphertext), AES.block_size)
        return ciphertext

    @staticmethod
    def crc(data: bytes) -> int:
        """Gather bytes for checksum calculation."""
        return binascii.crc32(data)

    @staticmethod
    def decompress(compressed_data: bytes):
        """Decompress data using gzip."""
        return gzip.decompress(compressed_data)


class EncryptionAdapter(Construct):
    """Adapter to handle communication encryption."""

    def __init__(self, token_func: Callable):
        super().__init__()
        self.token_func = token_func

    def _parse(self, stream, context, path):
        subcon1 = Optional(Int16ub)
        length = subcon1.parse_stream(stream, **context)
        if not length:
            if length == 0:
                subcon1.parse_stream(stream, **context)  # seek 2
            return None
        subcon2 = Bytes(length)
        obj = subcon2.parse_stream(stream, **context)
        return self._decode(obj, context, path)

    def _build(self, obj, stream, context, path):
        if obj is not None:
            obj2 = self._encode(obj, context, path)
            subcon1 = Int16ub
            length = len(obj2)
            subcon1.build_stream(length, stream, **context)
            subcon2 = Bytes(length)
            subcon2.build_stream(obj2, stream, **context)
        return obj

    def _encode(self, obj, context, _):
        """Encrypt the given payload with the token stored in the context.

        :param obj: JSON object to encrypt
        """
        if context.version == b"A01":
            iv = md5hex(format(context.random, "08x") + A01_HASH)[8:24]
            decipher = AES.new(bytes(context.search("local_key"), "utf-8"), AES.MODE_CBC, bytes(iv, "utf-8"))
            f = decipher.encrypt(obj)
            return f
        elif context.version == b"B01":
            iv = md5hex(f"{context.random:08x}" + B01_HASH)[9:25]
            decipher = AES.new(bytes(context.search("local_key"), "utf-8"), AES.MODE_CBC, bytes(iv, "utf-8"))
            return decipher.encrypt(obj)
        token = self.token_func(context)
        encrypted = Utils.encrypt_ecb(obj, token)
        return encrypted

    def _decode(self, obj, context, _):
        """Decrypts the given payload with the token stored in the context."""
        if context.version == b"A01":
            iv = md5hex(format(context.random, "08x") + A01_HASH)[8:24]
            decipher = AES.new(bytes(context.search("local_key"), "utf-8"), AES.MODE_CBC, bytes(iv, "utf-8"))
            f = decipher.decrypt(obj)
            return f
        elif context.version == b"B01":
            iv = md5hex(f"{context.random:08x}" + B01_HASH)[9:25]
            decipher = AES.new(bytes(context.search("local_key"), "utf-8"), AES.MODE_CBC, bytes(iv, "utf-8"))
            return decipher.decrypt(obj)
        token = self.token_func(context)
        decrypted = Utils.decrypt_ecb(obj, token)
        return decrypted


class OptionalChecksum(Checksum):
    def _parse(self, stream, context, path):
        if not context.message.value.payload:
            return
        hash1 = self.checksumfield.parse_stream(stream, **context)
        hash2 = self.hashfunc(self.bytesfunc(context))
        if hash1 != hash2:
            raise ChecksumError(
                f"wrong checksum, read {hash1 if not isinstance(hash1, bytestringtype) else binascii.hexlify(hash1)}, "
                f"computed {hash2 if not isinstance(hash2, bytestringtype) else binascii.hexlify(hash2)}",
                path=path,
            )
        return hash1


class PrefixedStruct(Struct):
    def _parse(self, stream, context, path):
        subcon1 = Peek(Optional(Bytes(3)))
        peek_version = subcon1.parse_stream(stream, **context)
        if peek_version not in (b"1.0", b"A01", b"B01"):
            subcon2 = Bytes(4)
            subcon2.parse_stream(stream, **context)
        return super()._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        prefixed = context.search("prefixed")
        if not prefixed:
            return super()._build(obj, stream, context, path)
        offset = stream_tell(stream, path)
        stream_seek(stream, offset + 4, 0, path)
        super()._build(obj, stream, context, path)
        new_offset = stream_tell(stream, path)
        subcon1 = Bytes(4)
        stream_seek(stream, offset, 0, path)
        subcon1.build_stream(new_offset - offset - subcon1.sizeof(**context), stream, **context)
        stream_seek(stream, new_offset + 4, 0, path)
        return obj


_Message = RawCopy(
    Struct(
        "version" / Bytes(3),
        "seq" / Int32ub,
        "random" / Int32ub,
        "timestamp" / Int32ub,
        "protocol" / Int16ub,
        "payload"
        / EncryptionAdapter(
            lambda ctx: Utils.md5(
                Utils.encode_timestamp(ctx.timestamp) + Utils.ensure_bytes(ctx.search("local_key")) + SALT
            ),
        ),
    )
)

_Messages = Struct(
    "messages"
    / GreedyRange(
        PrefixedStruct(
            "message" / _Message,
            "checksum" / OptionalChecksum(Optional(Int32ub), Utils.crc, lambda ctx: ctx.message.data),
        )
    ),
    "remaining" / Optional(GreedyBytes),
)


class _Parser:
    def __init__(self, con: Construct, required_local_key: bool):
        self.con = con
        self.required_local_key = required_local_key

    def parse(self, data: bytes, local_key: str | None = None) -> tuple[list[RoborockMessage], bytes]:
        if self.required_local_key and local_key is None:
            raise RoborockException("Local key is required")
        parsed = self.con.parse(data, local_key=local_key)
        parsed_messages = [Container({"message": parsed.message})] if parsed.get("message") else parsed.messages
        messages = []
        for message in parsed_messages:
            messages.append(
                RoborockMessage(
                    version=message.message.value.version,
                    seq=message.message.value.seq,
                    random=message.message.value.get("random"),
                    timestamp=message.message.value.get("timestamp"),
                    protocol=message.message.value.protocol,
                    payload=message.message.value.payload,
                )
            )
        remaining = parsed.get("remaining") or b""
        return messages, remaining

    def build(
        self, roborock_messages: list[RoborockMessage] | RoborockMessage, local_key: str, prefixed: bool = True
    ) -> bytes:
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]
        messages = []
        for roborock_message in roborock_messages:
            messages.append(
                {
                    "message": {
                        "value": {
                            "version": roborock_message.version,
                            "seq": roborock_message.seq,
                            "random": roborock_message.random,
                            "timestamp": roborock_message.timestamp,
                            "protocol": roborock_message.protocol,
                            "payload": roborock_message.payload,
                        }
                    },
                }
            )
        return self.con.build(
            {"messages": [message for message in messages], "remaining": b""}, local_key=local_key, prefixed=prefixed
        )


MessageParser: _Parser = _Parser(_Messages, True)


def create_mqtt_params(rriot: RRiot) -> MqttParams:
    """Return the MQTT parameters for this user."""
    url = urlparse(rriot.r.m)
    if not isinstance(url.hostname, str):
        raise RoborockException(f"Url parsing '{rriot.r.m}' returned an invalid hostname")
    if not url.port:
        raise RoborockException(f"Url parsing '{rriot.r.m}' returned an invalid port")
    hashed_user = md5hex(rriot.u + ":" + rriot.k)[2:10]
    hashed_password = md5hex(rriot.s + ":" + rriot.k)[16:]
    return MqttParams(
        host=str(url.hostname),
        port=url.port,
        tls=(url.scheme == "ssl"),
        username=hashed_user,
        password=hashed_password,
    )


Decoder = Callable[[bytes], list[RoborockMessage]]
Encoder = Callable[[RoborockMessage], bytes]


def create_mqtt_decoder(local_key: str) -> Decoder:
    """Create a decoder for MQTT messages."""

    def decode(data: bytes) -> list[RoborockMessage]:
        """Parse the given data into Roborock messages."""
        messages, _ = MessageParser.parse(data, local_key)
        return messages

    return decode


def create_mqtt_encoder(local_key: str) -> Encoder:
    """Create an encoder for MQTT messages."""

    def encode(messages: RoborockMessage) -> bytes:
        """Build the given Roborock messages into a byte string."""
        return MessageParser.build(messages, local_key, prefixed=False)

    return encode


def create_local_decoder(local_key: str) -> Decoder:
    """Create a decoder for local API messages."""

    # This buffer is used to accumulate bytes until a complete message can be parsed.
    # It is defined outside the decode function to maintain state across calls.
    buffer: bytes = b""

    def decode(bytes: bytes) -> list[RoborockMessage]:
        """Parse the given data into Roborock messages."""
        nonlocal buffer
        buffer += bytes
        parsed_messages, remaining = MessageParser.parse(buffer, local_key=local_key)
        buffer = remaining
        return parsed_messages

    return decode


def create_local_encoder(local_key: str) -> Encoder:
    """Create an encoder for local API messages."""

    def encode(message: RoborockMessage) -> bytes:
        """Called when data is sent to the transport."""
        return MessageParser.build(message, local_key=local_key)

    return encode

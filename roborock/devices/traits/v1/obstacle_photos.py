"""Trait for fetching obstacle photos from V1 vacuums."""

from dataclasses import dataclass

from roborock.data import RoborockBase
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import SecurityData, V1RpcChannel
from roborock.roborock_typing import RoborockCommand

_PHOTO_TYPE_SMALL = 1
_PHOTO_DATA_BLOCK_TYPE = 3
_MAP_OBJECT_PHOTO_ENABLED_BIT = 10
_TYPE_SIZE = 2
_HEADER_SIZE_SIZE = 2
_PAYLOAD_SIZE_SIZE = 4
_MIN_BLOCK_HEADER_SIZE = _TYPE_SIZE + _HEADER_SIZE_SIZE + _PAYLOAD_SIZE_SIZE
_IMAGE_HEADERS = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")


@dataclass
class ObstaclePhoto(RoborockBase):
    """Obstacle photo content."""

    photo_id: str
    image_content: bytes


class ObstaclePhotoConverter(common.V1TraitDataConverter):
    """Convert a decrypted get_photo payload to an obstacle photo."""

    def convert(self, response: common.V1ResponseData) -> ObstaclePhoto:
        """Parse the response from the device into an obstacle photo."""
        if not isinstance(response, bytes):
            raise ValueError(f"Unexpected ObstaclePhotoTrait response format: {type(response)}")
        return ObstaclePhoto(photo_id="", image_content=parse_photo_data(response))


def parse_photo_data(response: bytes) -> bytes:
    """Parse the get_photo response payload and return image bytes.

    Roborock's app parses get_photo as a sequence of little-endian typed blocks.
    Block type 3 contains the image bytes.
    """
    offset = 0
    while offset + _MIN_BLOCK_HEADER_SIZE <= len(response):
        block_type = int.from_bytes(response[offset : offset + _TYPE_SIZE], "little")
        header_size = int.from_bytes(
            response[offset + _TYPE_SIZE : offset + _TYPE_SIZE + _HEADER_SIZE_SIZE],
            "little",
        )
        payload_size = int.from_bytes(
            response[offset + _TYPE_SIZE + _HEADER_SIZE_SIZE : offset + _MIN_BLOCK_HEADER_SIZE],
            "little",
        )
        next_offset = offset + header_size + payload_size
        if header_size < _MIN_BLOCK_HEADER_SIZE or next_offset > len(response):
            raise RoborockException("Invalid obstacle photo payload")

        if block_type == _PHOTO_DATA_BLOCK_TYPE:
            image_content = response[offset + header_size : next_offset]
            if not image_content.startswith(_IMAGE_HEADERS):
                raise RoborockException("Obstacle photo payload is not a supported image")
            return image_content

        offset = next_offset

    raise RoborockException("Obstacle photo payload does not contain photo data")


class ObstaclePhotoTrait(RoborockBase, common.V1TraitMixin):
    """Trait for fetching obstacle photos."""

    command = RoborockCommand.GET_PHOTO
    converter = ObstaclePhotoConverter()
    blob_rpc_channel = True
    requires_feature = "is_ai_recognition_obstacle_supported"

    def __init__(self, standard_rpc_channel: V1RpcChannel, security_data: SecurityData) -> None:
        """Initialize the obstacle photo trait."""
        super().__init__()
        self._standard_rpc_channel = standard_rpc_channel
        self._security_data = security_data

    async def get_enabled(self) -> bool:
        """Return whether map object photo capture is enabled on the vacuum."""
        response = await self._standard_rpc_channel.send_command(RoborockCommand.GET_CAMERA_STATUS)
        if not isinstance(response, list) or not response or not isinstance(response[0], int):
            raise RoborockException("get_camera_status response did not contain camera status")
        return bool((response[0] >> _MAP_OBJECT_PHOTO_ENABLED_BIT) & 1)

    async def get_photo(self, photo_id: str, photo_type: int = _PHOTO_TYPE_SMALL) -> ObstaclePhoto:
        """Fetch an obstacle photo by its map photo id."""
        public_key = await self._standard_rpc_channel.send_command(RoborockCommand.GET_RANDOM_PKEY)
        if not isinstance(public_key, dict) or not isinstance(public_key.get("pub_key"), dict):
            raise RoborockException("get_random_pkey response did not contain a public key")
        security = self._security_data.to_dict()["security"]
        response = await self.rpc_channel.send_command(
            self.command,
            params={
                "security": {
                    "pub_key": public_key["pub_key"],
                    "cipher_suite": 0,
                },
                "endpoint": security["endpoint"],
                "nonce": security["nonce"],
                "data_filter": {"img_id": photo_id, "type": photo_type},
            },
        )
        photo = self.converter.convert(response)
        photo.photo_id = photo_id
        return photo

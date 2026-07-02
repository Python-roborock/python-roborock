"""Map trait for B01 Q7 devices."""

from roborock.data import Q7MapList
from roborock.devices.rpc.b01_q7_channel import Q7RpcChannel
from roborock.devices.traits import Trait
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockB01Q7Methods


class MapTrait(Q7MapList, Trait):
    """Map trait for B01/Q7 devices, responsible for fetching and caching map list metadata.

    The MapContent is fetched from the MapContent trait, which relies on this trait to determine the
    current map ID to fetch.
    """

    def __init__(self, channel: Q7RpcChannel) -> None:
        super().__init__()
        self._channel = channel

    async def refresh(self) -> None:
        """Refresh cached map list metadata from the device."""
        response = await self._channel.send_command(
            command=RoborockB01Q7Methods.GET_MAP_LIST,
            params={},
        )
        if not isinstance(response, dict):
            raise RoborockException(
                f"Unexpected response type for GET_MAP_LIST: {type(response).__name__}: {response!r}"
            )

        if (parsed := Q7MapList.from_dict(response)) is None:
            raise RoborockException(f"Failed to decode map list response: {response!r}")

        self.map_list = parsed.map_list

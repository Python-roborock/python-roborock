"""Home and room endpoints (``/user/homes``, ``/user/deviceshare/.../rooms``)."""

from pyrate_limiter import Duration, Limiter, Rate

from roborock.data import HomeData, HomeDataRoom, UserData
from roborock.exceptions import RoborockException, RoborockRateLimit

from ._base import RoborockApiBase


class HomesApi(RoborockApiBase):
    """Home data (devices, products, rooms) lookups."""

    _HOME_DATA_RATES = [
        Rate(1, Duration.SECOND),
        Rate(3, Duration.MINUTE),
        Rate(5, Duration.HOUR),
        Rate(40, Duration.DAY),
    ]
    _home_data_limiter = Limiter(_HOME_DATA_RATES)

    async def _get_home_data_version(self, user_data: UserData, path_prefix: str) -> HomeData:
        """Fetch home data from ``{path_prefix}/user/homes/{home_id}`` with rate limiting."""
        if not self._home_data_limiter.try_acquire("home_data", blocking=False):
            raise RoborockRateLimit("Reached maximum requests for home data. Please try again later.")
        if user_data.rriot is None:
            raise RoborockException("rriot is none")
        home_id = await self._get_home_id(user_data)
        path = f"{path_prefix}/user/homes/{home_id}"
        home_request = self._rriot_request(user_data, path)
        home_response = await home_request.request("get", path)
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        raise RoborockException(f"home_response result was an unexpected type: {home_data}")

    async def get_home_data(self, user_data: UserData) -> HomeData:
        return await self._get_home_data_version(user_data, "")

    async def get_home_data_v2(self, user_data: UserData) -> HomeData:
        """This is the same as get_home_data, but uses a different endpoint and includes non-robotic vacuums."""
        return await self._get_home_data_version(user_data, "/v2")

    async def get_home_data_v3(self, user_data: UserData) -> HomeData:
        """This is the same as get_home_data, but uses a different endpoint and includes non-robotic vacuums."""
        return await self._get_home_data_version(user_data, "/v3")

    async def get_rooms(self, user_data: UserData, home_id: int | None = None) -> list[HomeDataRoom]:
        if user_data.rriot is None:
            raise RoborockException("rriot is none")
        if home_id is None:
            home_id = await self._get_home_id(user_data)
        path = f"/user/homes/{home_id}/rooms"
        room_request = self._rriot_request(user_data, path)
        room_response = await room_request.request("get", path)
        if not room_response.get("success"):
            raise RoborockException(room_response)
        rooms = room_response.get("result")
        if isinstance(rooms, list):
            return [HomeDataRoom.from_dict(room) for room in rooms]
        raise RoborockException("home_response result was an unexpected type")

    async def get_shared_device_rooms(self, user_data: UserData, device_id: str) -> list[HomeDataRoom]:
        """Fetch room names for a shared (received) device."""
        path = f"/user/deviceshare/query/{device_id}/rooms"
        room_request = self._rriot_request(user_data, path)
        room_response = await room_request.request("get", path)
        if not room_response.get("success"):
            raise RoborockException(room_response)
        rooms = room_response.get("result")
        if isinstance(rooms, list):
            output_list = []
            for room in rooms:
                normalized_room = room
                if isinstance(room, dict) and "id" not in room and "roomId" in room:
                    normalized_room = {**room, "id": room["roomId"]}
                output_list.append(HomeDataRoom.from_dict(normalized_room))
            return output_list
        raise RoborockException("get_shared_device_rooms result was an unexpected type")

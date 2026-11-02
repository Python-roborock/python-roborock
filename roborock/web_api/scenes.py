"""Scene (routine) endpoints (``/user/scene``)."""

from roborock.data import HomeDataScene, UserData
from roborock.exceptions import RoborockException

from ._base import RoborockApiBase


class ScenesApi(RoborockApiBase):
    """Listing and executing app routines."""

    async def get_scenes(self, user_data: UserData, device_id: str) -> list[HomeDataScene]:
        path = f"/user/scene/device/{str(device_id)}"
        scenes_request = self._rriot_request(user_data, path)
        scenes_response = await scenes_request.request("get", path)
        if not scenes_response.get("success"):
            raise RoborockException(scenes_response)
        scenes = scenes_response.get("result")
        if isinstance(scenes, list):
            return [HomeDataScene.from_dict(scene) for scene in scenes]
        raise RoborockException("scene_response result was an unexpected type")

    async def execute_scene(self, user_data: UserData, scene_id: int) -> None:
        path = f"/user/scene/{str(scene_id)}/execute"
        execute_scene_request = self._rriot_request(user_data, path)
        execute_scene_response = await execute_scene_request.request("POST", path)
        if not execute_scene_response.get("success"):
            raise RoborockException(execute_scene_response)

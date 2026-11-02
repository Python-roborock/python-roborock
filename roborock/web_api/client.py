"""Public web API clients composed from the per-resource mixins."""

from collections.abc import Callable

from roborock.data import HomeData, HomeDataRoom, HomeDataScene, UserData
from roborock.exceptions import RoborockInvalidCredentials

from .auth import AuthApi
from .devices import DevicesApi
from .homes import HomesApi
from .jobs import JobsApi
from .ota import OtaApi
from .products import ProductsApi
from .scenes import ScenesApi


class RoborockApiClient(AuthApi, HomesApi, DevicesApi, ScenesApi, JobsApi, OtaApi, ProductsApi):
    """Client for the Roborock cloud REST APIs.

    Each group of endpoints lives in its own mixin (``roborock.web_api.auth``,
    ``roborock.web_api.homes`` ...); this class simply composes them so callers keep a
    single entry point.
    """


class UserWebApiClient:
    """Wrapper around RoborockApiClient to provide information for a specific user.

    This binds a RoborockApiClient to a specific user context with the
    provided UserData. This allows for easier access to user-specific data,
    to avoid needing to pass UserData around and mock out the web API.
    """

    def __init__(
        self, web_api: RoborockApiClient, user_data: UserData, unauthorized_hook: Callable[[], None] | None = None
    ) -> None:
        """Initialize the wrapper with the API client and user data."""
        self._web_api = web_api
        self._user_data = user_data
        self._unauthorized_hook = unauthorized_hook

    async def get_home_data(self) -> HomeData:
        """Fetch home data using the API client."""
        try:
            return await self._web_api.get_home_data_v3(self._user_data)
        except RoborockInvalidCredentials:
            if self._unauthorized_hook:
                self._unauthorized_hook()
            raise

    async def get_routines(self, device_id: str) -> list[HomeDataScene]:
        """Fetch routines (scenes) for a specific device."""
        try:
            return await self._web_api.get_scenes(self._user_data, device_id)
        except RoborockInvalidCredentials:
            if self._unauthorized_hook:
                self._unauthorized_hook()
            raise

    async def get_rooms(self) -> list[HomeDataRoom]:
        """Fetch rooms using the API client."""
        try:
            return await self._web_api.get_rooms(self._user_data)
        except RoborockInvalidCredentials:
            if self._unauthorized_hook:
                self._unauthorized_hook()
            raise

    async def get_shared_device_rooms(self, device_id: str) -> list[HomeDataRoom]:
        """Fetch shared-device rooms using the API client."""
        return await self._web_api.get_shared_device_rooms(self._user_data, device_id)

    async def execute_routine(self, scene_id: int) -> None:
        """Execute a specific routine (scene) by its ID."""
        try:
            await self._web_api.execute_scene(self._user_data, scene_id)
        except RoborockInvalidCredentials:
            if self._unauthorized_hook:
                self._unauthorized_hook()
            raise

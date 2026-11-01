"""Tests for scene (routine) endpoints."""

from roborock import HomeDataScene
from roborock.web_api import RoborockApiClient


async def test_get_scenes():
    """Test that we can get scenes"""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    sc = await api.get_scenes(ud, "123456")
    assert sc == [
        HomeDataScene.from_dict(
            {
                "id": 1234567,
                "name": "My plan",
            }
        )
    ]


async def test_execute_scene(mock_rest):
    """Test that we can execute a scene"""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    await api.execute_scene(ud, 123456)
    mock_rest.assert_any_call("https://api-us.roborock.com/user/scene/123456/execute", "post")

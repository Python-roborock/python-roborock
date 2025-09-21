import aiohttp

from roborock import HomeData, HomeDataScene, UserData
from roborock.web_api import RoborockApiClient
from tests.mock_data import HOME_DATA_RAW, USER_DATA


async def test_pass_login_flow() -> None:
    """Test that we can login with a password and we get back the correct userdata object."""
    my_session = aiohttp.ClientSession()
    api = RoborockApiClient(username="test_user@gmail.com", session=my_session)
    ud = await api.pass_login("password")
    assert ud == UserData.from_dict(USER_DATA)
    assert not my_session.closed


async def test_code_login_flow() -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    assert ud == UserData.from_dict(USER_DATA)


async def test_get_home_data_v2():
    """Test a full standard flow where we get the home data to end it off.
    This matches what HA does"""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    hd = await api.get_home_data_v2(ud)
    assert hd == HomeData.from_dict(HOME_DATA_RAW)


async def test_nc_prepare():
    """Test adding a device and that nothing breaks"""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    prepare = await api.nc_prepare(ud, "America/New_York")
    new_device = await api.add_device(ud, prepare["s"], prepare["t"])
    assert new_device["duid"] == "rand_duid"


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


async def test_code_login_v4_flow(mock_rest) -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    ud = await api.code_login_v4(4123, "US", 1)
    assert ud == UserData.from_dict(USER_DATA)


async def test_get_country_code_and_country(mock_rest) -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com", base_url="https://euiot.roborock.com")
    res = await api.get_country_code_and_country()
    assert res == {"country": USER_DATA["country"], "countrycode": USER_DATA["countrycode"]}

from roborock import HomeData, UserData
from roborock.web_api import RoborockApiClient
from tests.mock_data import HOME_DATA_RAW, USER_DATA


async def test_pass_login_flow() -> None:
    """Test that we can login with a password and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    assert ud == UserData.from_dict(USER_DATA)


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

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import math
import secrets
import string
import time
from dataclasses import dataclass

import aiohttp
from aiohttp import ContentTypeError, FormData
from pyrate_limiter import BucketFullException, Duration, Limiter, Rate

from roborock.data import HomeData, HomeDataRoom, HomeDataScene, ProductResponse, RRiot, UserData
from roborock.exceptions import (
    RoborockAccountDoesNotExist,
    RoborockException,
    RoborockInvalidCode,
    RoborockInvalidCredentials,
    RoborockInvalidEmail,
    RoborockInvalidUserAgreement,
    RoborockMissingParameters,
    RoborockNoResponseFromBaseURL,
    RoborockNoUserAgreement,
    RoborockRateLimit,
    RoborockTooFrequentCodeRequests,
)

_LOGGER = logging.getLogger(__name__)
BASE_URLS = [
    "https://usiot.roborock.com",
    "https://euiot.roborock.com",
    "https://cniot.roborock.com",
    "https://ruiot.roborock.com",
]


@dataclass
class IotLoginInfo:
    """Information about the login to the iot server."""

    base_url: str
    country_code: str
    country: str


class RoborockApiClient:
    _LOGIN_RATES = [
        Rate(1, Duration.SECOND),
        Rate(3, Duration.MINUTE),
        Rate(10, Duration.HOUR),
        Rate(20, Duration.DAY),
    ]
    _HOME_DATA_RATES = [
        Rate(1, Duration.SECOND),
        Rate(5, Duration.MINUTE),
        Rate(15, Duration.HOUR),
        Rate(40, Duration.DAY),
    ]

    _login_limiter = Limiter(_LOGIN_RATES)
    _home_data_limiter = Limiter(_HOME_DATA_RATES)

    def __init__(
        self, username: str, base_url: str | None = None, session: aiohttp.ClientSession | None = None
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._base_url = base_url
        self._device_identifier = secrets.token_urlsafe(16)
        self.session = session
        self._iot_login_info: IotLoginInfo | None = None

    async def _get_iot_login_info(self) -> IotLoginInfo:
        if self._iot_login_info is None:
            valid_urls = BASE_URLS if self._base_url is None else [self._base_url]
            for iot_url in valid_urls:
                url_request = PreparedRequest(iot_url, self.session)
                response = await url_request.request(
                    "post",
                    "/api/v1/getUrlByEmail",
                    params={"email": self._username, "needtwostepauth": "false"},
                )
                if response is None:
                    continue
                response_code = response.get("code")
                if response_code != 200:
                    if response_code == 2003:
                        raise RoborockInvalidEmail("Your email was incorrectly formatted.")
                    elif response_code == 1001:
                        raise RoborockMissingParameters(
                            "You are missing parameters for this request, are you sure you entered your username?"
                        )
                    else:
                        raise RoborockException(f"{response.get('msg')} - response code: {response_code}")
                country_code = response["data"]["countrycode"]
                country = response["data"]["country"]
                if country_code is not None or country is not None:
                    self._iot_login_info = IotLoginInfo(
                        base_url=response["data"]["url"],
                        country=country,
                        country_code=country_code,
                    )
                    _LOGGER.debug("Country determined to be %s and code is %s", country, country_code)
                    return self._iot_login_info
            raise RoborockNoResponseFromBaseURL(
                "No account was found for any base url we tried. Either your email is incorrect or we do not have a"
                " record of the roborock server your device is on."
            )
        return self._iot_login_info

    @property
    async def base_url(self):
        if self._base_url is not None:
            return self._base_url
        return (await self._get_iot_login_info()).base_url

    @property
    async def country(self):
        return (await self._get_iot_login_info()).country

    @property
    async def country_code(self):
        return (await self._get_iot_login_info()).country_code

    def _get_header_client_id(self):
        md5 = hashlib.md5()
        md5.update(self._username.encode())
        md5.update(self._device_identifier.encode())
        return base64.b64encode(md5.digest()).decode()

    async def nc_prepare(self, user_data: UserData, timezone: str) -> dict:
        """This gets a few critical parameters for adding a device to your account."""
        if (
            user_data.rriot is None
            or user_data.rriot.r is None
            or user_data.rriot.u is None
            or user_data.rriot.r.a is None
        ):
            raise RoborockException("Your userdata is missing critical attributes.")
        base_url = user_data.rriot.r.a
        prepare_request = PreparedRequest(base_url, self.session)
        hid = await self._get_home_id(user_data)

        data = FormData()
        data.add_field("hid", hid)
        data.add_field("tzid", timezone)

        prepare_response = await prepare_request.request(
            "post",
            "/nc/prepare",
            headers={
                "Authorization": _get_hawk_authentication(
                    user_data.rriot, "/nc/prepare", {"hid": hid, "tzid": timezone}
                ),
            },
            data=data,
        )

        if prepare_response is None:
            raise RoborockException("prepare_response is None")
        if not prepare_response.get("success"):
            raise RoborockException(f"{prepare_response.get('msg')} - response code: {prepare_response.get('code')}")

        return prepare_response["result"]

    async def add_device(self, user_data: UserData, s: str, t: str) -> dict:
        """This will add a new device to your account
        it is recommended to only use this during a pairing cycle with a device.
        Please see here: https://github.com/Python-roborock/Roborockmitmproxy/blob/main/handshake_protocol.md
        """
        if (
            user_data.rriot is None
            or user_data.rriot.r is None
            or user_data.rriot.u is None
            or user_data.rriot.r.a is None
        ):
            raise RoborockException("Your userdata is missing critical attributes.")
        base_url = user_data.rriot.r.a
        add_device_request = PreparedRequest(base_url, self.session)

        add_device_response = await add_device_request.request(
            "GET",
            "/user/devices/newadd",
            headers={
                "Authorization": _get_hawk_authentication(
                    user_data.rriot, "/user/devices/newadd", params={"s": s, "t": t}
                ),
            },
            params={"s": s, "t": t},
        )

        if add_device_response is None:
            raise RoborockException("add_device is None")
        if not add_device_response.get("success"):
            raise RoborockException(
                f"{add_device_response.get('msg')} - response code: {add_device_response.get('code')}"
            )

        return add_device_response["result"]

    async def request_code(self) -> None:
        try:
            self._login_limiter.try_acquire("login")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.") from ex
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        code_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})

        code_response = await code_request.request(
            "post",
            "/api/v1/sendEmailCode",
            params={
                "username": self._username,
                "type": "auth",
            },
        )
        if code_response is None:
            raise RoborockException("Failed to get a response from send email code")
        response_code = code_response.get("code")
        if response_code != 200:
            _LOGGER.info("Request code failed for %s with the following context: %s", self._username, code_response)
            if response_code == 2008:
                raise RoborockAccountDoesNotExist("Account does not exist - check your login and try again.")
            elif response_code == 9002:
                raise RoborockTooFrequentCodeRequests("You have attempted to request too many codes. Try again later")
            else:
                raise RoborockException(f"{code_response.get('msg')} - response code: {code_response.get('code')}")

    async def request_code_v4(self) -> None:
        """Request a code using the v4 endpoint."""
        if await self.country_code is None or await self.country is None:
            _LOGGER.info("No country code or country found, trying old version of request code.")
            return await self.request_code()
        try:
            self._login_limiter.try_acquire("login")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.") from ex
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        code_request = PreparedRequest(
            base_url,
            self.session,
            {
                "header_clientid": header_clientid,
                "Content-Type": "application/x-www-form-urlencoded",
                "header_clientlang": "en",
            },
        )

        code_response = await code_request.request(
            "post",
            "/api/v4/email/code/send",
            params={"email": self._username, "type": "login", "platform": ""},
        )
        if code_response is None:
            raise RoborockException("Failed to get a response from send email code")
        response_code = code_response.get("code")
        if response_code != 200:
            _LOGGER.info("Request code failed for %s with the following context: %s", self._username, code_response)
            if response_code == 2008:
                raise RoborockAccountDoesNotExist("Account does not exist - check your login and try again.")
            elif response_code == 9002:
                raise RoborockTooFrequentCodeRequests("You have attempted to request too many codes. Try again later")
            else:
                raise RoborockException(f"{code_response.get('msg')} - response code: {code_response.get('code')}")

    async def _sign_key_v3(self, s: str) -> str:
        """Sign a randomly generated string."""
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        code_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})

        code_response = await code_request.request(
            "post",
            "/api/v3/key/sign",
            params={"s": s},
        )

        if not code_response or "data" not in code_response or "k" not in code_response["data"]:
            raise RoborockException("Failed to get a response from sign key")
        response_code = code_response.get("code")

        if response_code != 200:
            _LOGGER.info("Request code failed for %s with the following context: %s", self._username, code_response)
            raise RoborockException(f"{code_response.get('msg')} - response code: {code_response.get('code')}")

        return code_response["data"]["k"]

    async def code_login_v4(
        self, code: int | str, country: str | None = None, country_code: int | None = None
    ) -> UserData:
        """
        Login via code authentication.
        :param code: The code from the email.
        :param country: The two-character representation of the country, i.e. "US"
        :param country_code: the country phone number code i.e. 1 for US.
        """
        base_url = await self.base_url
        if country is None:
            country = await self.country
        if country_code is None:
            country_code = await self.country_code
        if country_code is None or country is None:
            _LOGGER.info("No country code or country found, trying old version of code login.")
            return await self.code_login(code)
        header_clientid = self._get_header_client_id()
        x_mercy_ks = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        x_mercy_k = await self._sign_key_v3(x_mercy_ks)
        login_request = PreparedRequest(
            base_url,
            self.session,
            {"header_clientid": header_clientid, "x-mercy-ks": x_mercy_ks, "x-mercy-k": x_mercy_k},
        )
        login_response = await login_request.request(
            "post",
            "/api/v4/auth/email/login/code",
            params={
                "country": country,
                "countryCode": country_code,
                "email": self._username,
                "code": code,
                # Major and minor version are the user agreement version, we will need to see if this needs to be
                # dynamic https://usiot.roborock.com/api/v3/app/agreement/latest?country=US
                "majorVersion": 14,
                "minorVersion": 0,
            },
        )
        if login_response is None:
            raise RoborockException("Login request response is None")
        response_code = login_response.get("code")
        if response_code != 200:
            _LOGGER.info("Login failed for %s with the following context: %s", self._username, login_response)
            if response_code == 2018:
                raise RoborockInvalidCode("Invalid code - check your code and try again.")
            if response_code == 3009:
                raise RoborockNoUserAgreement("You must accept the user agreement in the Roborock app to continue.")
            if response_code == 3006:
                raise RoborockInvalidUserAgreement(
                    "User agreement must be accepted again - or you are attempting to use the Mi Home app account."
                )
            raise RoborockException(f"{login_response.get('msg')} - response code: {response_code}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def pass_login(self, password: str) -> UserData:
        try:
            self._login_limiter.try_acquire("login")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.") from ex
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()

        login_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        login_response = await login_request.request(
            "post",
            "/api/v1/login",
            params={
                "username": self._username,
                "password": password,
                "needtwostepauth": "false",
            },
        )
        if login_response is None:
            raise RoborockException("Login response is none")
        if login_response.get("code") != 200:
            _LOGGER.info("Login failed for %s with the following context: %s", self._username, login_response)
            raise RoborockException(f"{login_response.get('msg')} - response code: {login_response.get('code')}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def pass_login_v3(self, password: str) -> UserData:
        """Seemingly it follows the format below, but password is encrypted in some manner.
        # login_response = await login_request.request(
        #     "post",
        #     "/api/v3/auth/email/login",
        #     params={
        #         "email": self._username,
        #         "password": password,
        #         "twoStep": 1,
        #         "version": 0
        #     },
        # )
        """
        raise NotImplementedError("Pass_login_v3 has not yet been implemented")

    async def code_login(self, code: int | str) -> UserData:
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()

        login_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        login_response = await login_request.request(
            "post",
            "/api/v1/loginWithCode",
            params={
                "username": self._username,
                "verifycode": code,
                "verifycodetype": "AUTH_EMAIL_CODE",
            },
        )
        if login_response is None:
            raise RoborockException("Login request response is None")
        response_code = login_response.get("code")
        if response_code != 200:
            _LOGGER.info("Login failed for %s with the following context: %s", self._username, login_response)
            if response_code == 2018:
                raise RoborockInvalidCode("Invalid code - check your code and try again.")
            if response_code == 3009:
                raise RoborockNoUserAgreement("You must accept the user agreement in the Roborock app to continue.")
            if response_code == 3006:
                raise RoborockInvalidUserAgreement(
                    "User agreement must be accepted again - or you are attempting to use the Mi Home app account."
                )
            raise RoborockException(f"{login_response.get('msg')} - response code: {response_code}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def _get_home_id(self, user_data: UserData):
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        home_id_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        home_id_response = await home_id_request.request(
            "get",
            "/api/v1/getHomeDetail",
            headers={"Authorization": user_data.token},
        )
        if home_id_response is None:
            raise RoborockException("home_id_response is None")
        if home_id_response.get("code") != 200:
            _LOGGER.info("Get Home Id failed with the following context: %s", home_id_response)
            if home_id_response.get("code") == 2010:
                raise RoborockInvalidCredentials(
                    f"Invalid credentials ({home_id_response.get('msg')}) - check your login and try again."
                )
            raise RoborockException(f"{home_id_response.get('msg')} - response code: {home_id_response.get('code')}")

        return home_id_response["data"]["rrHomeId"]

    async def get_home_data(self, user_data: UserData) -> HomeData:
        try:
            self._home_data_limiter.try_acquire("home_data")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for home data. Please try again later.") from ex
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        home_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, f"/user/homes/{str(home_id)}"),
            },
        )
        home_response = await home_request.request("get", "/user/homes/" + str(home_id))
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_home_data_v2(self, user_data: UserData) -> HomeData:
        """This is the same as get_home_data, but uses a different endpoint and includes non-robotic vacuums."""
        try:
            self._home_data_limiter.try_acquire("home_data")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for home data. Please try again later.") from ex
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        home_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, "/v2/user/homes/" + str(home_id)),
            },
        )
        home_response = await home_request.request("get", "/v2/user/homes/" + str(home_id))
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_home_data_v3(self, user_data: UserData) -> HomeData:
        """This is the same as get_home_data, but uses a different endpoint and includes non-robotic vacuums."""
        try:
            self._home_data_limiter.try_acquire("home_data")
        except BucketFullException as ex:
            _LOGGER.info(ex.meta_info)
            raise RoborockRateLimit("Reached maximum requests for home data. Please try again later.") from ex
        rriot = user_data.rriot
        home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        home_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, "/v3/user/homes/" + str(home_id)),
            },
        )
        home_response = await home_request.request("get", "/v3/user/homes/" + str(home_id))
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        raise RoborockException(f"home_response result was an unexpected type: {home_data}")

    async def get_rooms(self, user_data: UserData, home_id: int | None = None) -> list[HomeDataRoom]:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        if home_id is None:
            home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        room_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, "/v2/user/homes/" + str(home_id)),
            },
        )
        room_response = await room_request.request("get", f"/user/homes/{str(home_id)}/rooms" + str(home_id))
        if not room_response.get("success"):
            raise RoborockException(room_response)
        rooms = room_response.get("result")
        if isinstance(rooms, list):
            output_list = []
            for room in rooms:
                output_list.append(HomeDataRoom.from_dict(room))
            return output_list
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_scenes(self, user_data: UserData, device_id: str) -> list[HomeDataScene]:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        scenes_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, f"/user/scene/device/{str(device_id)}"),
            },
        )
        scenes_response = await scenes_request.request("get", f"/user/scene/device/{str(device_id)}")
        if not scenes_response.get("success"):
            raise RoborockException(scenes_response)
        scenes = scenes_response.get("result")
        if isinstance(scenes, list):
            return [HomeDataScene.from_dict(scene) for scene in scenes]
        else:
            raise RoborockException("scene_response result was an unexpected type")

    async def execute_scene(self, user_data: UserData, scene_id: int) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        execute_scene_request = PreparedRequest(
            rriot.r.a,
            self.session,
            {
                "Authorization": _get_hawk_authentication(rriot, f"/user/scene/{str(scene_id)}/execute"),
            },
        )
        execute_scene_response = await execute_scene_request.request("POST", f"/user/scene/{str(scene_id)}/execute")
        if not execute_scene_response.get("success"):
            raise RoborockException(execute_scene_response)

    async def get_products(self, user_data: UserData) -> ProductResponse:
        """Gets all products and their schemas, good for determining status codes and model numbers."""
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        product_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        product_response = await product_request.request(
            "get",
            "/api/v4/product",
            headers={"Authorization": user_data.token},
        )
        if product_response is None:
            raise RoborockException("home_id_response is None")
        if product_response.get("code") != 200:
            raise RoborockException(f"{product_response.get('msg')} - response code: {product_response.get('code')}")
        result = product_response.get("data")
        if isinstance(result, dict):
            return ProductResponse.from_dict(result)
        raise RoborockException("product result was an unexpected type")

    async def download_code(self, user_data: UserData, product_id: int):
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        product_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        request = {"apilevel": 99999, "productids": [product_id], "type": 2}
        response = await product_request.request(
            "post",
            "/api/v1/appplugin",
            json=request,
            headers={"Authorization": user_data.token, "Content-Type": "application/json"},
        )
        return response["data"][0]["url"]

    async def download_category_code(self, user_data: UserData):
        base_url = await self.base_url
        header_clientid = self._get_header_client_id()
        product_request = PreparedRequest(base_url, self.session, {"header_clientid": header_clientid})
        response = await product_request.request(
            "get",
            "api/v1/plugins?apiLevel=99999&type=2",
            headers={
                "Authorization": user_data.token,
            },
        )
        return {r["category"]: r["url"] for r in response["data"]["categoryPluginList"]}


class PreparedRequest:
    def __init__(
        self, base_url: str, session: aiohttp.ClientSession | None = None, base_headers: dict | None = None
    ) -> None:
        self.base_url = base_url
        self.base_headers = base_headers or {}
        self.session = session

    async def request(self, method: str, url: str, params=None, data=None, headers=None, json=None) -> dict:
        _url = "/".join(s.strip("/") for s in [self.base_url, url])
        _headers = {**self.base_headers, **(headers or {})}
        close_session = self.session is None
        session = self.session if self.session is not None else aiohttp.ClientSession()
        try:
            async with session.request(method, _url, params=params, data=data, headers=_headers, json=json) as resp:
                return await resp.json()
        except ContentTypeError as err:
            """If we get an error, lets log everything for debugging."""
            try:
                resp_json = await resp.json(content_type=None)
                _LOGGER.info("Resp: %s", resp_json)
            except ContentTypeError as err_2:
                _LOGGER.info(err_2)
            resp_raw = await resp.read()
            _LOGGER.info("Resp raw: %s", resp_raw)
            # Still raise the err so that it's clear it failed.
            raise err
        finally:
            if close_session:
                await session.close()


def _process_extra_hawk_values(values: dict | None) -> str:
    if values is None:
        return ""
    else:
        sorted_keys = sorted(values.keys())
        result = []
        for key in sorted_keys:
            value = values.get(key)
            result.append(f"{key}={value}")
        return hashlib.md5("&".join(result).encode()).hexdigest()


def _get_hawk_authentication(rriot: RRiot, url: str, formdata: dict | None = None, params: dict | None = None) -> str:
    timestamp = math.floor(time.time())
    nonce = secrets.token_urlsafe(6)
    formdata_str = _process_extra_hawk_values(formdata)
    params_str = _process_extra_hawk_values(params)

    prestr = ":".join(
        [
            rriot.u,
            rriot.s,
            nonce,
            str(timestamp),
            hashlib.md5(url.encode()).hexdigest(),
            params_str,
            formdata_str,
        ]
    )
    mac = base64.b64encode(hmac.new(rriot.h.encode(), prestr.encode(), hashlib.sha256).digest()).decode()
    return f'Hawk id="{rriot.u}",s="{rriot.s}",ts="{timestamp}",nonce="{nonce}",mac="{mac}"'


class UserWebApiClient:
    """Wrapper around RoborockApiClient to provide information for a specific user.

    This binds a RoborockApiClient to a specific user context with the
    provided UserData. This allows for easier access to user-specific data,
    to avoid needing to pass UserData around and mock out the web API.
    """

    def __init__(self, web_api: RoborockApiClient, user_data: UserData) -> None:
        """Initialize the wrapper with the API client and user data."""
        self._web_api = web_api
        self._user_data = user_data

    async def get_home_data(self) -> HomeData:
        """Fetch home data using the API client."""
        return await self._web_api.get_home_data_v3(self._user_data)

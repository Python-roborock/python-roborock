"""Shared state and request-building helpers for the web API mixins.

Every resource mixin (``AuthApi``, ``HomesApi``, ``JobsApi`` ...) inherits from
``RoborockApiBase`` so that it can rely on the username, session, regional base
URL resolution and the two request builders defined here. ``RoborockApiClient``
composes the mixins into the single public client.
"""

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass

import aiohttp

from roborock.data import UserData
from roborock.exceptions import (
    RoborockException,
    RoborockInvalidCredentials,
    RoborockInvalidEmail,
    RoborockMissingParameters,
    RoborockNoResponseFromBaseURL,
)

from ._hawk import _get_hawk_authentication
from ._request import PreparedRequest

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


class RoborockApiBase:
    """State and helpers shared by all web API resource mixins."""

    def __init__(
        self, username: str, base_url: str | None = None, session: aiohttp.ClientSession | None = None
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._base_url = base_url
        self._device_identifier = secrets.token_urlsafe(16)
        self.session = session
        self._iot_login_info: IotLoginInfo | None = None
        self._base_urls = BASE_URLS if base_url is None else [base_url]

    async def _get_iot_login_info(self) -> IotLoginInfo:
        if self._iot_login_info is None:
            for iot_url in self._base_urls:
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

    async def _iot_request(self, extra_headers: dict | None = None) -> PreparedRequest:
        """Build a request against the regional Base IoT server with the standard client headers."""
        base_url = await self.base_url
        headers = {"header_clientid": self._get_header_client_id(), **(extra_headers or {})}
        return PreparedRequest(base_url, self.session, headers)

    def _rriot_request(
        self,
        user_data: UserData,
        path: str,
        *,
        formdata: dict | None = None,
        params: dict | None = None,
        body: dict | None = None,
        extra_headers: dict | None = None,
    ) -> PreparedRequest:
        """Build a Hawk-authenticated request against the RRIoT server for ``path``.

        The same ``formdata``/``params``/``body`` passed here must be sent on the request so
        that the signed MAC matches what the server receives.
        """
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        headers = {
            "Authorization": _get_hawk_authentication(rriot, path, formdata=formdata, params=params, body=body),
            **(extra_headers or {}),
        }
        return PreparedRequest(rriot.r.a, self.session, headers)

    async def _get_home_id(self, user_data: UserData):
        home_id_request = await self._iot_request()
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

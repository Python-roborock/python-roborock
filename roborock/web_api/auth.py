"""Login, verification-code and account-discovery endpoints on the Base IoT API."""

import logging
import secrets
import string

from pyrate_limiter import Duration, Limiter, Rate

from roborock.data import UserData
from roborock.exceptions import (
    RoborockAccountDoesNotExist,
    RoborockException,
    RoborockInvalidCode,
    RoborockInvalidUserAgreement,
    RoborockNoUserAgreement,
    RoborockRateLimit,
    RoborockTooFrequentCodeRequests,
)

from ._base import RoborockApiBase
from ._request import PreparedRequest

_LOGGER = logging.getLogger(__name__)

# Fallback user agreement version, used only if the latest version cannot be fetched.
DEFAULT_AGREEMENT_MAJOR_VERSION = 14
DEFAULT_AGREEMENT_MINOR_VERSION = 0


class AuthApi(RoborockApiBase):
    """Email/password and email-code login flows."""

    _LOGIN_RATES = [
        Rate(1, Duration.SECOND),
        Rate(3, Duration.MINUTE),
        Rate(10, Duration.HOUR),
        Rate(20, Duration.DAY),
    ]
    _login_limiter = Limiter(_LOGIN_RATES)

    async def request_code(self) -> None:
        if not await self._login_limiter.try_acquire_async("login", blocking=True, timeout=1):
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.")
        code_request = await self._iot_request()

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
        if not await self._login_limiter.try_acquire_async("login", blocking=True, timeout=1):
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.")
        code_request = await self._iot_request(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "header_clientlang": "en",
            }
        )

        code_response = await code_request.request(
            "post",
            "/api/v4/email/code/send",
            data={"email": self._username, "type": "login", "platform": ""},
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
            elif response_code == 3030 and len(self._base_urls) > 1:
                self._base_urls = self._base_urls[1:]
                self._iot_login_info = None
                return await self.request_code_v4()
            else:
                raise RoborockException(f"{code_response.get('msg')} - response code: {code_response.get('code')}")

    async def _sign_key_v3(self, s: str) -> str:
        """Sign a randomly generated string."""
        code_request = await self._iot_request()

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

    async def _get_agreement_version(self, country: str) -> dict[str, int]:
        """Get the latest user agreement version for the given country.

        The login endpoint rejects a stale agreement version with code 3006. The
        current version differs per server and per country, so it must be looked
        up rather than hardcoded. Falls back to the previously hardcoded values
        if the lookup fails so that login is never blocked by this request.
        """
        try:
            base_url = await self.base_url
            agreement_request = PreparedRequest(base_url, self.session, {"header_clientlang": "en"})
            response = await agreement_request.request(
                "get",
                "/api/v3/app/agreement/latest",
                params={"country": country},
            )
            if response is not None and response.get("code") == 200:
                data = response.get("data") or {}
                major = data.get("majorVersion")
                minor = data.get("minorVersion")
                if isinstance(major, int) and isinstance(minor, int):
                    _LOGGER.debug("Using user agreement version %s.%s for %s", major, minor, country)
                    return {"majorVersion": major, "minorVersion": minor}
            _LOGGER.debug("Unexpected agreement version response: %s", response)
        except RoborockException as err:
            _LOGGER.debug("Could not fetch latest user agreement version: %s", err)
        return {"majorVersion": DEFAULT_AGREEMENT_MAJOR_VERSION, "minorVersion": DEFAULT_AGREEMENT_MINOR_VERSION}

    async def code_login_v4(
        self, code: int | str, country: str | None = None, country_code: int | None = None
    ) -> UserData:
        """
        Login via code authentication.
        :param code: The code from the email.
        :param country: The two-character representation of the country, i.e. "US"
        :param country_code: the country phone number code i.e. 1 for US.
        """
        if country is None:
            country = await self.country
        if country_code is None:
            country_code = await self.country_code
        if country_code is None or country is None:
            _LOGGER.info("No country code or country found, trying old version of code login.")
            return await self.code_login(code)
        x_mercy_ks = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        x_mercy_k = await self._sign_key_v3(x_mercy_ks)
        login_request = await self._iot_request(
            {
                "x-mercy-ks": x_mercy_ks,
                "x-mercy-k": x_mercy_k,
                "Content-Type": "application/x-www-form-urlencoded",
                "header_clientlang": "en",
                "header_appversion": "4.54.02",
                "header_phonesystem": "iOS",
                "header_phonemodel": "iPhone16,1",
            }
        )
        login_response = await login_request.request(
            "post",
            "/api/v4/auth/email/login/code",
            data={
                "country": country,
                "countryCode": country_code,
                "email": self._username,
                "code": code,
                **await self._get_agreement_version(country),
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
            if response_code == 3039:
                raise RoborockAccountDoesNotExist(
                    "This account does not exist - please ensure that you selected the right region and email."
                )
            raise RoborockException(f"{login_response.get('msg')} - response code: {response_code}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def pass_login(self, password: str) -> UserData:
        if not await self._login_limiter.try_acquire_async("login", blocking=True, timeout=1):
            raise RoborockRateLimit("Reached maximum requests for login. Please try again later.")
        login_request = await self._iot_request()
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
        login_request = await self._iot_request()
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

"""Cloud environment simulator for python-roborock testing.

This module provides `FakeRoborockCloud` which acts as a central registry
for all simulated devices, dynamically faking HTTP endpoints via aioresponses
to simulate physical devices connected to the Roborock Cloud.
"""

import contextlib
import re
from typing import Any
from unittest.mock import AsyncMock, patch

from aioresponses import CallbackResult, aioresponses

from roborock.data import HomeData, Reference, RRiot, UserData
from roborock.devices.rpc.v1_channel import create_v1_channel as original_create_v1_channel
from roborock.devices.transport.mqtt_channel import create_mqtt_channel as original_create_mqtt_channel
from roborock.testing.simulator import RoborockDeviceSimulator
from roborock.testing.v1_simulator import V1VacuumSimulator

# EAPI Base URL pattern constants
IOT_API_BASE_URL = r"https://.*iot\.roborock\.com/api/v1"
REST_API_BASE_URL = r"https://api-.*\.roborock\.com"

DEFAULT_USER_DATA = UserData(
    uid=123456,
    tokentype="token_type",
    token="abc123",
    rruid="abc123",
    region="us",
    countrycode="1",
    country="US",
    nickname="user_nickname",
    rriot=RRiot(
        u="user123",
        s="pass123",
        h="unknown123",
        k="qiCNieZa",
        r=Reference(
            r="US",
            a="https://api-us.roborock.com",
            l="https://wood-us.roborock.com",
            m="tcp://mqtt-us.roborock.com:8883",
        ),
    ),
)


class FakeWebApiClient:
    """Fakes the EAPI at the HTTP network boundary using aioresponses.

    Exposes attributes that allow test suites (like Home Assistant) to easily
    override response payloads, status codes, and simulate API errors.
    """

    def __init__(self, cloud: "FakeRoborockCloud"):
        self.cloud = cloud
        self.url_by_email_status = 200
        self.url_by_email_payload: dict[str, Any] | None = None  # Synthesized if None
        self.login_status = 200
        self.login_payload: dict[str, Any] | None = None  # Synthesized if None
        self.home_detail_status = 200
        self.home_detail_payload: dict[str, Any] | None = None  # Synthesized if None
        self.homes_status = 200
        self.homes_payload_override: dict[str, Any] | None = None

    def get_url_by_email_payload(self) -> dict[str, Any]:
        """Synthesize getUrlByEmail payload."""
        if self.url_by_email_payload is not None:
            return self.url_by_email_payload
        return {
            "code": 200,
            "data": {
                "country": self.cloud.user_data.country,
                "countrycode": self.cloud.user_data.countrycode,
                "url": f"https://{self.cloud.user_data.region}iot.roborock.com",
            },
            "msg": "success",
        }

    def get_login_payload(self) -> dict[str, Any]:
        """Synthesize login payload using the cloud user profile state."""
        if self.login_payload is not None:
            return self.login_payload
        return {
            "code": 200,
            "data": self.cloud.user_data.as_dict(),
            "msg": "success",
        }

    def get_home_detail_payload(self) -> dict[str, Any]:
        """Synthesize getHomeDetail payload using the cloud home state."""
        if self.home_detail_payload is not None:
            return self.home_detail_payload
        return {
            "code": 200,
            "data": {
                "deviceListOrder": None,
                "id": self.cloud.home_id,
                "name": self.cloud.home_name,
                "rrHomeId": self.cloud.home_id,
                "tuyaHomeId": 0,
            },
            "msg": "success",
        }

    def mock_requests(self, mocked: aioresponses) -> None:
        """Register EAPI endpoint mocks with aioresponses."""
        # getUrlByEmail Endpoint Mocking
        mocked.post(
            re.compile(rf"{IOT_API_BASE_URL}/getUrlByEmail.*"),
            status=self.url_by_email_status,
            payload=self.get_url_by_email_payload(),
        )

        # User Logins Endpoint Mocking
        mocked.post(
            re.compile(rf"{IOT_API_BASE_URL}/login.*"),
            status=self.login_status,
            payload=self.get_login_payload(),
        )
        mocked.post(
            re.compile(rf"{IOT_API_BASE_URL}/loginWithCode.*"),
            status=self.login_status,
            payload=self.get_login_payload(),
        )

        # getHomeDetail Endpoint Mocking
        mocked.get(
            re.compile(rf"{IOT_API_BASE_URL}/getHomeDetail.*"),
            status=self.home_detail_status,
            payload=self.get_home_detail_payload(),
        )

        # Dynamic homes response callback wrapper
        def get_homes_callback(url, **kwargs):
            if self.homes_status != 200 or self.homes_payload_override is not None:
                return CallbackResult(
                    status=self.homes_status,
                    payload=self.homes_payload_override,
                )

            devices = []
            products = []
            for server in self.cloud.simulated_devices.values():
                devices.append(server.device_info)
                products.append(server.product)

            home_data = HomeData(
                id=self.cloud.home_id,
                name=self.cloud.home_name,
                devices=devices,
                products=products,
            )
            return CallbackResult(
                status=200,
                payload={
                    "api": None,
                    "code": 200,
                    "result": home_data.as_dict(),
                    "status": "ok",
                    "success": True,
                },
            )

        # getHomeDetail v2 & v3 callbacks routing
        mocked.get(
            re.compile(rf"{REST_API_BASE_URL}/v2/user/homes/{self.cloud.home_id}"),
            callback=get_homes_callback,
        )
        mocked.get(
            re.compile(rf"{REST_API_BASE_URL}/v3/user/homes/{self.cloud.home_id}"),
            callback=get_homes_callback,
        )


class FakeRoborockCloud:
    """A central state object representing the Roborock Cloud environment under test."""

    def __init__(
        self,
        user_data: UserData | None = None,
        home_id: int = 123456,
        home_name: str = "Fake Home",
    ) -> None:
        self.simulated_devices: dict[str, RoborockDeviceSimulator] = {}
        self.user_data = user_data or DEFAULT_USER_DATA
        self.home_id = home_id
        self.home_name = home_name
        self.web_api = FakeWebApiClient(self)

    def add_device(self, server: RoborockDeviceSimulator) -> None:
        """Register a stateful device simulator in the cloud registry."""
        self.simulated_devices[server.duid] = server

    @contextlib.contextmanager
    def patch_device_manager(self):
        """Context manager to patch create_v1_channel and create_mqtt_channel.

        This automatically routes communications to the registered device simulators
        and intercepts HTTP calls at the network boundary using aioresponses.
        """

        # Wrapper function for create_v1_channel
        def mock_create_v1_channel(user_data, mqtt_params, mqtt_session, device, device_cache):
            if device.pv in ("A01", "B01"):
                raise NotImplementedError(
                    f"Simulating protocol {device.pv} is not yet supported. "
                    "TODO: Implement stateful simulators for B01 (Q7/Q10) and A01 (Zeo/Dyad) devices."
                )
            server = self.simulated_devices.get(device.duid)
            if server is not None:
                if not isinstance(server, V1VacuumSimulator):
                    raise TypeError(
                        f"Device '{device.duid}' is registered with a {type(server).__name__} "
                        f"simulator, but create_v1_channel requires a V1VacuumSimulator."
                    )
                return server.v1_channel
            return original_create_v1_channel(user_data, mqtt_params, mqtt_session, device, device_cache)

        # Wrapper function for create_mqtt_channel
        def mock_create_mqtt_channel(user_data, mqtt_params, mqtt_session, device):
            if device.pv in ("A01", "B01"):
                raise NotImplementedError(
                    f"Simulating protocol {device.pv} is not yet supported. "
                    "TODO: Implement stateful simulators for B01 (Q7/Q10) and A01 (Zeo/Dyad) devices."
                )
            server = self.simulated_devices.get(device.duid)
            if server:
                return server.mqtt_channel
            return original_create_mqtt_channel(user_data, mqtt_params, mqtt_session, device)

        # Route Web requests using the dynamic FakeWebApiClient
        with aioresponses() as mocked:
            self.web_api.mock_requests(mocked)

            # Patch Channel factories and rate limiters
            with (
                patch(
                    "roborock.web_api.RoborockApiClient._login_limiter.try_acquire_async",
                    new=AsyncMock(return_value=True),
                ),
                patch("roborock.web_api.RoborockApiClient._home_data_limiter.try_acquire", return_value=True),
                patch("roborock.devices.device_manager.create_v1_channel", side_effect=mock_create_v1_channel),
                patch("roborock.devices.device_manager.create_mqtt_channel", side_effect=mock_create_mqtt_channel),
            ):
                yield

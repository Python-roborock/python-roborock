"""Device pairing and device-record endpoints (``/nc/prepare``, ``/user/devices``)."""

from aiohttp import FormData

from roborock.data import UserData
from roborock.exceptions import RoborockException

from ._base import RoborockApiBase
from ._hawk import _get_hawk_authentication
from ._request import PreparedRequest


class DevicesApi(RoborockApiBase):
    """Adding devices to an account and editing per-device cloud settings."""

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

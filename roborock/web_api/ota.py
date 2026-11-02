"""Firmware / OTA endpoints (``/ota/...`` and the silent-OTA device switch)."""

from roborock.data import FirmwareInfo, UserData
from roborock.exceptions import RoborockException

from ._base import RoborockApiBase


class OtaApi(RoborockApiBase):
    """Firmware update discovery and control."""

    async def get_firmware_info(self, user_data: UserData, device_id: str) -> FirmwareInfo:
        """Get firmware/OTA info for a device (latest version + updatable flag)."""
        path = f"/ota/firmware/{device_id}/updatev2"
        params = {"lang": "en"}
        firmware_request = self._rriot_request(user_data, path, params=params)
        firmware_response = await firmware_request.request("get", path, params=params)
        if not firmware_response or not firmware_response.get("success"):
            raise RoborockException(firmware_response)
        return FirmwareInfo.from_dict(firmware_response.get("result") or {})

    async def start_firmware_update(self, user_data: UserData, device_id: str) -> None:
        """Trigger the (irreversible) firmware update for a device.

        The device downloads and flashes the latest firmware reported by
        :meth:`get_firmware_info`.
        """
        path = f"/ota/device/{device_id}/upgrade"
        upgrade_request = self._rriot_request(user_data, path)
        upgrade_response = await upgrade_request.request("post", path)
        if not upgrade_response or not upgrade_response.get("success"):
            raise RoborockException(upgrade_response)

    async def set_silent_ota(self, user_data: UserData, device_id: str, enabled: bool) -> None:
        """Enable/disable automatic (silent) firmware updates for a device.

        The current value is reported as ``silent_ota_switch`` on the home-data device.
        """
        path = f"/user/devices/{device_id}"
        formdata = {"silentOtaSwitch": "true" if enabled else "false"}
        silent_ota_request = self._rriot_request(user_data, path, formdata=formdata)
        silent_ota_response = await silent_ota_request.request("put", path, data=formdata)
        if not silent_ota_response or not silent_ota_response.get("success"):
            raise RoborockException(silent_ota_response)

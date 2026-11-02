"""Scheduled job / timer endpoints (``/user/devices/{duid}/jobs``)."""

from roborock.data import HomeDataSchedule, UserData
from roborock.exceptions import RoborockException

from ._base import RoborockApiBase
from ._hawk import _compact_json


class JobsApi(RoborockApiBase):
    """Cloud-side cleaning schedules and one-time jobs."""

    async def get_schedules(self, user_data: UserData, device_id: str) -> list[HomeDataSchedule]:
        path = f"/user/devices/{device_id}/jobs"
        schedules_request = self._rriot_request(user_data, path)
        schedules_response = await schedules_request.request("get", path)
        if not schedules_response.get("success"):
            raise RoborockException(schedules_response)
        schedules = schedules_response.get("result")
        if isinstance(schedules, list):
            return [HomeDataSchedule.from_dict(schedule) for schedule in schedules]
        raise RoborockException(f"schedule_response result was an unexpected type: {schedules}")

    async def create_job(self, user_data: UserData, device_id: str, job: dict) -> dict:
        """Create a /jobs entry (schedule or one-time room clean) on a B01 device.

        Body-bearing writes must sign the request body in the Hawk payload slot and send those same
        compact bytes via ``data=``; ``json=`` would re-serialize with spaces and break the MAC.
        """
        path = f"/user/devices/{device_id}/jobs"
        job_request = self._rriot_request(user_data, path, body=job, extra_headers={"Content-Type": "application/json"})
        response = await job_request.request("post", path, data=_compact_json(job).encode())
        if not response.get("success"):
            raise RoborockException(response)
        return response

    async def update_job(self, user_data: UserData, device_id: str, job: HomeDataSchedule) -> None:
        """Replace an existing cloud job with the full supplied schedule.

        Pass a schedule returned by :meth:`get_schedules` with the desired changes.
        The job ID identifies the URL; all other fields are sent as the replacement body.
        """
        path = f"/user/devices/{device_id}/jobs/{job.id}"
        body = job.as_dict(exclude={"id"})
        job_request = self._rriot_request(
            user_data, path, body=body, extra_headers={"Content-Type": "application/json"}
        )
        response = await job_request.request("put", path, data=_compact_json(body).encode())
        if not response or not response.get("success"):
            raise RoborockException(response)

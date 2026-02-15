"""Example script demonstrating how to connect to Roborock devices and print their status."""

import asyncio
import dataclasses
import json
import pathlib
from typing import Any

from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.devices.file_cache import FileCache, load_value, store_value
from roborock.web_api import RoborockApiClient

# We typically store the login credentials/information separately from other cached data.
USER_PARAMS_PATH = pathlib.Path.home() / ".cache" / "roborock-user-params.pkl"

# Device connection information is cached to speed up future connections.
CACHE_PATH = pathlib.Path.home() / ".cache" / "roborock-cache-data.pkl"


async def login_flow() -> UserParams:
    """Perform the login flow to obtain UserData from the web API."""
    username = input("Email: ")
    web_api = RoborockApiClient(username=username)
    print("Requesting login code sent to email...")
    await web_api.request_code()
    code = input("Code: ")
    user_data = await web_api.code_login(code)
    # We store the base_url to avoid future discovery calls.
    base_url = await web_api.base_url
    return UserParams(
        username=username,
        user_data=user_data,
        base_url=base_url,
    )


async def get_or_create_session() -> UserParams:
    """Initialize the session by logging in if necessary."""
    user_params = await load_value(USER_PARAMS_PATH)
    if user_params is None:
        print("No cached login data found, please login.")
        user_params = await login_flow()
        print("Login successful, caching login data...")
        await store_value(USER_PARAMS_PATH, user_params)
        print(f"Cached login data to {USER_PARAMS_PATH}.")
    return user_params


def remove_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


async def main():
    user_params = await get_or_create_session()
    cache = FileCache(CACHE_PATH)

    # Create a device manager that can discover devices.
    device_manager = await create_device_manager(user_params, cache=cache)

    try:
        devices = await device_manager.get_devices()

        # Get all vacuum devices that support the v1 PropertiesApi
        device_results = []
        for device in devices:
            if not device.v1_properties:
                continue

            # Refresh the current device status
            status_trait = device.v1_properties.status
            await status_trait.refresh()

            # Print the device status as JSON
            device_results.append(
                {
                    "device": device.name,
                    "status": remove_none_values(dataclasses.asdict(status_trait)),
                }
            )

        print(json.dumps(device_results, indent=2))

    finally:
        # Close device manager to cancel background tasks before flushing cache
        await device_manager.close()
        await cache.flush()


if __name__ == "__main__":
    asyncio.run(main())

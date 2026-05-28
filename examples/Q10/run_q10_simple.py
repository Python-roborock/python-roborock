#!/usr/bin/env python3
"""Simple test script for Q10 VacuumTrait functionality."""

import asyncio
import pathlib

from roborock.devices.device_manager import UserParams, create_device_manager
from roborock.devices.file_cache import FileCache, load_value, store_value
from roborock.web_api import RoborockApiClient

# Cache paths
USER_PARAMS_PATH = pathlib.Path.home() / ".cache" / "roborock-user-params.pkl"
CACHE_PATH = pathlib.Path.home() / ".cache" / "roborock-cache-data.pkl"


async def login_flow() -> UserParams:
    """Perform the login flow to obtain UserData from the web API."""
    username = input("📧 Email: ")
    web_api = RoborockApiClient(username=username)
    print("📨 Requesting login code sent to email...")
    await web_api.request_code()
    code = input("🔑 Code: ")
    user_data = await web_api.code_login(code)
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
        print("✅ Login successful, caching login data...")
        await store_value(USER_PARAMS_PATH, user_params)
    return user_params


async def main():
    """Test Q10 vacuum commands."""
    print("🔄 Initializing...")

    try:
        user_params = await get_or_create_session()
        cache = FileCache(CACHE_PATH)

        print("🔄 Creating device manager...")
        device_manager = await create_device_manager(user_params, cache=cache)

        print("🔄 Getting devices...")
        devices = await device_manager.get_devices()

        print(f"\n📱 Found {len(devices)} device(s)")

        # List all devices with their properties
        for idx, device in enumerate(devices, 1):
            print(f"\n  Device {idx}: {device.name}")
            print(f"    Product: {device.product.name} ({device.product.model})")
            print(f"    Has v1_properties: {device.v1_properties is not None}")
            print(f"    Has b01_q10_properties: {device.b01_q10_properties is not None}")

            # Check what attributes the device has
            attrs = [attr for attr in dir(device) if not attr.startswith("_") and "properties" in attr.lower()]
            print(f"    Available property APIs: {attrs}")

        # Select device
        if len(devices) == 1:
            device = devices[0]
            print(f"\n✅ Using device: {device.name}")
        else:
            device_idx = int(input("\nSelect device number: ")) - 1
            device = devices[device_idx]
            print(f"\n✅ Selected device: {device.name}")

        # Check if it's a Q10 device
        if device.b01_q10_properties is None:
            print("\n❌ This device doesn't have Q10 properties")
            print(f"   Product: {device.product.name} ({device.product.model})")
            print("\n💡 Available properties:")
            if device.v1_properties:
                print("   - v1_properties (V1 API)")
            if hasattr(device, "b01_q7_properties") and device.b01_q7_properties:
                print("   - b01_q7_properties (Q7 API)")
            await cache.flush()
            return

        print("\n✅ Device has Q10 properties!")

        # Check if vacuum trait exists
        if not hasattr(device.b01_q10_properties, "vacuum"):
            print("\n❌ Q10 properties don't have 'vacuum' trait")
            print(
                f"   Available traits: {[attr for attr in dir(device.b01_q10_properties) if not attr.startswith('_')]}"
            )
            await cache.flush()
            return

        vacuum = device.b01_q10_properties.vacuum
        print(f"✅ Vacuum trait found: {vacuum}")

        print("\n🤖 Q10 Vacuum Trait Test Menu")
        print("=" * 50)
        print("1. Start cleaning")
        print("2. Pause cleaning")
        print("3. Resume cleaning")
        print("4. Stop cleaning")
        print("5. Return to dock")
        print("0. Exit")
        print("=" * 50)

        while True:
            try:
                choice = input("\nEnter your choice (0-5): ").strip()

                if choice == "0":
                    print("👋 Exiting...")
                    break
                elif choice == "1":
                    print("▶️  Starting cleaning...")
                    await vacuum.start_clean()
                    print("✅ Start cleaning command sent!")
                elif choice == "2":
                    print("⏸️  Pausing cleaning...")
                    await vacuum.pause_clean()
                    print("✅ Pause command sent!")
                elif choice == "3":
                    print("▶️  Resuming cleaning...")
                    await vacuum.resume_clean()
                    print("✅ Resume command sent!")
                elif choice == "4":
                    print("⏹️  Stopping cleaning...")
                    await vacuum.stop_clean()
                    print("✅ Stop command sent!")
                elif choice == "5":
                    print("🏠 Returning to dock...")
                    await vacuum.return_to_dock()
                    print("✅ Return to dock command sent!")
                else:
                    print("❌ Invalid choice, please try again")
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback

                traceback.print_exc()

        await cache.flush()

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

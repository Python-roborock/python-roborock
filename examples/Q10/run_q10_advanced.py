#!/usr/bin/env python3
"""Advanced test script for Q10 VacuumTrait with complex features."""

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


async def test_basic_commands(vacuum):
    """Test basic vacuum commands."""
    print("\n" + "=" * 50)
    print("🧪 TESTING BASIC COMMANDS")
    print("=" * 50)

    commands = [
        ("Start cleaning", vacuum.start_clean),
        ("Pause cleaning", vacuum.pause_clean),
        ("Resume cleaning", vacuum.resume_clean),
        ("Stop cleaning", vacuum.stop_clean),
        ("Return to dock", vacuum.return_to_dock),
    ]

    for idx, (name, cmd) in enumerate(commands, 1):
        try:
            print(f"\n{idx}. Testing: {name}")
            await cmd()
            print("   ✅ Command sent successfully!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()


async def test_advanced_features(vacuum):
    """Test advanced cleaning features (based on code comments)."""
    print("\n" + "=" * 50)
    print("🚀 TESTING ADVANCED FEATURES")
    print("=" * 50)

    from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP

    # Test different cleaning modes
    print("\n1. Testing different cleaning modes...")

    modes = [
        ("Standard cleaning (cmd=1)", 1),
        ("Electoral/Area cleaning (cmd=2)", 2),
        ("Fast map creation (cmd=4)", 4),
    ]

    for mode_name, cmd_value in modes:
        try:
            # Ask for confirmation for map creation mode
            if cmd_value == 4:
                print(f"\n   ⚠️  {mode_name}")
                print("   ⚠️  WARNING: This will start the map creation process!")
                print("   ⚠️  The robot will start moving to map your home.")
                confirm = input("   Are you sure you want to proceed? (yes/no): ").strip().lower()
                if confirm != "yes":
                    print("   ⏭️  Skipped!")
                    continue

            print(f"\n   • {mode_name}")
            await vacuum._command.send(
                command=B01_Q10_DP.START_CLEAN,
                params={"cmd": cmd_value},
            )
            print("     ✅ Sent!")
        except Exception as e:
            print(f"     ❌ Error: {e}")


async def test_device_status(device):
    """Test device status monitoring."""
    print("\n" + "=" * 50)
    print("📊 CHECKING DEVICE STATUS")
    print("=" * 50)

    try:
        # Check if device has properties for status
        print(f"\nDevice: {device.name}")
        print(f"Product: {device.product.name} ({device.product.model})")
        print(f"Connected: {device.is_connected}")
        print(f"Local connected: {device.is_local_connected}")

        # Try to get status if available
        if device.v1_properties and device.v1_properties.status:
            print("\n🔍 V1 Status available")
            try:
                await device.v1_properties.status.refresh()
                status = device.v1_properties.status
                print(f"   Status: {status}")
            except Exception as e:
                print(f"   Could not refresh status: {e}")

        # Check Q10 properties
        if device.b01_q10_properties:
            print("\n✅ Q10 Properties available")
            print(f"   Command API: {device.b01_q10_properties.command}")
            print(f"   Vacuum Trait: {device.b01_q10_properties.vacuum}")

    except Exception as e:
        print(f"❌ Error checking device status: {e}")
        import traceback

        traceback.print_exc()


async def interactive_menu(vacuum):
    """Interactive menu for manual testing."""
    print("\n" + "=" * 50)
    print("🎮 INTERACTIVE TEST MENU")
    print("=" * 50)
    print("\n1. Start cleaning")
    print("2. Pause cleaning")
    print("3. Resume cleaning")
    print("4. Stop cleaning")
    print("5. Return to dock")
    print("6. Test all modes")
    print("0. Exit")
    print("=" * 50)

    while True:
        try:
            choice = input("\nEnter your choice (0-6): ").strip()

            if choice == "0":
                print("👋 Exiting...")
                break
            elif choice == "1":
                print("▶️  Starting cleaning...")
                await vacuum.start_clean()
                print("✅ Command sent!")
            elif choice == "2":
                print("⏸️  Pausing cleaning...")
                await vacuum.pause_clean()
                print("✅ Command sent!")
            elif choice == "3":
                print("▶️  Resuming cleaning...")
                await vacuum.resume_clean()
                print("✅ Command sent!")
            elif choice == "4":
                print("⏹️  Stopping cleaning...")
                await vacuum.stop_clean()
                print("✅ Command sent!")
            elif choice == "5":
                print("🏠 Returning to dock...")
                await vacuum.return_to_dock()
                print("✅ Command sent!")
            elif choice == "6":
                await test_advanced_features(vacuum)
            else:
                print("❌ Invalid choice")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main test function."""
    try:
        user_params = await get_or_create_session()
        cache = FileCache(CACHE_PATH)

        print("\n🔄 Connecting to devices...")
        device_manager = await create_device_manager(user_params, cache=cache)
        devices = await device_manager.get_devices()

        print(f"\n📱 Found {len(devices)} device(s)")
        for idx, device in enumerate(devices, 1):
            print(f"  {idx}. {device.name} ({device.product.model})")

        # Select device
        if len(devices) == 1:
            device = devices[0]
            print(f"\n✅ Using device: {device.name}")
        else:
            device_idx = int(input("\nSelect device number: ")) - 1
            device = devices[device_idx]
            print(f"\n✅ Selected device: {device.name}")

        # Check Q10 properties
        if device.b01_q10_properties is None:
            print("\n❌ This device doesn't have Q10 properties")
            await cache.flush()
            return

        vacuum = device.b01_q10_properties.vacuum

        # Show main menu
        print("\n" + "=" * 50)
        print("Q10 ADVANCED TEST SUITE")
        print("=" * 50)
        print("\n1. Run basic commands test")
        print("2. Test advanced features")
        print("3. Check device status")
        print("4. Interactive menu")
        print("5. Run all tests")
        print("0. Exit")
        print("=" * 50)

        while True:
            try:
                choice = input("\nSelect test (0-5): ").strip()

                if choice == "0":
                    break
                elif choice == "1":
                    await test_basic_commands(vacuum)
                elif choice == "2":
                    await test_advanced_features(vacuum)
                elif choice == "3":
                    await test_device_status(device)
                elif choice == "4":
                    await interactive_menu(vacuum)
                elif choice == "5":
                    await test_device_status(device)
                    await test_basic_commands(vacuum)
                    await test_advanced_features(vacuum)
                else:
                    print("❌ Invalid choice")
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

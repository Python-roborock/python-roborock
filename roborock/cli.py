"""Command line interface for python-roborock.

The CLI supports both one-off commands and an interactive session mode. In session
mode, an asyncio event loop is created in a separate thread, allowing users to
interactively run commands that require async operations.

Typical CLI usage:
```
$ roborock login --email <email> [--password <password>]
$ roborock discover
$ roborock list-devices
$ roborock status --device_id <device_id>
```
...

Session mode usage:
```
$ roborock session
roborock> list-devices
...
roborock> status --device_id <device_id>
```
"""

import asyncio
import datetime
import functools
import json
import logging
import sys
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import click
import click_shell
import yaml
from pyshark import FileCapture  # type: ignore
from pyshark.capture.live_capture import LiveCapture, UnknownInterfaceException  # type: ignore
from pyshark.packet.packet import Packet  # type: ignore

from roborock import RoborockCommand
from roborock.data import RoborockBase, UserData
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.code_mappings import SHORT_MODEL_TO_ENUM, RoborockProductNickname
from roborock.device_features import DeviceFeatures
from roborock.devices.cache import Cache, CacheData
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import DeviceManager, UserParams, create_device_manager
from roborock.devices.traits import Trait
from roborock.devices.traits.v1 import V1TraitMixin
from roborock.devices.traits.v1.consumeable import ConsumableAttribute
from roborock.devices.traits.v1.map_content import MapContentTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.protocol import MessageParser
from roborock.web_api import RoborockApiClient

_LOGGER = logging.getLogger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def dump_json(obj: Any) -> Any:
    """Dump an object as JSON."""

    def custom_json_serializer(obj):
        if isinstance(obj, datetime.time):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    return json.dumps(obj, default=custom_json_serializer)


def async_command(func):
    """Decorator for async commands that work in both CLI and session modes.

    The CLI supports two execution modes:
    1. CLI mode: One-off commands that create their own event loop
    2. Session mode: Interactive shell with a persistent background event loop

    This decorator ensures async commands work correctly in both modes:
    - CLI mode: Uses asyncio.run() to create a new event loop
    - Session mode: Uses the existing session event loop via run_in_session()
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = args[0]
        context: RoborockContext = ctx.obj

        async def run():
            try:
                await func(*args, **kwargs)
            except Exception as err:
                _LOGGER.exception("Uncaught exception in command")
                click.echo(f"Error: {err}", err=True)
            finally:
                if not context.is_session_mode():
                    await context.cleanup()

        if context.is_session_mode():
            # Session mode - run in the persistent loop
            return context.run_in_session(run())
        else:
            # CLI mode - just run normally (asyncio.run handles loop creation)
            return asyncio.run(run())

    return wrapper


@dataclass
class ConnectionCache(RoborockBase):
    """Cache for Roborock data.

    This is used to store data retrieved from the Roborock API, such as user
    data and home data to avoid repeated API calls.

    This cache is superset of `LoginData` since we used to directly store that
    dataclass, but now we also store additional data.
    """

    user_data: UserData
    email: str
    # TODO: Used new APIs for cache file storage
    cache_data: CacheData | None = None


class DeviceConnectionManager:
    """Manages device connections for both CLI and session modes."""

    def __init__(self, context: "RoborockContext", loop: asyncio.AbstractEventLoop | None = None):
        self.context = context
        self.loop = loop
        self.device_manager: DeviceManager | None = None
        self._devices: dict[str, RoborockDevice] = {}

    async def ensure_device_manager(self) -> DeviceManager:
        """Ensure device manager is initialized."""
        if self.device_manager is None:
            connection_cache = self.context.connection_cache()
            user_params = UserParams(
                username=connection_cache.email,
                user_data=connection_cache.user_data,
            )
            self.device_manager = await create_device_manager(user_params, cache=self.context)
            # Cache devices for quick lookup
            devices = await self.device_manager.get_devices()
            self._devices = {device.duid: device for device in devices}
        return self.device_manager

    async def get_device(self, device_id: str) -> RoborockDevice:
        """Get a device by ID, creating connections if needed."""
        await self.ensure_device_manager()
        if device_id not in self._devices:
            raise RoborockException(f"Device {device_id} not found")
        return self._devices[device_id]

    async def close(self):
        """Close device manager connections."""
        if self.device_manager:
            await self.device_manager.close()
            self.device_manager = None
            self._devices = {}


class RoborockContext(Cache):
    """Context that handles both CLI and session modes internally."""

    roborock_file = Path("~/.roborock").expanduser()
    roborock_cache_file = Path("~/.roborock.cache").expanduser()
    _connection_cache: ConnectionCache | None = None

    def __init__(self):
        self.reload()
        self._session_loop: asyncio.AbstractEventLoop | None = None
        self._session_thread: threading.Thread | None = None
        self._device_manager: DeviceConnectionManager | None = None

    def reload(self):
        if self.roborock_file.is_file():
            with open(self.roborock_file) as f:
                data = json.load(f)
                if data:
                    self._connection_cache = ConnectionCache.from_dict(data)

    def update(self, connection_cache: ConnectionCache):
        data = json.dumps(connection_cache.as_dict(), default=vars, indent=4)
        with open(self.roborock_file, "w") as f:
            f.write(data)
        self.reload()

    def validate(self):
        if self._connection_cache is None:
            raise RoborockException("You must login first")

    def connection_cache(self) -> ConnectionCache:
        """Get the cache data."""
        self.validate()
        return cast(ConnectionCache, self._connection_cache)

    def start_session_mode(self):
        """Start session mode with a background event loop."""
        if self._session_loop is not None:
            return  # Already started

        self._session_loop = asyncio.new_event_loop()
        self._session_thread = threading.Thread(target=self._run_session_loop)
        self._session_thread.daemon = True
        self._session_thread.start()

    def _run_session_loop(self):
        """Run the session event loop in a background thread."""
        assert self._session_loop is not None  # guaranteed by start_session_mode
        asyncio.set_event_loop(self._session_loop)
        self._session_loop.run_forever()

    def is_session_mode(self) -> bool:
        return self._session_loop is not None

    def run_in_session(self, coro):
        """Run a coroutine in the session loop (session mode only)."""
        if not self._session_loop:
            raise RoborockException("Not in session mode")
        future = asyncio.run_coroutine_threadsafe(coro, self._session_loop)
        return future.result()

    async def get_device_manager(self) -> DeviceConnectionManager:
        """Get device manager, creating if needed."""
        await self.get_devices()
        if self._device_manager is None:
            self._device_manager = DeviceConnectionManager(self, self._session_loop)
        return self._device_manager

    async def refresh_devices(self) -> ConnectionCache:
        """Refresh device data from server (always fetches fresh data)."""
        connection_cache = self.connection_cache()
        client = RoborockApiClient(connection_cache.email)
        home_data = await client.get_home_data_v3(connection_cache.user_data)
        if connection_cache.cache_data is None:
            connection_cache.cache_data = CacheData()
        connection_cache.cache_data.home_data = home_data
        self.update(connection_cache)
        return connection_cache

    async def get_devices(self) -> ConnectionCache:
        """Get device data (uses cache if available, fetches if needed)."""
        connection_cache = self.connection_cache()
        if (connection_cache.cache_data is None) or (connection_cache.cache_data.home_data is None):
            connection_cache = await self.refresh_devices()
        return connection_cache

    async def cleanup(self):
        """Clean up resources (mainly for session mode)."""
        if self._device_manager:
            await self._device_manager.close()
            self._device_manager = None

        # Stop session loop if running
        if self._session_loop:
            self._session_loop.call_soon_threadsafe(self._session_loop.stop)
            if self._session_thread:
                self._session_thread.join(timeout=5.0)
            self._session_loop = None
            self._session_thread = None

    def finish_session(self) -> None:
        """Finish the session and clean up resources."""
        if self._session_loop:
            future = asyncio.run_coroutine_threadsafe(self.cleanup(), self._session_loop)
            future.result(timeout=5.0)

    async def get(self) -> CacheData:
        """Get cached value."""
        _LOGGER.debug("Getting cache data")
        connection_cache = self.connection_cache()
        if connection_cache.cache_data is not None:
            return connection_cache.cache_data
        return CacheData()

    async def set(self, value: CacheData) -> None:
        """Set value in the cache."""
        _LOGGER.debug("Setting cache data")
        connection_cache = self.connection_cache()
        connection_cache.cache_data = value
        self.update(connection_cache)


@click.option("-d", "--debug", default=False, count=True)
@click.version_option(package_name="python-roborock")
@click.group()
@click.pass_context
def cli(ctx, debug: int):
    logging_config: dict[str, Any] = {"level": logging.DEBUG if debug > 0 else logging.INFO}
    logging.basicConfig(**logging_config)  # type: ignore
    ctx.obj = RoborockContext()


@click.command()
@click.option("--email", required=True)
@click.option(
    "--reauth",
    is_flag=True,
    default=False,
    help="Re-authenticate even if cached credentials exist.",
)
@click.option(
    "--password",
    required=False,
    help="Password for the Roborock account. If not provided, an email code will be requested.",
)
@click.pass_context
@async_command
async def login(ctx, email, password, reauth):
    """Login to Roborock account."""
    context: RoborockContext = ctx.obj
    if not reauth:
        try:
            context.validate()
            _LOGGER.info("Already logged in")
            return
        except RoborockException:
            pass
    client = RoborockApiClient(email)
    if password is not None:
        user_data = await client.pass_login(password)
    else:
        print(f"Requesting code for {email}")
        await client.request_code()
        code = click.prompt("A code has been sent to your email, please enter the code", type=str)
        user_data = await client.code_login(code)
        print("Login successful")
    context.update(ConnectionCache(user_data=user_data, email=email))


def _shell_session_finished(ctx):
    """Callback for when shell session finishes."""
    context: RoborockContext = ctx.obj
    try:
        context.finish_session()
    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
    click.echo("Session finished")


@click_shell.shell(
    prompt="roborock> ",
    on_finished=_shell_session_finished,
)
@click.pass_context
def session(ctx):
    """Start an interactive session."""
    context: RoborockContext = ctx.obj
    # Start session mode with background loop
    context.start_session_mode()
    context.run_in_session(context.get_device_manager())
    click.echo("OK")


@session.command()
@click.pass_context
@async_command
async def discover(ctx):
    """Discover devices."""
    context: RoborockContext = ctx.obj
    # Use the explicit refresh method for the discover command
    connection_cache = await context.refresh_devices()

    home_data = connection_cache.cache_data.home_data
    click.echo(f"Discovered devices {', '.join([device.name for device in home_data.get_all_devices()])}")


@session.command()
@click.pass_context
@async_command
async def list_devices(ctx):
    context: RoborockContext = ctx.obj
    connection_cache = await context.get_devices()

    home_data = connection_cache.cache_data.home_data

    device_name_id = {device.name: device.duid for device in home_data.get_all_devices()}
    click.echo(json.dumps(device_name_id, indent=4))


@click.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def list_scenes(ctx, device_id):
    context: RoborockContext = ctx.obj
    connection_cache = await context.get_devices()

    client = RoborockApiClient(connection_cache.email)
    scenes = await client.get_scenes(connection_cache.user_data, device_id)
    output_list = []
    for scene in scenes:
        output_list.append(scene.as_dict())
    click.echo(json.dumps(output_list, indent=4))


@click.command()
@click.option("--scene_id", required=True)
@click.pass_context
@async_command
async def execute_scene(ctx, scene_id):
    context: RoborockContext = ctx.obj
    connection_cache = await context.get_devices()

    client = RoborockApiClient(connection_cache.email)
    await client.execute_scene(connection_cache.user_data, scene_id)


async def _v1_trait(context: RoborockContext, device_id: str, display_func: Callable[[], V1TraitMixin]) -> Trait:
    device_manager = await context.get_device_manager()
    device = await device_manager.get_device(device_id)
    if device.v1_properties is None:
        raise RoborockUnsupportedFeature(f"Device {device.name} does not support V1 protocol")
    await device.v1_properties.discover_features()
    trait = display_func(device.v1_properties)
    if trait is None:
        raise RoborockUnsupportedFeature("Trait not supported by device")
    await trait.refresh()
    return trait


async def _display_v1_trait(context: RoborockContext, device_id: str, display_func: Callable[[], Trait]) -> None:
    try:
        trait = await _v1_trait(context, device_id, display_func)
    except RoborockUnsupportedFeature:
        click.echo("Feature not supported by device")
        return
    except RoborockException as e:
        click.echo(f"Error: {e}")
        return
    click.echo(dump_json(trait.as_dict()))


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def status(ctx, device_id: str):
    """Get device status."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.status)


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def clean_summary(ctx, device_id: str):
    """Get device clean summary."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.clean_summary)


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def clean_record(ctx, device_id: str):
    """Get device last clean record."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.clean_record)


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def dock_summary(ctx, device_id: str):
    """Get device dock summary."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.dock_summary)


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def volume(ctx, device_id: str):
    """Get device volume."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.sound_volume)


@session.command()
@click.option("--device_id", required=True)
@click.option("--volume", required=True, type=int)
@click.pass_context
@async_command
async def set_volume(ctx, device_id: str, volume: int):
    """Set the devicevolume."""
    context: RoborockContext = ctx.obj
    volume_trait = await _v1_trait(context, device_id, lambda v1: v1.sound_volume)
    await volume_trait.set_volume(volume)
    click.echo(f"Set Device {device_id} volume to {volume}")


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def maps(ctx, device_id: str):
    """Get device maps info."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.maps)


@session.command()
@click.option("--device_id", required=True)
@click.option("--output-file", required=True, help="Path to save the map image.")
@click.pass_context
@async_command
async def map_image(ctx, device_id: str, output_file: str):
    """Get device map image and save it to a file."""
    context: RoborockContext = ctx.obj
    trait: MapContentTrait = await _v1_trait(context, device_id, lambda v1: v1.map_content)
    if trait.image_content:
        with open(output_file, "wb") as f:
            f.write(trait.image_content)
        click.echo(f"Map image saved to {output_file}")
    else:
        click.echo("No map image content available.")


@session.command()
@click.option("--device_id", required=True)
@click.option("--include_path", is_flag=True, default=False, help="Include path data in the output.")
@click.pass_context
@async_command
async def map_data(ctx, device_id: str, include_path: bool):
    """Get parsed map data as JSON."""
    context: RoborockContext = ctx.obj
    trait: MapContentTrait = await _v1_trait(context, device_id, lambda v1: v1.map_content)
    if not trait.map_data:
        click.echo("No parsed map data available.")
        return

    # Pick some parts of the map data to display.
    data_summary = {
        "charger": trait.map_data.charger.as_dict() if trait.map_data.charger else None,
        "image_size": trait.map_data.image.data.size if trait.map_data.image else None,
        "vacuum_position": trait.map_data.vacuum_position.as_dict() if trait.map_data.vacuum_position else None,
        "calibration": trait.map_data.calibration(),
        "zones": [z.as_dict() for z in trait.map_data.zones or ()],
    }
    if include_path and trait.map_data.path:
        data_summary["path"] = trait.map_data.path.as_dict()
    click.echo(dump_json(data_summary))


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def consumables(ctx, device_id: str):
    """Get device consumables."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.consumables)


@session.command()
@click.option("--device_id", required=True)
@click.option("--consumable", required=True, type=click.Choice([e.value for e in ConsumableAttribute]))
@click.pass_context
@async_command
async def reset_consumable(ctx, device_id: str, consumable: str):
    """Reset a specific consumable attribute."""
    context: RoborockContext = ctx.obj
    trait = await _v1_trait(context, device_id, lambda v1: v1.consumables)
    attribute = ConsumableAttribute.from_str(consumable)
    await trait.reset_consumable(attribute)
    click.echo(f"Reset {consumable} for device {device_id}")


@session.command()
@click.option("--device_id", required=True)
@click.option("--enabled", type=bool, help="Enable (True) or disable (False) the child lock.")
@click.pass_context
@async_command
async def child_lock(ctx, device_id: str, enabled: bool | None):
    """Get device child lock status."""
    context: RoborockContext = ctx.obj
    try:
        trait = await _v1_trait(context, device_id, lambda v1: v1.child_lock)
    except RoborockUnsupportedFeature:
        click.echo("Feature not supported by device")
        return
    if enabled is not None:
        if enabled:
            await trait.enable()
        else:
            await trait.disable()
        click.echo(f"Set child lock to {enabled} for device {device_id}")
        await trait.refresh()

    click.echo(dump_json(trait.as_dict()))


@session.command()
@click.option("--device_id", required=True)
@click.option("--enabled", type=bool, help="Enable (True) or disable (False) the DND status.")
@click.pass_context
@async_command
async def dnd(ctx, device_id: str, enabled: bool | None):
    """Get Do Not Disturb Timer status."""
    context: RoborockContext = ctx.obj
    try:
        trait = await _v1_trait(context, device_id, lambda v1: v1.dnd)
    except RoborockUnsupportedFeature:
        click.echo("Feature not supported by device")
        return
    if enabled is not None:
        if enabled:
            await trait.enable()
        else:
            await trait.disable()
        click.echo(f"Set DND to {enabled} for device {device_id}")
        await trait.refresh()

    click.echo(dump_json(trait.as_dict()))


@session.command()
@click.option("--device_id", required=True)
@click.option("--enabled", required=False, type=bool, help="Enable (True) or disable (False) the Flow LED.")
@click.pass_context
@async_command
async def flow_led_status(ctx, device_id: str, enabled: bool | None):
    """Get device Flow LED status."""
    context: RoborockContext = ctx.obj
    try:
        trait = await _v1_trait(context, device_id, lambda v1: v1.flow_led_status)
    except RoborockUnsupportedFeature:
        click.echo("Feature not supported by device")
        return
    if enabled is not None:
        if enabled:
            await trait.enable()
        else:
            await trait.disable()
        click.echo(f"Set Flow LED to {enabled} for device {device_id}")
        await trait.refresh()

    click.echo(dump_json(trait.as_dict()))


@session.command()
@click.option("--device_id", required=True)
@click.option("--enabled", required=False, type=bool, help="Enable (True) or disable (False) the LED.")
@click.pass_context
@async_command
async def led_status(ctx, device_id: str, enabled: bool | None):
    """Get device LED status."""
    context: RoborockContext = ctx.obj
    try:
        trait = await _v1_trait(context, device_id, lambda v1: v1.led_status)
    except RoborockUnsupportedFeature:
        click.echo("Feature not supported by device")
        return
    if enabled is not None:
        if enabled:
            await trait.enable()
        else:
            await trait.disable()
        click.echo(f"Set LED Status to {enabled} for device {device_id}")
        await trait.refresh()

    click.echo(dump_json(trait.as_dict()))


@session.command()
@click.option("--device_id", required=True)
@click.option("--enabled", required=True, type=bool, help="Enable (True) or disable (False) the child lock.")
@click.pass_context
@async_command
async def set_child_lock(ctx, device_id: str, enabled: bool):
    """Set the child lock status."""
    context: RoborockContext = ctx.obj
    trait = await _v1_trait(context, device_id, lambda v1: v1.child_lock)
    await trait.set_child_lock(enabled)
    status = "enabled" if enabled else "disabled"
    click.echo(f"Child lock {status} for device {device_id}")


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def rooms(ctx, device_id: str):
    """Get device room mapping info."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.rooms)


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def features(ctx, device_id: str):
    """Get device room mapping info."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.device_features)


@session.command()
@click.option("--device_id", required=True)
@click.option("--refresh", is_flag=True, default=False, help="Refresh status before discovery.")
@click.pass_context
@async_command
async def home(ctx, device_id: str, refresh: bool):
    """Discover and cache home layout (maps and rooms)."""
    context: RoborockContext = ctx.obj
    device_manager = await context.get_device_manager()
    device = await device_manager.get_device(device_id)
    if device.v1_properties is None:
        raise RoborockException(f"Device {device.name} does not support V1 protocol")

    # Ensure we have the latest status before discovery
    await device.v1_properties.status.refresh()

    home_trait = device.v1_properties.home
    await home_trait.discover_home()
    if refresh:
        await home_trait.refresh()

    # Display the discovered home cache
    if home_trait.home_map_info:
        cache_summary = {
            map_flag: {
                "name": map_data.name,
                "room_count": len(map_data.rooms),
                "rooms": [{"segment_id": room.segment_id, "name": room.name} for room in map_data.rooms],
            }
            for map_flag, map_data in home_trait.home_map_info.items()
        }
        click.echo(dump_json(cache_summary))
    else:
        click.echo("No maps discovered")


@session.command()
@click.option("--device_id", required=True)
@click.pass_context
@async_command
async def network_info(ctx, device_id: str):
    """Get device network information."""
    context: RoborockContext = ctx.obj
    await _display_v1_trait(context, device_id, lambda v1: v1.network_info)


def _parse_b01_q10_command(cmd: str) -> B01_Q10_DP:
    """Parse B01_Q10 command from either enum name or value."""
    try:
        return B01_Q10_DP(int(cmd))
    except ValueError:
        try:
            return B01_Q10_DP.from_name(cmd)
        except ValueError:
            try:
                return B01_Q10_DP.from_value(cmd)
            except ValueError:
                pass
    raise RoborockException(f"Invalid command {cmd} for B01_Q10 device")


@click.command()
@click.option("--device_id", required=True)
@click.option("--cmd", required=True)
@click.option("--params", required=False)
@click.pass_context
@async_command
async def command(ctx, cmd, device_id, params):
    context: RoborockContext = ctx.obj
    device_manager = await context.get_device_manager()
    device = await device_manager.get_device(device_id)
    if device.v1_properties is not None:
        command_trait: Trait = device.v1_properties.command
        result = await command_trait.send(cmd, json.loads(params) if params is not None else None)
        if result:
            click.echo(dump_json(result))
    elif device.b01_q10_properties is not None:
        cmd_value = _parse_b01_q10_command(cmd)
        command_trait: Trait = device.b01_q10_properties.command
        await command_trait.send(cmd_value, json.loads(params) if params is not None else None)
        click.echo("Command sent successfully; Enable debug logging (-d) to see responses.")
        # Q10 commands don't have a specific time to respond, so wait a bit and log
        await asyncio.sleep(5)


@click.command()
@click.option("--local_key", required=True)
@click.option("--device_ip", required=True)
@click.option("--file", required=False)
@click.pass_context
@async_command
async def parser(_, local_key, device_ip, file):
    file_provided = file is not None
    if file_provided:
        capture = FileCapture(file)
    else:
        _LOGGER.info("Listen for interface rvi0 since no file was provided")
        capture = LiveCapture(interface="rvi0")
    buffer = {"data": b""}

    def on_package(packet: Packet):
        if hasattr(packet, "ip"):
            if packet.transport_layer == "TCP" and (packet.ip.dst == device_ip or packet.ip.src == device_ip):
                if hasattr(packet, "DATA"):
                    if hasattr(packet.DATA, "data"):
                        if packet.ip.dst == device_ip:
                            try:
                                f, buffer["data"] = MessageParser.parse(
                                    buffer["data"] + bytes.fromhex(packet.DATA.data),
                                    local_key,
                                )
                                print(f"Received request: {f}")
                            except BaseException as e:
                                print(e)
                                pass
                        elif packet.ip.src == device_ip:
                            try:
                                f, buffer["data"] = MessageParser.parse(
                                    buffer["data"] + bytes.fromhex(packet.DATA.data),
                                    local_key,
                                )
                                print(f"Received response: {f}")
                            except BaseException as e:
                                print(e)
                                pass

    try:
        await capture.packets_from_tshark(on_package, close_tshark=not file_provided)
    except UnknownInterfaceException:
        raise RoborockException(
            "You need to run 'rvictl -s XXXXXXXX-XXXXXXXXXXXXXXXX' first, with an iPhone connected to usb port"
        )


def _parse_diagnostic_file(diagnostic_path: Path) -> dict[str, dict[str, Any]]:
    """Parse device info from a Home Assistant diagnostic file.

    Args:
        diagnostic_path: Path to the diagnostic JSON file.

    Returns:
        A dictionary mapping model names to device info dictionaries.
    """
    with open(diagnostic_path, encoding="utf-8") as f:
        diagnostic_data = json.load(f)

    all_products_data: dict[str, dict[str, Any]] = {}

    # Navigate to coordinators in the diagnostic data
    coordinators = diagnostic_data.get("data", {}).get("coordinators", {})
    if not coordinators:
        return all_products_data

    for coordinator_id, coordinator_data in coordinators.items():
        device_data = coordinator_data.get("device", {})
        product_data = coordinator_data.get("product", {})

        model = product_data.get("model")
        if not model:
            continue

        # Skip duplicate models
        if model in all_products_data:
            continue

        # Derive product nickname from model
        short_model = model.split(".")[-1]
        product_nickname = SHORT_MODEL_TO_ENUM.get(short_model, RoborockProductNickname.PEARLPLUS)

        current_product_data: dict[str, Any] = {
            "Protocol Version": device_data.get("pv"),
            "Product Nickname": product_nickname.name,
        }

        # Get feature info from the device_features trait (preferred location)
        traits_data = coordinator_data.get("traits", {})
        device_features = traits_data.get("device_features", {})

        # newFeatureInfo is the integer
        new_feature_info = device_features.get("newFeatureInfo")
        if new_feature_info is not None:
            current_product_data["New Feature Info"] = new_feature_info

        # newFeatureInfoStr is the hex string
        new_feature_info_str = device_features.get("newFeatureInfoStr")
        if new_feature_info_str:
            current_product_data["New Feature Info Str"] = new_feature_info_str

        # featureInfo is the list of feature codes
        feature_info = device_features.get("featureInfo")
        if feature_info:
            current_product_data["Feature Info"] = feature_info

        # Build product dict from diagnostic product data
        if product_data:
            # Convert to the format expected by device_info.yaml
            product_dict: dict[str, Any] = {}
            for key in ["id", "name", "model", "category", "capability", "schema"]:
                if key in product_data:
                    product_dict[key] = product_data[key]
            if product_dict:
                current_product_data["Product"] = product_dict

        all_products_data[model] = current_product_data

    return all_products_data


@click.command()
@click.option(
    "--record",
    is_flag=True,
    default=False,
    help="Save new device info entries to the YAML file.",
)
@click.option(
    "--device-info-file",
    default="device_info.yaml",
    help="Path to the YAML file with device and product data.",
)
@click.option(
    "--diagnostic-file",
    default=None,
    help="Path to a Home Assistant diagnostic JSON file to parse instead of connecting to devices.",
)
@click.pass_context
@async_command
async def get_device_info(ctx: click.Context, record: bool, device_info_file: str, diagnostic_file: str | None):
    """
    Connects to devices and prints their feature information in YAML format.

    Can also parse device info from a Home Assistant diagnostic file using --diagnostic-file.
    """
    context: RoborockContext = ctx.obj
    device_info_path = Path(device_info_file)
    existing_device_info: dict[str, Any] = {}

    # Load existing device info if recording
    if record:
        click.echo(f"Using device info file: {device_info_path.resolve()}")
        if device_info_path.exists():
            with open(device_info_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                existing_device_info = data

    # Parse from diagnostic file if provided
    if diagnostic_file:
        diagnostic_path = Path(diagnostic_file)
        if not diagnostic_path.exists():
            click.echo(f"Diagnostic file not found: {diagnostic_path}", err=True)
            return

        click.echo(f"Parsing diagnostic file: {diagnostic_path.resolve()}")
        all_products_data = _parse_diagnostic_file(diagnostic_path)

        if not all_products_data:
            click.echo("No device data found in diagnostic file.")
            return

        click.echo(f"Found {len(all_products_data)} device(s) in diagnostic file.")

        # Filter out already recorded models if recording
        if record:
            all_products_data = {
                model: data for model, data in all_products_data.items() if model not in existing_device_info
            }
            if not all_products_data:
                click.echo("No new device info to record (all models already exist).")
                return

    else:
        # Original behavior: connect to devices
        click.echo("Discovering devices...")

        if record:
            connection_cache = await context.get_devices()
            home_data = connection_cache.cache_data.home_data if connection_cache.cache_data else None
            if home_data is None:
                click.echo("Home data not available.", err=True)
                return

        device_connection_manager = await context.get_device_manager()
        device_manager = await device_connection_manager.ensure_device_manager()
        devices = await device_manager.get_devices()
        if not devices:
            click.echo("No devices found.")
            return

        click.echo(f"Found {len(devices)} devices. Fetching data...")

        all_products_data = {}

        for device in devices:
            click.echo(f"  - Processing {device.name} ({device.duid})")

            model = device.product.model
            if record and model in existing_device_info:
                click.echo(f"    - Device info already recorded for {model}")
                continue
            if model in all_products_data:
                click.echo(f"    - Skipping duplicate model {model}")
                continue

            current_product_data = {
                "Protocol Version": device.device_info.pv,
                "Product Nickname": device.product.product_nickname.name,
            }
            if device.v1_properties is not None:
                try:
                    result: list[dict[str, Any]] = await device.v1_properties.command.send(
                        RoborockCommand.APP_GET_INIT_STATUS
                    )
                except Exception as e:
                    click.echo(f"    - Error processing device {device.name}: {e}", err=True)
                    continue
                init_status_result = result[0] if result else {}
                current_product_data.update(
                    {
                        "New Feature Info": init_status_result.get("new_feature_info"),
                        "New Feature Info Str": init_status_result.get("new_feature_info_str"),
                        "Feature Info": init_status_result.get("feature_info"),
                    }
                )

            product_data = device.product.as_dict()
            if product_data:
                current_product_data["Product"] = product_data

            all_products_data[model] = current_product_data

    if record:
        if not all_products_data:
            click.echo("No device info updates needed.")
            return
        updated_device_info = {**existing_device_info, **all_products_data}
        device_info_path.parent.mkdir(parents=True, exist_ok=True)
        ordered_data = dict(sorted(updated_device_info.items(), key=lambda item: item[0]))
        with open(device_info_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(ordered_data, f, sort_keys=False)
        click.echo(f"Updated {device_info_path}.")
        click.echo("\n--- Device Info Updates ---\n")
        click.echo(yaml.safe_dump(all_products_data, sort_keys=False))
        return

    if all_products_data:
        click.echo("\n--- Device Information (copy to your YAML file) ---\n")
        click.echo(yaml.dump(all_products_data, sort_keys=False))


@click.command()
@click.option("--data-file", default="../device_info.yaml", help="Path to the YAML file with device feature data.")
@click.option("--output-file", default="../SUPPORTED_FEATURES.md", help="Path to the output markdown file.")
def update_docs(data_file: str, output_file: str):
    """
    Generates a markdown file by processing raw feature data from a YAML file.
    """
    data_path = Path(data_file)
    output_path = Path(output_file)

    if not data_path.exists():
        click.echo(f"Error: Data file not found at '{data_path}'", err=True)
        return

    click.echo(f"Loading data from {data_path}...")
    with open(data_path, encoding="utf-8") as f:
        product_data_from_yaml = yaml.safe_load(f)

    if not product_data_from_yaml:
        click.echo("No data found in YAML file. Exiting.", err=True)
        return

    product_features_map = {}
    all_feature_names = set()

    # Process the raw data from YAML to build the feature map
    for model, data in product_data_from_yaml.items():
        # Reconstruct the DeviceFeatures object from the raw data in the YAML file
        device_features = DeviceFeatures.from_feature_flags(
            new_feature_info=data.get("New Feature Info"),
            new_feature_info_str=data.get("New Feature Info Str"),
            feature_info=data.get("Feature Info"),
            product_nickname=data.get("Product Nickname"),
        )
        features_dict = asdict(device_features)

        # This dictionary will hold the final data for the markdown table row
        current_product_data = {
            "Product Nickname": data.get("Product Nickname", ""),
            "Protocol Version": data.get("Protocol Version", ""),
            "New Feature Info": data.get("New Feature Info", ""),
            "New Feature Info Str": data.get("New Feature Info Str", ""),
        }

        # Populate features from the calculated DeviceFeatures object
        for feature, is_supported in features_dict.items():
            all_feature_names.add(feature)
            if is_supported:
                current_product_data[feature] = "X"

        supported_codes = data.get("Feature Info", [])
        if isinstance(supported_codes, list):
            for code in supported_codes:
                feature_name = str(code)
                all_feature_names.add(feature_name)
                current_product_data[feature_name] = "X"

        product_features_map[model] = current_product_data

    # --- Helper function to write the markdown table ---
    def write_markdown_table(product_features: dict[str, dict[str, any]], all_features: set[str]):
        """Writes the data into a markdown table (products as columns)."""
        sorted_products = sorted(product_features.keys())
        special_rows = [
            "Product Nickname",
            "Protocol Version",
            "New Feature Info",
            "New Feature Info Str",
        ]
        # Regular features are the remaining keys, sorted alphabetically
        # We filter out the special rows to avoid duplicating them.
        sorted_features = sorted(list(all_features - set(special_rows)))

        header = ["Feature"] + sorted_products

        click.echo(f"Writing documentation to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("| " + " | ".join(header) + " |\n")
            f.write("|" + "---|" * len(header) + "\n")

            # Write the special metadata rows first
            for row_name in special_rows:
                row_values = [str(product_features[p].get(row_name, "")) for p in sorted_products]
                f.write("| " + " | ".join([row_name] + row_values) + " |\n")

            # Write the feature rows
            for feature in sorted_features:
                # Use backticks for feature names that are just numbers (from the list)
                display_feature = f"`{feature}`"
                feature_row = [display_feature]
                for product in sorted_products:
                    # Use .get() to place an 'X' or an empty string
                    feature_row.append(product_features[product].get(feature, ""))
                f.write("| " + " | ".join(feature_row) + " |\n")

    write_markdown_table(product_features_map, all_feature_names)
    click.echo("Done.")


cli.add_command(login)
cli.add_command(discover)
cli.add_command(list_devices)
cli.add_command(list_scenes)
cli.add_command(execute_scene)
cli.add_command(status)
cli.add_command(command)
cli.add_command(parser)
cli.add_command(session)
cli.add_command(get_device_info)
cli.add_command(update_docs)
cli.add_command(clean_summary)
cli.add_command(clean_record)
cli.add_command(dock_summary)
cli.add_command(volume)
cli.add_command(set_volume)
cli.add_command(maps)
cli.add_command(map_image)
cli.add_command(map_data)
cli.add_command(consumables)
cli.add_command(reset_consumable)
cli.add_command(rooms)
cli.add_command(home)
cli.add_command(features)
cli.add_command(child_lock)
cli.add_command(dnd)
cli.add_command(flow_led_status)
cli.add_command(led_status)
cli.add_command(network_info)


def main():
    return cli()


if __name__ == "__main__":
    main()

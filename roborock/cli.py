import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from pyshark import FileCapture  # type: ignore
from pyshark.capture.live_capture import LiveCapture, UnknownInterfaceException  # type: ignore
from pyshark.packet.packet import Packet  # type: ignore

from roborock import RoborockException
from roborock.containers import DeviceData, HomeData, HomeDataProduct, LoginData, NetworkInfo, RoborockBase, UserData
from roborock.devices.cache import Cache, CacheData
from roborock.devices.device_manager import create_device_manager, create_home_data_api
from roborock.protocol import MessageParser
from roborock.util import run_sync
from roborock.version_1_apis.roborock_local_client_v1 import RoborockLocalClientV1
from roborock.version_1_apis.roborock_mqtt_client_v1 import RoborockMqttClientV1
from roborock.web_api import RoborockApiClient

_LOGGER = logging.getLogger(__name__)


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
    home_data: HomeData | None = None
    network_info: dict[str, NetworkInfo] | None = None


class RoborockContext(Cache):
    roborock_file = Path("~/.roborock").expanduser()
    _cache_data: ConnectionCache | None = None

    def __init__(self):
        self.reload()

    def reload(self):
        if self.roborock_file.is_file():
            with open(self.roborock_file) as f:
                data = json.load(f)
                if data:
                    self._cache_data = ConnectionCache.from_dict(data)

    def update(self, cache_data: ConnectionCache):
        data = json.dumps(cache_data.as_dict(), default=vars, indent=4)
        with open(self.roborock_file, "w") as f:
            f.write(data)
        self.reload()

    def validate(self):
        if self._cache_data is None:
            raise RoborockException("You must login first")

    def cache_data(self) -> ConnectionCache:
        """Get the cache data."""
        self.validate()
        return self._cache_data

    async def get(self) -> CacheData:
        """Get cached value."""
        connection_cache = self.cache_data()
        return CacheData(home_data=connection_cache.home_data, network_info=connection_cache.network_info or {})

    async def set(self, value: CacheData) -> None:
        """Set value in the cache."""
        connection_cache = self.cache_data()
        connection_cache.home_data = value.home_data
        connection_cache.network_info = value.network_info
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
    "--password",
    required=False,
    help="Password for the Roborock account. If not provided, an email code will be requested.",
)
@click.pass_context
@run_sync()
async def login(ctx, email, password):
    """Login to Roborock account."""
    context: RoborockContext = ctx.obj
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
    context.update(LoginData(user_data=user_data, email=email))


@click.command()
@click.pass_context
@click.option("--duration", default=10, help="Duration to run the MQTT session in seconds")
@run_sync()
async def session(ctx, duration: int):
    context: RoborockContext = ctx.obj
    cache_data = context.cache_data()

    home_data_api = create_home_data_api(cache_data.email, cache_data.user_data)

    # Create device manager
    device_manager = await create_device_manager(cache_data.user_data, home_data_api, context)

    devices = await device_manager.get_devices()
    click.echo(f"Discovered devices: {', '.join([device.name for device in devices])}")

    click.echo("MQTT session started. Querying devices...")
    for device in devices:
        if not (status_trait := device.traits.get("status")):
            click.echo(f"Device {device.name} does not have a status trait")
            continue
        try:
            status = await status_trait.get_status()
        except RoborockException as e:
            click.echo(f"Failed to get status for {device.name}: {e}")
        else:
            click.echo(f"Device {device.name} status: {status.as_dict()}")

    click.echo("Listening for messages.")
    await asyncio.sleep(duration)

    # Close the device manager (this will close all devices and MQTT session)
    await device_manager.close()


async def _discover(ctx):
    context: RoborockContext = ctx.obj
    cache_data = context.cache_data()
    if not cache_data:
        raise Exception("You need to login first")
    client = RoborockApiClient(cache_data.email)
    home_data = await client.get_home_data(cache_data.user_data)
    cache_data.home_data = home_data
    context.update(cache_data)
    click.echo(f"Discovered devices {', '.join([device.name for device in home_data.get_all_devices()])}")


async def _load_and_discover(ctx) -> RoborockContext:
    """Discover devices if home data is not available."""
    context: RoborockContext = ctx.obj
    cache_data = context.cache_data()
    if not cache_data.home_data:
        await _discover(ctx)
        cache_data = context.cache_data()
    return context


@click.command()
@click.pass_context
@run_sync()
async def discover(ctx):
    await _discover(ctx)


@click.command()
@click.pass_context
@run_sync()
async def list_devices(ctx):
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()
    home_data = cache_data.home_data
    device_name_id = {device.name: device.duid for device in home_data.devices + home_data.received_devices}
    click.echo(json.dumps(device_name_id, indent=4))


@click.command()
@click.option("--device_id", required=True)
@click.pass_context
@run_sync()
async def list_scenes(ctx, device_id):
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()
    client = RoborockApiClient(cache_data.email)
    scenes = await client.get_scenes(cache_data.user_data, device_id)
    output_list = []
    for scene in scenes:
        output_list.append(scene.as_dict())
    click.echo(json.dumps(output_list, indent=4))


@click.command()
@click.option("--scene_id", required=True)
@click.pass_context
@run_sync()
async def execute_scene(ctx, scene_id):
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()
    client = RoborockApiClient(cache_data.email)
    await client.execute_scene(cache_data.user_data, scene_id)


@click.command()
@click.option("--device_id", required=True)
@click.pass_context
@run_sync()
async def status(ctx, device_id):
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()

    home_data = cache_data.home_data
    devices = home_data.devices + home_data.received_devices
    device = next(device for device in devices if device.duid == device_id)
    product_info: dict[str, HomeDataProduct] = {product.id: product for product in home_data.products}
    device_data = DeviceData(device, product_info[device.product_id].model, region=cache_data.user_data.region)

    mqtt_client = RoborockMqttClientV1(cache_data.user_data, device_data)
    if not (networking := cache_data.network_info.get(device.duid)):
        networking = await mqtt_client.get_networking()
        cache_data.network_info[device.duid] = networking
        context.update(cache_data)
    else:
        _LOGGER.debug("Using cached networking info for device %s: %s", device.duid, networking)

    local_device_data = DeviceData(
        device, product_info[device.product_id].model, networking.ip, region=cache_data.user_data.region
    )
    local_client = RoborockLocalClientV1(local_device_data)
    status = await local_client.get_status()
    click.echo(json.dumps(status.as_dict(), indent=4))


@click.command()
@click.option("--device_id", required=True)
@click.option("--cmd", required=True)
@click.option("--params", required=False)
@click.pass_context
@run_sync()
async def command(ctx, cmd, device_id, params):
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()

    home_data = cache_data.home_data
    devices = home_data.devices + home_data.received_devices
    device = next(device for device in devices if device.duid == device_id)
    model = next(
        (product.model for product in home_data.products if device is not None and product.id == device.product_id),
        None,
    )
    if model is None:
        raise RoborockException(f"Could not find model for device {device.name}")
    device_info = DeviceData(device=device, model=model, region=cache_data.user_data.region)
    mqtt_client = RoborockMqttClientV1(cache_data.user_data, device_info)
    await mqtt_client.send_command(cmd, json.loads(params) if params is not None else None)
    await mqtt_client.async_release()


@click.command()
@click.option("--local_key", required=True)
@click.option("--device_ip", required=True)
@click.option("--file", required=False)
@click.pass_context
@run_sync()
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


cli.add_command(login)
cli.add_command(discover)
cli.add_command(list_devices)
cli.add_command(list_scenes)
cli.add_command(execute_scene)
cli.add_command(status)
cli.add_command(command)
cli.add_command(parser)
cli.add_command(session)


def main():
    return cli()


if __name__ == "__main__":
    main()

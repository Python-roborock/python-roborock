from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import click
from pyshark import FileCapture  # type: ignore
from pyshark.capture.live_capture import LiveCapture, UnknownInterfaceException  # type: ignore
from pyshark.packet.packet import Packet  # type: ignore

from roborock import RoborockException
from roborock.containers import DeviceData, HomeDataProduct, LoginData
from roborock.protocol import MessageParser
from roborock.util import run_sync
from roborock.version_1_apis.roborock_local_client_v1 import RoborockLocalClientV1
from roborock.version_1_apis.roborock_mqtt_client_v1 import RoborockMqttClientV1
from roborock.web_api import RoborockApiClient

_LOGGER = logging.getLogger(__name__)


class RoborockContext:
    roborock_file = Path("~/.roborock").expanduser()
    _login_data: LoginData | None = None

    def __init__(self):
        self.reload()

    def reload(self):
        if self.roborock_file.is_file():
            with open(self.roborock_file) as f:
                data = json.load(f)
                if data:
                    self._login_data = LoginData.from_dict(data)

    def update(self, login_data: LoginData):
        data = json.dumps(login_data.as_dict(), default=vars)
        with open(self.roborock_file, "w") as f:
            f.write(data)
        self.reload()

    def validate(self):
        if self._login_data is None:
            raise RoborockException("You must login first")

    def login_data(self):
        self.validate()
        return self._login_data


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
@click.option("--password", required=True)
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
    user_data = await client.pass_login(password)
    context.update(LoginData(user_data=user_data, email=email))


async def _discover(ctx):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data:
        raise Exception("You need to login first")
    client = RoborockApiClient(login_data.email)
    home_data = await client.get_home_data(login_data.user_data)
    login_data.home_data = home_data
    context.update(login_data)
    click.echo(f"Discovered devices {', '.join([device.name for device in home_data.get_all_devices()])}")


@click.command()
@click.pass_context
@run_sync()
async def discover(ctx):
    await _discover(ctx)


@click.command()
@click.pass_context
@run_sync()
async def list_devices(ctx):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data
    device_name_id = ", ".join(
        [f"{device.name}: {device.duid}" for device in home_data.devices + home_data.received_devices]
    )
    click.echo(f"Known devices {device_name_id}")


@click.command()
@click.option("--device_id", required=True)
@click.pass_context
@run_sync()
async def list_scenes(ctx, device_id):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    client = RoborockApiClient(login_data.email)
    scenes = await client.get_scenes(login_data.user_data, device_id)
    output_list = []
    for scene in scenes:
        output_list.append(scene.as_dict())
    click.echo(json.dumps(output_list, indent=4))


@click.command()
@click.option("--scene_id", required=True)
@click.pass_context
@run_sync()
async def execute_scene(ctx, scene_id):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    client = RoborockApiClient(login_data.email)
    await client.execute_scene(login_data.user_data, scene_id)


@click.command()
@click.option("--device_id", required=True)
@click.pass_context
@run_sync()
async def status(ctx, device_id):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data
    devices = home_data.devices + home_data.received_devices
    device = next(device for device in devices if device.duid == device_id)
    product_info: dict[str, HomeDataProduct] = {product.id: product for product in home_data.products}
    device_data = DeviceData(device, product_info[device.product_id].model)
    mqtt_client = RoborockMqttClientV1(login_data.user_data, device_data)
    networking = await mqtt_client.get_networking()
    local_device_data = DeviceData(device, product_info[device.product_id].model, networking.ip)
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
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data
    devices = home_data.devices + home_data.received_devices
    device = next(device for device in devices if device.duid == device_id)
    model = next(
        (product.model for product in home_data.products if device is not None and product.id == device.product_id),
        None,
    )
    if model is None:
        raise RoborockException(f"Could not find model for device {device.name}")
    device_info = DeviceData(device=device, model=model)
    mqtt_client = RoborockMqttClientV1(login_data.user_data, device_info)
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


def main():
    return cli()


if __name__ == "__main__":
    main()

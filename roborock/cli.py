from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import click
from pyshark import FileCapture  # type: ignore
from pyshark.capture.live_capture import LiveCapture, UnknownInterfaceException  # type: ignore
from pyshark.packet.packet import Packet  # type: ignore

from roborock import SHORT_MODEL_TO_ENUM, DeviceFeatures, RoborockCommand, RoborockException
from roborock.containers import DeviceData, HomeData, HomeDataProduct, LoginData
from roborock.devices.device_manager import create_device_manager, create_home_data_api
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

    def login_data(self) -> LoginData:
        """Get the login data."""
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
    login_data = context.login_data()

    home_data_api = create_home_data_api(login_data.email, login_data.user_data)

    async def home_data_cache() -> HomeData:
        if login_data.home_data is None:
            login_data.home_data = await home_data_api()
            context.update(login_data)
        return login_data.home_data

    # Create device manager
    device_manager = await create_device_manager(login_data.user_data, home_data_cache)

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


@click.command()
@click.pass_context
@run_sync()
async def update_docs(ctx):
    """
    Generates or updates a markdown file with features for all devices.
    """
    MARKDOWN_FILE = Path("../SUPPORTED_FEATURES.md")

    def write_markdown_table(product_data: dict[str, dict[str, str]], all_features: set[str]):
        """Writes the data into a markdown table (products as columns)."""
        sorted_products = sorted(product_data.keys())
        sorted_features = sorted(list(all_features))

        header = ["Feature"] + sorted_products

        with open(MARKDOWN_FILE, "w", encoding="utf-8") as f:
            f.write("| " + " | ".join(header) + " |\n")
            f.write("|" + "---|" * len(header) + "\n")

            # Create data for special rows
            special_rows = [
                "Product Nickname",
                "Protocol Version",
                "New Feature Info",
                "New Feature Info Str",
                "Feature Info",
            ]
            for row in special_rows:
                row_values = [str(product_data[p].get(row, "")) for p in sorted_products]
                f.write("| " + " | ".join([row] + row_values) + " |\n")
            for feature in sorted_features:
                feature_row = [f"`{feature}`"]
                for product in sorted_products:
                    feature_row.append(product_data[product].get(feature, ""))
                f.write("| " + " | ".join(feature_row) + " |\n")

    product_features_map = {}
    all_feature_names = set()

    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data

    all_devices = home_data.devices + home_data.received_devices
    click.echo(f"Found {len(all_devices)} devices. Fetching current data via MQTT...")

    for device in all_devices:
        click.echo(f"  - Processing {device.name} ({device.duid})")
        product_info = home_data.product_map[device.product_id]
        device_data = DeviceData(device, product_info.model)
        mqtt_client = RoborockMqttClientV1(login_data.user_data, device_data)
        try:
            init_status_result = await mqtt_client.send_command(
                RoborockCommand.APP_GET_INIT_STATUS,
            )
            product_nickname = SHORT_MODEL_TO_ENUM.get(product_info.model.split(".")[-1])
            device_features = DeviceFeatures.from_feature_flags(
                new_feature_info=init_status_result.get("new_feature_info"),
                new_feature_info_str=init_status_result.get("new_feature_info_str"),
                feature_info=init_status_result.get("feature_info"),
                product_nickname=product_nickname,
            )
            features_dict = asdict(device_features)

            current_product_data = {
                "Protocol Version": device.pv,
                "Product Nickname": product_nickname,
                "New Feature Info": init_status_result.get("new_feature_info"),
                "New Feature Info Str": init_status_result.get("new_feature_info_str"),
                "Feature Info": init_status_result.get("feature_info"),
            }

            for feature, is_supported in features_dict.items():
                all_feature_names.add(feature)
                current_product_data[feature] = "X" if is_supported else ""

            product_features_map[product_info.model] = current_product_data

        except Exception as e:
            click.echo(f"    - Error processing device {device.name}: {e}")
        finally:
            await mqtt_client.async_release()

    if not product_features_map:
        click.echo("No device data could be gathered. File not updated.")
        return

    click.echo(f"Writing updated data to {MARKDOWN_FILE}...")
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
cli.add_command(update_docs)


def main():
    return cli()


if __name__ == "__main__":
    main()

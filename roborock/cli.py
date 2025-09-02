import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click
import yaml
from pyshark import FileCapture  # type: ignore
from pyshark.capture.live_capture import LiveCapture, UnknownInterfaceException  # type: ignore
from pyshark.packet.packet import Packet  # type: ignore

from roborock import SHORT_MODEL_TO_ENUM, DeviceFeatures, RoborockCommand, RoborockException
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
    home_data = await client.get_home_data_v3(cache_data.user_data)
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
    device_data = DeviceData(device, product_info[device.product_id].model)

    mqtt_client = RoborockMqttClientV1(cache_data.user_data, device_data)
    if not (networking := cache_data.network_info.get(device.duid)):
        networking = await mqtt_client.get_networking()
        cache_data.network_info[device.duid] = networking
        context.update(cache_data)
    else:
        _LOGGER.debug("Using cached networking info for device %s: %s", device.duid, networking)

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
    device_info = DeviceData(device=device, model=model)
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


@click.command()
@click.pass_context
@run_sync()
async def get_device_info(ctx: click.Context):
    """
    Connects to devices and prints their feature information in YAML format.
    """
    click.echo("Discovering devices...")
    context: RoborockContext = await _load_and_discover(ctx)
    cache_data = context.cache_data()

    home_data = cache_data.home_data

    all_devices = home_data.devices + home_data.received_devices
    if not all_devices:
        click.echo("No devices found.")
        return

    click.echo(f"Found {len(all_devices)} devices. Fetching data...")

    all_products_data = {}

    for device in all_devices:
        click.echo(f"  - Processing {device.name} ({device.duid})")
        product_info = home_data.product_map[device.product_id]
        device_data = DeviceData(device, product_info.model)
        mqtt_client = RoborockMqttClientV1(cache_data.user_data, device_data)

        try:
            init_status_result = await mqtt_client.send_command(
                RoborockCommand.APP_GET_INIT_STATUS,
            )
            product_nickname = SHORT_MODEL_TO_ENUM.get(product_info.model.split(".")[-1]).name
            current_product_data = {
                "Protocol Version": device.pv,
                "Product Nickname": product_nickname,
                "New Feature Info": init_status_result.get("new_feature_info"),
                "New Feature Info Str": init_status_result.get("new_feature_info_str"),
                "Feature Info": init_status_result.get("feature_info"),
            }

            all_products_data[product_info.model] = current_product_data

        except Exception as e:
            click.echo(f"    - Error processing device {device.name}: {e}", err=True)
        finally:
            await mqtt_client.async_release()

    if all_products_data:
        click.echo("\n--- Device Information (copy to your YAML file) ---\n")
        # Use yaml.dump to print in a clean, copy-paste friendly format
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


def main():
    return cli()


if __name__ == "__main__":
    main()

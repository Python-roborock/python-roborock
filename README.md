# Roborock

<p align="center">
  <a href="https://pypi.org/project/python-roborock/">
    <img src="https://img.shields.io/pypi/v/python-roborock.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/python-roborock.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/python-roborock.svg?style=flat-square" alt="License">
</p>

Roborock library for online and offline control of your vacuums.

## Installation

Install this via pip (or your favourite package manager):

`pip install python-roborock`

## Functionality

You can see all of the commands supported [here](https://python-roborock.readthedocs.io/en/latest/api_commands.html)

## Sending Commands

Here is an example that requires no manual intervention and can be done all automatically. You can skip some steps by
caching values or looking at them and grabbing them manually.
```python
import asyncio

from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient

async def main():
    web_api = RoborockApiClient(username="youremailhere")
    # Login via your password
    user_data = await web_api.pass_login(password="pass_here")
    # Or login via a code
    await web_api.request_code()
    code = input("What is the code?")
    user_data = await web_api.code_login(code)

    # Get home data
    home_data = await web_api.get_home_data_v2(user_data)

    # Get the device you want
    device = home_data.devices[0]

    # Get product ids:
    product_info: dict[str, HomeDataProduct] = {
            product.id: product for product in home_data.products
        }
    # Create the Mqtt(aka cloud required) Client
    device_data = DeviceData(device, product_info[device.product_id].model)
    mqtt_client = RoborockMqttClientV1(user_data, device_data)
    networking = await mqtt_client.get_networking()
    local_device_data = DeviceData(device, product_info[device.product_id].model, networking.ip)
    local_client = RoborockLocalClientV1(local_device_data)
    # You can use the send_command to send any command to the device
    status = await local_client.send_command(RoborockCommand.GET_STATUS)
    # Or use existing functions that will give you data classes
    status = await local_client.get_status()

asyncio.run(main())
```

## Supported devices

You can find what devices are supported
[here](https://python-roborock.readthedocs.io/en/latest/supported_devices.html).
Please note this may not immediately contain the latest devices.


## Credits

Thanks @rovo89 for https://gist.github.com/rovo89/dff47ed19fca0dfdda77503e66c2b7c7 And thanks @PiotrMachowski for https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor

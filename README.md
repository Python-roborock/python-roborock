# Roborock

<p align="center">
  <a href="https://pypi.org/project/python-roborock/">
    <img src="https://img.shields.io/pypi/v/python-roborock.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/python-roborock.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/python-roborock.svg?style=flat-square" alt="License">
    <a href="https://codecov.io/github/Python-roborock/python-roborock" >
  <img src="https://codecov.io/github/Python-roborock/python-roborock/graph/badge.svg?token=KEK4S3FPSZ" alt="Code Coverage"/>
 </a>
</p>


Roborock library for online and offline control of your vacuums.

## Installation

Install this via pip (or your favourite package manager):

`pip install python-roborock`

## Example Usage

See [examples/example.py](examples/example.py) for a more full featured example,
or the [API documentation](https://python-roborock.github.io/python-roborock/)
for more details.

Here is a basic example:

```python
import asyncio

from roborock.web_api import RoborockApiClient
from roborock.devices.device_manager import create_device_manager, UserParams


async def main():
    email_address = "youremailhere@example.com"
    web_api = RoborockApiClient(username=email_address)
    # Send a login code to the above email address
    await web_api.request_code()
    # Prompt the user to enter the code
    code = input("What is the code?")
    user_data = await web_api.code_login(code)

    # Create a device manager that can discover devices.
    user_params = UserParams(username=email_address, user_data=user_data)
    device_manager = await create_device_manager(user_params)
    devices = await device_manager.get_devices()

    # Get all vacuum devices. Each device generation has different capabilities
    # and APIs available so to find vacuums we filter by the v1 PropertiesApi.
    for device in devices:
        if not device.v1_properties:
            continue

        # The PropertiesAPI has traits different device commands such as getting
        # status, sending clean commands, etc. For this example we send a
        # command to refresh the current device status.
        status_trait = device.v1_properties.status
        await status_trait.refresh()
        print(status_trait)

asyncio.run(main())
```


## Functionality

The library interacts with devices through specific API properties based on the device protocol:

*   **Standard Vacuums (V1 Protocol)**: Most robot vacuums use this. Interaction is done through `device.v1_properties`, which contains traits like `status`, `consumables`, and `maps`. Use the `command` trait for actions like starting or stopping cleaning.
*   **Wet/Dry Vacuums & Washing Machines (A01 Protocol)**: Devices like the Dyad and Zeo use this. Interaction is done through `device.a01_properties` using `query_values()` and `set_value()`.

You can find detailed documentation for [Devices](https://python-roborock.github.io/python-roborock/roborock/devices/device.html) and [Traits](https://python-roborock.github.io/python-roborock/roborock/devices/traits.html).


## Supported devices

You can find what devices are supported
[here](https://python-roborock.readthedocs.io/en/latest/supported_devices.html).
Please note this may not immediately contain the latest devices.


## Acknowledgements

* Thanks to [@rovo89](https://github.com/rovo89) for [Login APIs gist](https://gist.github.com/rovo89/dff47ed19fca0dfdda77503e66c2b7c7).
* Thanks to [@PiotrMachowski](https://github.com/PiotrMachowski) for [Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor).

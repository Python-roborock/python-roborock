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

## Functionality

You can see all of the commands supported [here](https://python-roborock.readthedocs.io/en/latest/api_commands.html)

## Example Usage

```python
import asyncio

from roborock.web_api import RoborockApiClient
from roborock.devices.device_manager import create_device_manager, UserParams


async def main():
    web_api = RoborockApiClient(username="youremailhere")
    # Login via your password
    user_data = await web_api.pass_login(password="pass_here")
    # Or login via a code
    await web_api.request_code()
    code = input("What is the code?")
    user_data = await web_api.code_login(code)

    # Create a device manager that can discover devices.
    user_params = UserParams(
        username="youremailhere",
        user_data=user_data,
    )
    device_manager = await create_device_manager(user_params)
    devices = await device_manager.get_devices()

    # Get all vacuum devices that support the v1 PropertiesApi
    for device in devices:
        if not device.v1_properties:
            continue

        # Refresh the current device status
        status_trait = device.v1_properties.status
        await status_trait.refresh()
        print(status_trait)

asyncio.run(main())
```

See [examples/example.py](examples/example.py) for a more full featured example
that has performance improvements to cache cloud information to prefer
connections over the local network.

## Supported devices

You can find what devices are supported
[here](https://python-roborock.readthedocs.io/en/latest/supported_devices.html).
Please note this may not immediately contain the latest devices.


## Credits

Thanks @rovo89 for https://gist.github.com/rovo89/dff47ed19fca0dfdda77503e66c2b7c7 And thanks @PiotrMachowski for https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor

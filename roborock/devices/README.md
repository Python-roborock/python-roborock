# Roborock Device Manager

This library provides a high-level interface for discovering and controlling Roborock devices. It abstracts the underlying communication protocols (MQTT, Local TCP) and provides a unified `DeviceManager` for interacting with your devices.

For internal architecture details, protocol specifications, and design documentation, please refer to [docs/DEVICES.md](https://github.com/python-roborock/python-roborock/docs/DEVICES.md).

## Getting Started

### Credentials

To connect to your devices, you first need to obtain your user data (including the `rriot` token) from the Roborock Cloud. This is handled via the `RoborockApiClient`.

## Usage Guide

The core entry point for the library is the `DeviceManager`. It handles:
1.  **Device Discovery**: Fetching the list of devices associated with your account.
2.  **Connection Management**: Automatically determining the best connection method (Local vs MQTT) and protocol version (V1 vs A01/B01).
3.  **Command Execution**: Sending commands and query status.

### Example

See [examples/example.py](https://github.com/python-roborock/python-roborock/examples/example.py) for a complete example of how to login, create a device manager, and list the status of your vacuums.

### Device Properties

Different devices support different property sets:

*   **`v1_properties`**: Primarily for Vacuum Robots (S7, S8, Q5, etc.). Supports traits like `status`, `consumables`, `fan_power`, `water_box`.
*   **`a01_properties`**: For Washer/Dryers and handheld Wet/Dry Vacuums (Dyad, Zeo) that use another newer protocol.
*   **`b01_q7_properties`** and **`b01_q10_properties`**: For newer Vacuum/Mop devices using newer protocol instead of v1.

You can check if a property set is available by checking if the property on the device object is not `None` (e.g. `if device.v1_properties:`).

### Caching

Use `FileCache` or your own `Cache` implementation to persist:
- `HomeData`: The list of your home's rooms and devices.
- `NetworkingInfo`: Device IP addresses and tokens.
- `Device Capabilities`: What features your specific model supports.

This speeds up startup time and reduces load on the Roborock cloud APIs.

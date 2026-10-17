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


## Q10 archive updates

Archive updates use the same push-driven pattern as all other Q10 traits.
Register an update listener and update your view's state from the trait when the
callback runs. `refresh_detail()` publishes a selection; the device sends the
archive independently through its push stream. A history listener can also fire
for record-list updates, so read whichever properties your view displays on each
callback.

```python
from roborock.devices.traits.b01.q10 import Q10PropertiesApi


class ArchivePreview:
    def __init__(self, properties: Q10PropertiesApi) -> None:
        self.history = properties.clean_history
        self.image_content = self.history.detail_image_content
        self._unsubscribe = self.history.add_update_listener(self._archive_updated)

    def _archive_updated(self) -> None:
        self.image_content = self.history.detail_image_content
        # Notify your UI to redraw using the latest received image.

    async def select_latest_record(self) -> None:
        record = self.history.last_record
        if record is not None and record.map_len:
            await self.history.refresh_detail(record)

    def close(self) -> None:
        self._unsubscribe()
```

Keep the listener registered while the view is open and unsubscribe when it
closes. The callback receives updates regardless of which client requested them.

Clean-record detail packets contain no record identifier. `detail` represents
the latest received archive, including delayed or unsolicited pushes; it cannot
be reliably attributed to the record passed to `refresh_detail()`. In
particular, the API does not expose a `detail_record` association. Avoid
presenting a requested record's label as confirmed metadata for the response.
Concurrent selections and selections from another client have the same
limitation.

Saved-map previews follow the same listener pattern via `properties.maps`.
Call `await properties.maps.refresh_detail(map_id)` for a listed map, or omit
`map_id` to use the first map in the list. `detail_map_id` comes from the received
packet itself, so a consumer can check it before displaying a preview. A delayed
preview can replace the latest saved-map preview; no request ID is available to
identify which selection produced it. Archive updates never replace the live
map or trace in `properties.map`.

`properties.as_dict()` includes clean-history records and path data and
saved-map metadata. Binary map grids and PNG bytes are excluded; access images
through `detail_image_content`. Live map and trace updates use the usual trait
listener API.

"""Testing fakes and simulators for python-roborock.

This package provides stateful firmware simulators (e.g. `V1VacuumSimulator`),
fake transport channels (`FakeChannel`), and cloud orchestration simulators (`FakeRoborockCloud`)
to allow downstream consumers (such as Home Assistant integrations) to write high-fidelity
integration tests using the real client library classes instead of fragile top-level mocks.

Testing Architecture & Boundaries
---------------------------------
We fake communication at two boundaries:
1.  **Network HTTP API Interception**: `FakeRoborockCloud.patch_device_manager()` routes
    HTTP requests (such as discovery, login, home details) to custom mock endpoints using
    `aioresponses` under the hood. No Python client methods are mocked; the real EAPI client
    executes fully.
2.  **Plaintext RPC Message Interception**: Device communication is intercepted at the
    plaintext JSON RPC level (Layer 2). The real client classes (`V1Channel`, `MqttChannel`)
    run under test, but their transport calls are intercepted by our stateful simulators.

     ┌────────────────────────────────────────────────────────┐
     │               TESTED CLIENT (REAL CODE)                │
     │                                                        │
     │  RoborockDevice / Traits / V1RpcChannel / V1Channel    │
     └──────────────────────────┬─────────────────────────────┘
                                │
                      ROBOROCKMESSAGE PAYLOADS
                      (Plaintext JSON commands)
                                │
     ┌──────────────────────────▼─────────────────────────────┐
     │                 SIMULATOR (TEST FAKE)                  │
     │                                                        │
     │  FakeChannel (Intercepts publish/subscribe)            │
     │  RoborockDeviceSimulator (Stateful firmware simulator) │
     └────────────────────────────────────────────────────────┘

Integration Usage Example
-------------------------
```python
from roborock.testing import FakeRoborockCloud, V1VacuumSimulator

async def test_start_vacuum_service():
    # Setup cloud state and add a simulated vacuum device
    cloud = FakeRoborockCloud()
    fake_device = V1VacuumSimulator(duid="living_room_s7", battery=100, state=RoborockStateCode.charging)
    cloud.add_device(fake_device)

    # Patch channels and API calls using our cloud context manager
    with cloud.patch_device_manager():
        # Create the real client manager (logins and discovers natively via mock HTTP)
        manager = await create_device_manager(
            user_params=UserParams(username="test_user", user_data=USER_DATA),
            cache=InMemoryCache(),
        )

    # Fetch the discovered device client
    devices = await manager.get_devices()
    device = devices[0]

    # Trigger client start command
    await device.v1_properties.command.send("app_start")

    # Assert against the simulated vacuum state
    assert fake_device.state == RoborockStateCode.cleaning
```
"""

from roborock.testing.b01_q10_simulator import (
    DEFAULT_Q10_STATUS,
    Q10VacuumSimulator,
)
from roborock.testing.channel import FakeChannel
from roborock.testing.cloud import FakeRoborockCloud, FakeWebApiClient
from roborock.testing.simulator import (
    DEFAULT_KEY_T,
    DEFAULT_LOCAL_KEY,
    DEFAULT_PRODUCT_ID,
    RoborockDeviceSimulator,
)
from roborock.testing.v1_simulator import (
    DEFAULT_APP_INIT,
    DEFAULT_CLEAN_SUMMARY,
    DEFAULT_CONSUMABLE,
    DEFAULT_DND_TIMER,
    DEFAULT_LAST_CLEAN_RECORD,
    DEFAULT_NETWORK_INFO,
    DEFAULT_STATUS,
    V1VacuumSimulator,
)

__all__ = [
    "DEFAULT_APP_INIT",
    "DEFAULT_CLEAN_SUMMARY",
    "DEFAULT_CONSUMABLE",
    "DEFAULT_DND_TIMER",
    "DEFAULT_KEY_T",
    "DEFAULT_LAST_CLEAN_RECORD",
    "DEFAULT_LOCAL_KEY",
    "DEFAULT_NETWORK_INFO",
    "DEFAULT_PRODUCT_ID",
    "DEFAULT_Q10_STATUS",
    "DEFAULT_STATUS",
    "FakeChannel",
    "FakeRoborockCloud",
    "FakeWebApiClient",
    "Q10VacuumSimulator",
    "RoborockDeviceSimulator",
    "V1VacuumSimulator",
]

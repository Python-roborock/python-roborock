# Roborock Device Discovery

This page documents the full lifecycle of device discovery across Cloud and Network.

## Init account setup

### Login

- Login can happen with either email and password or email and sending a code. We
  currently prefer email with sending a code -- however the roborock no longer
  supports this method of login. In the future we may want to migrate to password
  if this login method is no longer supported.
- The Login API provides a `userData` object with information on connecting to the cloud APIs
- This `rriot` data contains per-session information, unique each time you login.
  - This contains information used to connect to MQTT
  - You get an `-eu` suffix in the API URLs if you are in the eu and `-us` if you are in the us

## Home Data

The `HomeData` includes information about the various devices in the home. We use `v3`
and it is notable that if devices don't show up in the `home_data` response it is likely
that a newer version of the API should be used.

- `products`: This is a list of all of the products you have on your account. These objects are always the same (i.e. a s7 maxv is always the exact same.)
  - It only shows the products for devices available on your account
- `devices` and `received_devices`:
  - These both share the same objects, but one is for devices that have been shared with you and one is those that are on your account.
  - The big things here are (MOST are static):
    - `duid`: A unique identifier for your device (this is always the same i think)
    - `name`: The name of the device in your app
    - `local_key`: The local key that is needed for encoding and decoding messages for the device. This stays the same unless someone sets their vacuum back up.
    - `pv`: the protocol version (i.e. 1.0 or A1 or B1)
    - `product_id`: The id of the product from the above products list.
    - `device_status`: An initial status for some of the data we care about, though this changes on each update.
- `rooms`: The rooms in the home.
  - This changes if the user adds a new room or changes its name.
  - We have to combine this with the room numbers from `GET_ROOM_MAPPING` on the device
  - There is another REST request `get_rooms` that will do the same thing.
  - Note: If we cache home_data, we likely need to use `get_rooms` to get rooms fresh

## Device Connections

### MQTT connection

- Initial device information must be obtained from MQTT
- We typically set up the MQTT device connection before the local device connection.
  - The `NetworkingInfo` needs to be fetched to get additional information about connecting to the device:
    - e.g. Local IP Address
  - This networking info can be cached to reduce network calls
  - MQTT also is the only way to get the device Map
- Incoming and outgoing messages are decoded/encoded using the device `local_key`
- Otherwise all commands may be performed locally.

## Local connection

- We can use the `ip` from the `NetworkingInfo` to find the device
- The local connection is preferred to for improved latency and reducing load on the cloud servers to avoid rate limiting.
- Connections are made using a normal TCP socket on port `58867`
- Incoming and outgoing messages are decoded/encoded using the device `local_key`
- Messages received on the stream may be partially received so we keep a running as messages are partially decoded

## Design

### Current API Issues

- Complex Inheritance Hierarchy: Multiple inheritance with classes like RoborockMqttClientV1 inheriting from both RoborockMqttClient and RoborockClientV1

- Callback-Heavy Design: Heavy reliance on callbacks and listeners in RoborockClientV1.on_message_received and the ListenerModel system

- Version Fragmentation: Separate v1 and A01 APIs with different patterns and abstractions

- Mixed Concerns: Classes handle both communication protocols (MQTT/local) and device-specific logic

- Complex Caching: The AttributeCache system with RepeatableTask adds complexity

- Manual Connection Management: Users need to manually set up both MQTT and local clients as shown in the README example

## Design Changes

- Prefer a single unfieid client that handles both MQTT and local connections internally.

- Home and device discovery (fetching home data and device setup) will be behind a single API.

- Asyncio First: Everything should be asyncio as much as possible, with fewer callbacks.

- The clients should be working in terms of devices. We need to detect capabilities for each device and not expose details about API versions.

- Reliability issues: The current Home Assistant integration has issues with reliability and needs to be simplified. It may be that there are bugs with the exception handling and it's too heavy the cloud APIs and could benefit from more seamless caching.

## Implementation Details

- We don't really need to worry about backwards compatibility for the new set of APIs.

- We'll have a `RoborockManager` responsible for managing the connections and getting devices.

- Caching can be persisted to disk. The caller can implement the cache storage themselves, but we need to give them an API to do so.

- Users don't really choose between cloud vs local. However, we will want to allow the caller to know if its using the locale connection so we can show a warnings.

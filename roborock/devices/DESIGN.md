# Roborock Python Library Design

This document outlines the current architecture and design of the `python-roborock` library.

## High-Level Architecture

The library is designed to communicate with Roborock devices via two primary transport mechanisms:
1.  **Cloud (MQTT)**: Uses the Roborock cloud infrastructure.
2.  **Local (TCP)**: Direct connection to the device on the local network.

The core components are:
*   **Device Manager**: Handles discovery and lifecycle of devices.
*   **Web API**: Fetches user and home configuration data.
*   **Device Model**: Represents a physical device and its capabilities.
*   **Communication Channels**: Abstracts the transport layer (MQTT vs Local).

## Component Detail

### 1. Device Discovery (`DeviceManager`)

The `DeviceManager` (`roborock/devices/device_manager.py`) is the entry point.
*   **Input**: `UserParams` (credentials).
*   **Process**:
    1.  Authenticates via `UserWebApiClient`.
    2.  Fetches `HomeData` (list of devices, products, rooms).
    3.  Iterates through devices and uses a factory pattern (`device_creator`) to instantiate specific `RoborockDevice` subclasses based on the protocol version (`V1`, `A01`, `B01`).
*   **Output**: A list of `RoborockDevice` instances.

### 2. Device Model (`RoborockDevice`)

The `RoborockDevice` (`roborock/devices/device.py`) is the base class for all devices.
*   **Composition**:
    *   `HomeDataDevice`: Static info (DUID, name).
    *   `HomeDataProduct`: Model info.
    *   `Channel`: The communication pipe.
    *   `Traits`: Capabilities mixed in via `TraitsMixin`.
*   **Traits System**: Devices expose functionality through traits (e.g., `FanSpeedTrait`, `CleaningTrait`). This allows for a unified interface across different device protocols.

### 3. Communication Layer

The library uses a layered channel architecture to abstract the differences between MQTT and Local connections.

#### Channels (`Channel` Protocol)
*   **`MqttChannel`**: Wraps the `MqttSession`. Handles topic construction (`rr/m/i/...`) and message encoding/decoding using the device's `local_key`.
*   **`LocalChannel`**: Manages a direct TCP connection (port 58867). Handles the custom handshake/heartbeat protocol and message framing.
*   **`V1Channel`**: A "smart" channel for V1 devices. It holds both an `MqttChannel` and a `LocalChannel`. It manages the complexity of:
    *   Fetching `NetworkingInfo` (to get the local IP).
    *   Establishing the local connection.
    *   Fallback logic (preferring local, falling back to MQTT).

#### RPC Abstraction (`V1RpcChannel`)
Above the raw byte-oriented `Channel`, the `V1RpcChannel` provides a command-oriented interface (`send_command`).
*   **`PayloadEncodedV1RpcChannel`**: Handles serialization of RPC commands (JSON payload -> Encrypted Bytes).
*   **`PickFirstAvailable`**: A composite channel that attempts to send a command via the Local channel first, and falls back to MQTT if the local connection is unavailable.

### 4. Session Management

*   **`RoborockMqttSession`**: Manages the persistent connection to the Roborock MQTT broker. It handles authentication, keepalives, and dispatching incoming messages to the appropriate `MqttChannel` based on topic.
*   **`LocalSession`**: Currently a factory for creating `LocalChannel` instances.

## Protocol Details

The library handles two variations of the underlying wire protocol depending on the transport.

#### Message Framing
*   **Local (TCP)**: Messages are **length-prefixed**. A 4-byte integer at the start of each packet indicates the total length of the message. This is necessary for framing over the streaming TCP connection.
*   **MQTT**: Messages are **raw**. The MQTT packet boundaries themselves serve as the framing mechanism, so no length prefix is added.

#### MQTT Authentication
The connection to the Roborock MQTT broker requires specific credentials derived from the user's `rriot` data (obtained during login):
*   **Username**: Derived from `MD5(rriot.u + ":" + rriot.k)`.
*   **Password**: Derived from `MD5(rriot.s + ":" + rriot.k)`.
*   **Topics**:
    *   Command (Publish): `rr/m/i/{rriot.u}/{username}/{duid}`
    *   Response (Subscribe): `rr/m/o/{rriot.u}/{username}/{duid}`

#### Local Handshake
1.  **Negotiation**: The client attempts to connect using a list of supported versions (currently `V1` and `L01`).
2.  **Hello Request**: Client sends a `HELLO_REQUEST` message containing the version string and a `connect_nonce`.
3.  **Hello Response**: Device responds with `HELLO_RESPONSE`. The client extracts the `ack_nonce` (from the message's `random` field).
4.  **Session Setup**: The `local_key`, `connect_nonce`, and `ack_nonce` are used to configure the encryption for subsequent messages.

#### Protocol Versions

The library supports multiple protocol versions which differ primarily in their encryption schemes:

*   **V1 (Legacy/Standard)**:
    *   **Encryption**: AES-128-ECB.
    *   **Key Derivation**: `MD5(timestamp + local_key + SALT)`.
    *   **Structure**: Header (Version, Seq, Random, Timestamp, Protocol) + Encrypted Payload + CRC32 Checksum.

*   **L01 (Newer)**:
    *   **Encryption**: AES-256-GCM (Authenticated Encryption).
    *   **Key Derivation**: SHA256 based on `timestamp`, `local_key`, and `SALT`.
    *   **IV/AAD**: Derived from sequence numbers and nonces (`connect_nonce`, `ack_nonce`) exchanged during handshake.
    *   **Security**: Provides better security against replay attacks and tampering compared to V1.

*   **A01 / B01**:
    *   **Encryption**: AES-CBC.
    *   **IV**: Derived from `MD5(random + HASH)`.
    *   These are typically used by newer camera-equipped models (e.g., S7 MaxV, Zeo).

## Data Flow (V1 Device Example)

1.  **Initialization**: `DeviceManager` creates a `V1Channel` with an `MqttChannel` and `LocalSession`.
2.  **Connection**:
    *   The `MqttChannel` is ready immediately (sharing the global `MqttSession`).
    *   The `V1Channel` attempts to connect locally in the background:
        1.  Sends a request via MQTT to get `NetworkingInfo` (contains Local IP).
        2.  Uses `LocalSession` to create a `LocalChannel` to that IP.
        3.  Performs the local handshake.
3.  **Command Execution**:
    *   User calls a method (e.g., `start_cleaning`).
    *   The method calls `send_command` on the device's `V1RpcChannel`.
    *   The `PickFirstAvailable` logic checks if `LocalChannel` is connected.
        *   **If Yes**: Sends via TCP.
        *   **If No**: Sends via MQTT.
4.  **Response**: The response is received, decrypted, decoded, and returned to the caller.

## Current Design Observations

*   **Complexity**: The wrapping of channels (`Device` -> `V1Channel` -> `V1RpcChannel` -> `PickFirstAvailable` -> `PayloadEncoded...` -> `Mqtt/LocalChannel`) is deep.
*   **State Management**: Synchronization between the global MQTT session and individual device local connections is handled within `V1Channel`.
*   **Protocol Versions**: Distinct logic paths exist for V1, A01, and B01 protocols, though they share the underlying MQTT transport.

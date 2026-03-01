# Roborock Device & Feature Discovery

## Goals

This document outlines the proposed improvements to the Roborock Home Assistant integration. The integration should be **fast**, **resilient**, and **dynamic**. Users should see their devices immediately upon setting up the integration, even if some devices are currently offline. The system should adapt to account changes (adding/removing devices) without requiring a restart.

## Current Challenges

- **Startup Latency:** The integration currently waits for *all* devices to connect and complete their initial data refresh before the integration is considered "ready". A single slow connection delays the entire platform.
- **Resilience Issues:** If a device is offline during startup, it may not be created in Home Assistant at all, or worse, can cause the integration setup to fail when all devices are offline (temporarily or otherwise).
- **Manual Management:** Changes to the user's account (adding a new vacuum, removing an old one) are not reflected until Home Assistant is manually restarted. There is also a bug with the initial version of the cache implementation since it never refreshes.
- **Coupled Availability & Discovery:** Currently, the integration performs a liveness check during setup (`async_setup`). If a device is offline, setup fails because we rely on that initial successful poll to determine *which* entities to create. We cannot create "Unavailable" entities because without the poll, we don't know what features the device supports.
- **Resource Waste:** We currently automatically connect to *every* discovered device. If a user has disabled a device in Home Assistant, we still maintain an active connection to it.

## Requirements Summary

| Scenario | Current Behavior | Proposed Behavior |
| :--- | :--- | :--- |
| **Startup** | Waits for all devices to refresh. | Starts immediately after getting device list. |
| **Offline Device** | May cause setup failure or missing entities. | Device and entities are created as "Unavailable". |
| **Unknown Device** | Might crash or fail integration setup. | Gracefully handled using basic generic traits. |
| **New Device** | Requires HA Restart. | Automatically added in the background. |

## Proposal Overview

### 1. Fast & Resilient Startup

We're moving from a model where we wait for all devices to be online to one where we load the device list and then listen for changes.

#### How it works:
1.  **Account Load (Cache First)**:
    - On startup, the `DeviceManager` loads the device list (`HomeData`) from its local cache.
    - **Result**: The integration setup finishes in milliseconds.
2.  **Device Setup (Lazy Loading)**:
    - We iterate through the cached list and create a Home Assistant device and coordinator for *every item*.
    - Entities are created immediately. If we don't have data yet, they show as **"Unavailable"**.
    - **Result**: The device is registered and visible in the UI immediately.
3.  **Connection & Recovery (Background)**:
    - In the background, `DeviceManager` works to establish MQTT/Local connections.
    - As devices come online, the `DeviceListener` triggers updates, and entities become "Available".
    - A background job periodically refreshes `HomeData` from the cloud to catch new devices or removals.
#### Why this solves our problems:
- **Zero Latency**: Startup time is constant, not proportional to device count or network speed.
- **Offline Persistence**: Offline devices remain in the UI (as Unavailable), so users can troubleshoot instead of wondering where they went.
- **Cloud Resilience**: If the Roborock Cloud is down, the local integration still boots using cached credentials and maps.

---

### 2. Entity Discovery

To verify a device is supported, we'll need to move to the model of checking device features, or only relying on the product information `HomeData` instead of waiting for a live response.

#### Entity Registration
- **Current Model**: We try to communicate with the device. If it fails, we don't know what sensors to create, so we create nothing.
- **Proposed Model**: We check the account metadata or cached device features, and create the corresponding sensors immediately.

#### Implementation: Trait Mapping & Cache Bridging
1.  **Static Mapping**: Where possible, we use existing product data (like protocol version or model) to determine features.
2.  **Cache Bridging**: If a device is too complex for static mapping (like some V1 vacuums), we use the cache.
    - *Run 1*: Connect live, discover features, save them to cache.
    - *Run 2+*: Load features from cache. Setup is instant.
3.  **Lazy Attributes**: Entities are created based on this metadata, not on whether the device has sent a value yet.

Question: Can existing device features be used confidently now? We likely need to either accelerate adopting this, or create placeholder device features based on previous device state state (e.g. fetch "Device prop" traits once, then decide if a feature is supported)

Alternative: As a temporary measure, we could continue to ensure v1 coordinator devices are refreshed on startup so that they have a valid `coordinator.data`. Given this is not the long term direction we're moving, I propose not to do this.

### 3. Background device discovery

Since we no longer block on startup, we treat account changes as a stream of events:
- **Auto-Discovery**: New devices in the background data refresh are added dynamically.
- **Orphan Removal**: Devices removed from the account are cleaned up automatically.

## Detail: Device Lifecycle & States

To support "Lazy Loading" properly, we must distinguish between *knowing* a device exists and *communicating* with it.

| State | Definition | Source | API Action | HA State |
| :--- | :--- | :--- | :--- | :--- |
| **Discovered** | Device exists in `HomeData`. | Cloud/Cache | `DeviceManager` creates object. | N/A |
| **Mapped (Ready)**| Capabilities are known. | Static Map / Cache | Fire `device_ready` callback. | **Entities Created** (Unavailable) |
| **Connected** | Active connection established. | MQTT/Local | Coordinator update. | **Available** |

### Clarification on `device_ready`

In this new model, `device_ready` means **"Ready for Instantiation"**, not "Ready for Interaction".
- It fires as soon as we reach the **Mapped** state.
- It does *not* wait for the **Connected** state.

The device will manage its own connection state in the background depending on the protocol.

## Work Plan: Implementation TL;DR

### 1. `DeviceManager` Changes
- Update `discover_devices` to instantiate devices but **do not await** the connection tasks.
    - *Rationale*: A timeout or connection failure is a *device state*, not a discovery failure. Once we get the list (from cache or cloud), discovery is successful.
- Update `DeviceManager` to optionally *not* auto-connect. The Home Assistant Coordinator will be responsible for calling `start_connect()` so that disabled devices remain disconnected.
- Ensure `device_ready` callbacks fire once feature discovery completes even if the initial connection fails
- Add a periodic task to re-run `discover_devices` every N minutes to fetch fresh `HomeData`.

### 2. Feature Definitions
- Expand `device_features` to cover more V1 features explicitly (e.g. some sensors check for non-None values that may not be covered by device features)
- Going forward, new protocols will need to follow this model as well of having a separate way to specify what features are supported vs the values provided by the device.

### 3. Home Assistant Changes
- Integration setup: Change to non-blocking. Return `True` as soon as `DeviceManager` is initialized with cached data or from the API.
- Platform setup: Update `sensor.py`, `binary_sensor.py`, etc., to check `device_features` instead of `coordinator.data` (State) for entity creation.

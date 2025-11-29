# GitHub Copilot Instructions for python-roborock

This document provides context and guidelines for GitHub Copilot to generate high-quality code for the `python-roborock` project.

## Project Overview

`python-roborock` is an asynchronous Python library for controlling Roborock vacuum cleaners. It supports communicating with devices via both Roborock's Cloud (MQTT) and local network (TCP) protocols.

## Key Documentation

*   **Architecture Design**: `roborock/devices/DESIGN.md` - Detailed explanation of the system architecture, communication channels, and protocol details.
*   **Device Discovery**: `roborock/devices/README.md` - Information about the device discovery lifecycle, login, and home data.

## Tech Stack

*   **Language**: Python 3.11+
*   **Async Framework**: `asyncio`
*   **Web Requests**: `aiohttp`
*   **MQTT**: `aiomqtt` (v2+)
*   **Binary Parsing**: `construct`
*   **Encryption**: `pycryptodome`
*   **Testing**: `pytest`, `pytest-asyncio`
*   **Linting/Formatting**: `ruff`

## Coding Standards

### 1. Typing
*   **Strict Typing**: All functions and methods must have type hints.
*   **Generics**: Use `list[str]` instead of `List[str]`, `dict[str, Any]` instead of `Dict[str, Any]`, etc.
*   **Optional**: Use `str | None` instead of `Optional[str]`.

### 2. Asynchronous Programming
*   **Async/Await**: Use `async def` and `await` for all I/O bound operations.
*   **Context Managers**: Use `async with` for managing resources like network sessions and locks.
*   **Concurrency**: Use `asyncio.gather` for concurrent operations. Avoid blocking calls in async functions.

### 3. Documentation
*   **Docstrings**: Use Google-style docstrings for all modules, classes, and functions.
*   **Comments**: Comment complex logic, especially protocol parsing and encryption details.

### 4. Error Handling
*   **Base Exception**: All custom exceptions must inherit from `roborock.exceptions.RoborockException`.
*   **Specific Exceptions**: Use specific exceptions like `RoborockTimeout`, `RoborockConnectionException` where appropriate.
*   **Wrapping**: Wrap external library exceptions (e.g., `aiohttp.ClientError`, `aiomqtt.MqttError`) in `RoborockException` subclasses to provide a consistent API surface.

## Architecture & Patterns

### 1. Device Model
*   **`RoborockDevice`**: The base class for all devices.
*   **Traits**: Functionality is composed using traits (e.g., `FanSpeedTrait`, `CleaningTrait`) mixed into device classes.
*   **Discovery**: `DeviceManager` handles authentication and device discovery.

### 2. Communication Channels
*   **`Channel` Protocol**: Defines the interface for communicating with a device.
*   **`MqttChannel`**: Handles communication via the Roborock MQTT broker.
*   **`LocalChannel`**: Handles direct TCP communication with the device.
*   **`V1Channel`**: A composite channel that manages both MQTT and Local connections, implementing fallback logic.

### 3. Protocol Parsing
*   **`construct` Library**: Use `construct` structs and adapters for defining binary message formats.
*   **Encryption**: Protocol encryption (AES-ECB, AES-GCM, AES-CBC) is handled in `roborock/protocol.py` and `roborock/devices/local_channel.py`.

## Testing Guidelines

*   **Framework**: Use `pytest` with `pytest-asyncio`.
*   **Fixtures**: Use fixtures defined in `tests/conftest.py` for common setup (e.g., `mock_mqtt_client`, `mock_local_client`).
*   **Mocking**: Prefer `unittest.mock.AsyncMock` for mocking async methods.
*   **Network Isolation**: Tests should not make real network requests. Use `aioresponses` for HTTP mocking and custom mocks for MQTT/TCP.

## Data Classes & Serialization

*   **`RoborockBase`**: The base class for all data models (`roborock/data/containers.py`).
*   **Automatic Conversion**: `RoborockBase` handles the conversion between the API's camelCase JSON keys and the Python dataclass's snake_case fields.
*   **Deserialization**: Use `MyClass.from_dict(data)` to instantiate objects from API responses.
*   **Nesting**: `RoborockBase` supports nested dataclasses, lists, and enums automatically.

## Example: Adding a New Trait / Command

Functionality is organized into "Traits". To add a new command (for v1 devices), follow these steps:

1.  **Define Command**: Add the command string to the `RoborockCommand` enum in `roborock/roborock_typing.py`.
2.  **Create Data Model**: Define a dataclass inheriting from `RoborockBase` (or `RoborockValueBase` for single values) to represent the state.
3.  **Create Trait**: For v1, create a class inheriting from your data model and `V1TraitMixin`.
    *   Set the `command` class variable to your `RoborockCommand`.
    *   Add methods to perform actions using `self.rpc_channel.send_command()`.
4.  **Register Trait**: Add the trait to `PropertiesApi` in `roborock/devices/traits/v1/__init__.py`.

```python
# 1. Define Data Model
@dataclass
class SoundVolume(RoborockValueBase):
    volume: int | None = field(default=None, metadata={"roborock_value": True})

# 2. Define Trait
class SoundVolumeTrait(SoundVolume, V1TraitMixin):
    command = RoborockCommand.GET_SOUND_VOLUME

    async def set_volume(self, volume: int) -> None:
        # 3. Send Command
        await self.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params=[volume])
        # Optimistic update
        self.volume = volume
```

## Example: Error Handling

```python
from roborock.exceptions import RoborockException, RoborockTimeout

async def my_operation(self) -> None:
    try:
        await self._channel.send_command("some_command")
    except TimeoutError as err:
        raise RoborockTimeout("Operation timed out") from err
    except Exception as err:
        raise RoborockException(f"Operation failed: {err}") from err
```

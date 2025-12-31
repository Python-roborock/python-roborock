"""Module for sending device specific commands to Roborock devices.

This module provides a application-level interface for sending commands to Roborock
devices. These modules can be used by traits (higher level APIs) to send commands.

Each module may contain details that are common across all traits, and may depend
on the transport level modules (e.g. MQTT, Local device) for issuing the
commands.

The lowest level protocol encoding is handled in `roborock.protocols` which
have no dependencies on the transport level modules.
"""

__all__: list[str] = []

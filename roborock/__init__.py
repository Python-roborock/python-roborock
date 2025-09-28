"""Roborock API.

.. include:: ../README.md
"""

from roborock.b01_containers import *
from roborock.code_mappings import *
from roborock.containers import *
from roborock.exceptions import *
from roborock.roborock_typing import *

from . import (
    b01_containers,
    clean_modes,
    cloud_api,
    code_mappings,
    const,
    containers,
    exceptions,
    roborock_typing,
    version_1_apis,
    version_a01_apis,
    web_api,
)

__all__ = [
    "web_api",
    "version_1_apis",
    "version_a01_apis",
    "containers",
    "b01_containers",
    "const",
    "cloud_api",
    "clean_modes",
    "code_mappings",
    "roborock_typing",
    "exceptions",
    # Add new APIs here in the future when they are public e.g. devices/
]

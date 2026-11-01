"""Roborock cloud REST API clients.

The public entry points are :class:`RoborockApiClient` and :class:`UserWebApiClient`.
Endpoints are grouped by resource into submodules (``auth``, ``homes``, ``devices``,
``scenes``, ``jobs``, ``ota``, ``products``); each exposes a mixin that
``RoborockApiClient`` composes. Everything that was importable from the former
``roborock.web_api`` module is re-exported here for backwards compatibility.
"""

# Modules and the logger the former single-file module exposed. Re-exported so that
# existing patch targets such as ``roborock.web_api.time.time`` keep resolving.
import base64
import hashlib
import hmac
import json
import math
import secrets
import string
import time

import aiohttp

from ._base import _LOGGER, BASE_URLS, IotLoginInfo, RoborockApiBase
from ._hawk import _compact_json, _get_hawk_authentication, _process_extra_hawk_values
from ._request import PreparedRequest
from .auth import DEFAULT_AGREEMENT_MAJOR_VERSION, DEFAULT_AGREEMENT_MINOR_VERSION, AuthApi
from .client import RoborockApiClient, UserWebApiClient
from .devices import DevicesApi
from .homes import HomesApi
from .jobs import JobsApi
from .ota import OtaApi
from .products import ProductsApi
from .scenes import ScenesApi

__all__ = [
    "BASE_URLS",
    "DEFAULT_AGREEMENT_MAJOR_VERSION",
    "DEFAULT_AGREEMENT_MINOR_VERSION",
    "AuthApi",
    "DevicesApi",
    "HomesApi",
    "IotLoginInfo",
    "JobsApi",
    "OtaApi",
    "PreparedRequest",
    "ProductsApi",
    "RoborockApiBase",
    "RoborockApiClient",
    "ScenesApi",
    "UserWebApiClient",
]

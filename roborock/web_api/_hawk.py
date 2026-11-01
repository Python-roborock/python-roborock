"""Hawk request signing for the RRIoT (``user_data.rriot.r.a``) API surface."""

import base64
import hashlib
import hmac
import json
import math
import secrets
import time

from roborock.data import RRiot


def _process_extra_hawk_values(values: dict | None) -> str:
    if values is None:
        return ""
    else:
        sorted_keys = sorted(values.keys())
        result = []
        for key in sorted_keys:
            value = values.get(key)
            result.append(f"{key}={value}")
        return hashlib.md5("&".join(result).encode()).hexdigest()


def _compact_json(body: dict) -> str:
    """Serialize a JSON body to the exact compact bytes that are both signed and sent."""
    return json.dumps(body, separators=(",", ":"))


def _get_hawk_authentication(
    rriot: RRiot,
    url: str,
    formdata: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
) -> str:
    timestamp = math.floor(time.time())
    nonce = secrets.token_urlsafe(6)
    params_str = _process_extra_hawk_values(params)
    if body is not None:
        payload_str = hashlib.md5(_compact_json(body).encode()).hexdigest()
    else:
        payload_str = _process_extra_hawk_values(formdata)

    prestr = ":".join(
        [
            rriot.u,
            rriot.s,
            nonce,
            str(timestamp),
            hashlib.md5(url.encode()).hexdigest(),
            params_str,
            payload_str,
        ]
    )
    mac = base64.b64encode(hmac.new(rriot.h.encode(), prestr.encode(), hashlib.sha256).digest()).decode()
    return f'Hawk id="{rriot.u}",s="{rriot.s}",ts="{timestamp}",nonce="{nonce}",mac="{mac}"'

import json
from dataclasses import replace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.a01 import DyadApi, ZeoApi, create
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol
from roborock.testing.a01_simulator import (
    DEFAULT_DYAD_DEVICE_INFO,
    DEFAULT_DYAD_PRODUCT,
    DEFAULT_ZEO_DEVICE_INFO,
    DEFAULT_ZEO_PRODUCT,
)


@pytest.fixture
def mock_channel():
    channel = Mock()
    channel.send_command = AsyncMock()
    return channel


@pytest.mark.asyncio
async def test_dyad_query_values(mock_channel):
    with patch("roborock.devices.traits.a01.send_decoded_command", new_callable=AsyncMock) as mock_send:
        api = DyadApi(mock_channel)

        # Setup mock return value (raw values)
        mock_send.return_value = {
            int(RoborockDyadDataProtocol.CLEAN_MODE): 1,
            int(RoborockDyadDataProtocol.POWER): 100,
        }

        protocols = [RoborockDyadDataProtocol.CLEAN_MODE, RoborockDyadDataProtocol.POWER]
        result = await api.query_values(protocols)

        # Verify conversion
        assert RoborockDyadDataProtocol.CLEAN_MODE in result
        assert RoborockDyadDataProtocol.POWER in result

        assert isinstance(result[RoborockDyadDataProtocol.CLEAN_MODE], str)
        assert result[RoborockDyadDataProtocol.POWER] == 100


@pytest.mark.asyncio
async def test_zeo_query_values(mock_channel):
    with patch("roborock.devices.traits.a01.send_decoded_command", new_callable=AsyncMock) as mock_send:
        api = ZeoApi(mock_channel)

        mock_send.return_value = {
            int(RoborockZeoProtocol.STATE): 6,  # spinning
            int(RoborockZeoProtocol.COUNTDOWN): 120,
        }

        protocols = [RoborockZeoProtocol.STATE, RoborockZeoProtocol.COUNTDOWN]
        result = await api.query_values(protocols)

        assert RoborockZeoProtocol.STATE in result
        assert result[RoborockZeoProtocol.STATE] == "spinning"
        assert result[RoborockZeoProtocol.COUNTDOWN] == 120


DYAD_PRODUCT_INFO_JSON = json.dumps(
    {
        "sn": "TESTSERIAL",
        "ssid": "test-network",
        "timezone": "Europe/Warsaw",
        "posix_timezone": "CET-1CEST,M3.5.0/2,M10.5.0/3",
        "ip": "192.0.2.1",
        "mac": "00:00:5e:00:53:01",
        "oba": {"bom": "A.01"},
    }
)


@pytest.mark.parametrize(
    ("product", "device_info", "device_status", "expected_traits"),
    [
        (
            DEFAULT_DYAD_PRODUCT,
            DEFAULT_DYAD_DEVICE_INFO,
            {"201": 3, "10005": DYAD_PRODUCT_INFO_JSON},
            {"status": "charging", "product_info": {"timezone": "Europe/Warsaw"}},
        ),
        (
            DEFAULT_ZEO_PRODUCT,
            DEFAULT_ZEO_DEVICE_INFO,
            {"203": 1, "217": 5},
            {"state": "standby", "countdown": 5},
        ),
    ],
    ids=["dyad", "zeo"],
)
def test_a01_diagnostic_data_includes_redacted_traits(
    mock_channel, product, device_info, device_status, expected_traits
):
    """A01 diagnostics report the decoded state without identifiers."""
    device = RoborockDevice(
        device_info=replace(device_info, device_status=device_status),
        product=product,
        channel=AsyncMock(),
        trait=create(product, mock_channel, device_status=device_status),
    )

    diagnostics = device.diagnostic_data()

    dumped = json.dumps(diagnostics)
    for private_value in ("TESTSERIAL", "test-network", "192.0.2.1", "00:00:5e:00:53:01"):
        assert private_value not in dumped
    traits = diagnostics["traits"]
    for name, expected in expected_traits.items():
        if isinstance(expected, dict):
            assert expected.items() <= traits[name].items()
        else:
            assert traits[name] == expected

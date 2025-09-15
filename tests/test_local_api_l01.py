import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from roborock.containers import DeviceData, HomeDataDevice
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.version_1_apis.roborock_local_client_v1 import RoborockLocalClientV1


@pytest.fixture
def device_data():
    """Return a default device data."""
    home_data_device = HomeDataDevice(
        duid="test_duid",
        name="Test Device",
        local_key="b8Hj5mFk3QzT7rLp",
        fv="1.0",
        product_id="roborock.vacuum.a15",
    )
    return DeviceData(
        device=home_data_device,
        model="roborock.vacuum.a15",
        host="127.0.0.1",
    )


class TestRoborockLocalApiL01:
    """Test the L01 local API."""

    @pytest.mark.asyncio
    async def test_l01_handshake_fallback(self, device_data):
        """Test the L01 handshake fallback mechanism."""
        client = RoborockLocalClientV1(device_data)

        l01_response = RoborockMessage(
            protocol=RoborockMessageProtocol.HELLO_RESPONSE,
            version=b"L01",
            seq=1,
            random=485592656,
        )

        with patch.object(client, "_send_message", side_effect=[RoborockException, l01_response]) as mock_send_message:
            await client.hello()
            assert client._version == "L01"
            assert client._ack_nonce == 485592656
            assert mock_send_message.call_count == 2
            # first call with 1.0
            args, kwargs = mock_send_message.call_args_list[0]
            roborock_message = kwargs["roborock_message"]
            assert roborock_message.version == b"1.0"
            # second call with L01
            args, kwargs = mock_send_message.call_args_list[1]
            roborock_message = kwargs["roborock_message"]
            assert roborock_message.version == b"L01"

    @pytest.mark.asyncio
    async def test_l01_send_command(self, device_data):
        """Test sending a command over L01 protocol."""
        client = RoborockLocalClientV1(device_data, version="L01")
        client._connect_nonce = 893563
        client._ack_nonce = 485592656
        client._reinitialize_encoder_decoder()
        client.transport = MagicMock()

        response_payload = {"dps": {"102": json.dumps({"id": 12345, "result": "ok", "exe_time": 100})}}
        response_message = RoborockMessage(
            protocol=RoborockMessageProtocol.GENERAL_REQUEST,
            payload=json.dumps(response_payload).encode("utf-8"),
            seq=12345,
        )

        async def send_and_receive():
            result = await client._send_command("set_custom_mode", [101])
            assert result == "ok"

        async def feed_response():
            await asyncio.sleep(0.1)
            client.on_message_received([response_message])

        with patch("roborock.version_1_apis.roborock_local_client_v1.get_next_int", return_value=12345):
            await asyncio.gather(send_and_receive(), feed_response())

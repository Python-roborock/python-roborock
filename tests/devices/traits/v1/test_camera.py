"""Tests for camera commands through the V1 trait channel."""

import base64
import json
from unittest.mock import AsyncMock

import pytest

from roborock.data import HomeDataDevice
from roborock.data.camera import CameraQuality, CameraSdpDescription, CameraTurnServer
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.camera import CameraTrait
from roborock.exceptions import RoborockException, RoborockParsingException, RoborockTimeout
from roborock.protocols.camera_signaling import parse_ice_candidate
from roborock.roborock_typing import RoborockCommand
from tests import mock_data


@pytest.fixture
def camera(mock_rpc_channel: AsyncMock) -> CameraTrait:
    """Use the shared mocked V1 channel."""
    trait = CameraTrait()
    trait._rpc_channel = mock_rpc_channel
    mock_rpc_channel.send_command.return_value = ["ok"]
    return trait


@pytest.mark.parametrize(
    ("device_info", "supported"),
    [
        (mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_s5e.json"][0], False),
        (mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"][0], True),
    ],
)
async def test_camera_discovery(
    device: RoborockDevice,
    mock_mqtt_rpc_channel: AsyncMock,
    device_info: HomeDataDevice,
    supported: bool,
    discover_features_fixture: None,
) -> None:
    """Feature discovery exposes camera commands only when video is supported."""
    assert device.v1_properties is not None
    assert (device.v1_properties.camera is not None) is supported
    if supported:
        assert device.v1_properties.camera is not None
        mock_mqtt_rpc_channel.send_command.return_value = ["ok"]
        await device.v1_properties.camera.stop_preview()
        mock_mqtt_rpc_channel.send_command.assert_called_once_with(RoborockCommand.STOP_CAMERA_PREVIEW, params=None)


async def test_start_preview(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    await camera.start_preview("viewer-id", "1234", CameraQuality.SD)
    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.START_CAMERA_PREVIEW,
        params={"client_id": "viewer-id", "password": "81dc9bdb52d04dc20036dbd8313ed055", "quality": "SD"},
    )


async def test_check_password(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    await camera.check_password("1234")
    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.CHECK_HOMESEC_PASSWORD, params={"password": "81dc9bdb52d04dc20036dbd8313ed055"}
    )


@pytest.mark.parametrize(("client_id", "password"), [(" ", "1234"), ("viewer", "abc"), ("viewer", "")])
async def test_invalid_preview_inputs(
    camera: CameraTrait, mock_rpc_channel: AsyncMock, client_id: str, password: str
) -> None:
    with pytest.raises(ValueError):
        await camera.start_preview(client_id, password)
    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize("quality", list(CameraQuality))
async def test_set_quality(camera: CameraTrait, mock_rpc_channel: AsyncMock, quality: CameraQuality) -> None:
    await camera.set_quality(quality)
    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SWITCH_VIDEO_QUALITY, params={"quality": quality.value}
    )


@pytest.mark.parametrize(
    ("method", "command"),
    [
        ("stop_preview", RoborockCommand.STOP_CAMERA_PREVIEW),
        ("start_voice_chat", RoborockCommand.START_VOICE_CHAT),
        ("stop_voice_chat", RoborockCommand.STOP_VOICE_CHAT),
    ],
)
@pytest.mark.parametrize("response", [["ok"], {}])
async def test_control_commands(
    camera: CameraTrait, mock_rpc_channel: AsyncMock, method: str, command: RoborockCommand, response: object
) -> None:
    mock_rpc_channel.send_command.return_value = response
    await getattr(camera, method)()
    mock_rpc_channel.send_command.assert_called_once_with(command, params=None)


@pytest.mark.parametrize("wrapped", [False, True])
async def test_turn_server(camera: CameraTrait, mock_rpc_channel: AsyncMock, wrapped: bool) -> None:
    data = {"url": "turn:relay.example:3478", "user": "viewer", "pwd": "secret"}
    mock_rpc_channel.send_command.return_value = [data] if wrapped else data
    server = await camera.get_turn_server()
    assert server == CameraTurnServer(urls=["turn:relay.example:3478"], username="viewer", credential="secret")
    assert "secret" not in repr(server)
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_TURN_SERVER)


@pytest.mark.parametrize("response", [[], 1, {"url": "secret-invalid-url", "pwd": "secret-password"}])
async def test_turn_parse_error_is_redacted(camera: CameraTrait, mock_rpc_channel: AsyncMock, response: object) -> None:
    mock_rpc_channel.send_command.return_value = response
    with pytest.raises(RoborockParsingException) as error:
        await camera.get_turn_server()
    assert "secret" not in str(error.value)


async def test_sdp_offer(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    await camera.send_sdp_offer("v=0\r\ns=offer\r\n")
    command = mock_rpc_channel.send_command.call_args
    assert command.args == (RoborockCommand.SEND_SDP_TO_ROBOT,)
    assert json.loads(base64.b64decode(command.kwargs["params"]["app_sdp"])) == {
        "sdp": "v=0\r\ns=offer\r\n",
        "type": "offer",
    }


@pytest.mark.parametrize("wrapped", [False, True])
async def test_sdp_answer(camera: CameraTrait, mock_rpc_channel: AsyncMock, wrapped: bool) -> None:
    answer = {"dev_sdp": base64.b64encode(b'{"sdp":"v=0\\r\\n", "type":"answer"}').decode()}
    mock_rpc_channel.send_command.return_value = [answer] if wrapped else answer
    assert await camera.get_sdp_answer() == CameraSdpDescription(sdp="v=0\r\n", type="answer")


async def test_sdp_pending_does_not_poll(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    mock_rpc_channel.send_command.return_value = [{"dev_sdp": "retry"}]
    assert await camera.get_sdp_answer() is None
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DEVICE_SDP)


async def test_ice_exchange(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    candidate = parse_ice_candidate("candidate:1 1 udp 123 192.0.2.1 1234 typ host", "video", 1)
    await camera.send_ice_candidate(candidate)
    call = mock_rpc_channel.send_command.call_args
    assert call.args == (RoborockCommand.SEND_ICE_TO_ROBOT,)
    encoded = call.kwargs["params"]["app_ice"]
    assert json.loads(base64.b64decode(encoded)) == {
        "candidate": candidate.to_sdp(),
        "sdpMid": "video",
        "sdpMLineIndex": 1,
    }
    mock_rpc_channel.send_command.return_value = [{"dev_ice": [encoded]}]
    assert await camera.get_ice_candidates() == [candidate]


async def test_empty_remote_ice(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    mock_rpc_channel.send_command.return_value = {"dev_ice": []}
    assert await camera.get_ice_candidates() == []


@pytest.mark.parametrize("method", ["get_sdp_answer", "get_ice_candidates"])
@pytest.mark.parametrize("response", [123, {}, ["not-base64"]])
async def test_malformed_signaling_response(
    camera: CameraTrait, mock_rpc_channel: AsyncMock, method: str, response: object
) -> None:
    mock_rpc_channel.send_command.return_value = response
    with pytest.raises(RoborockParsingException):
        await getattr(camera, method)()


@pytest.mark.parametrize("response", [["error"], {"code": -1, "message": "secret"}, [], 0])
async def test_command_rejection(camera: CameraTrait, mock_rpc_channel: AsyncMock, response: object) -> None:
    mock_rpc_channel.send_command.return_value = response
    with pytest.raises(RoborockException, match="was not accepted") as error:
        await camera.check_password("1234")
    assert "secret" not in str(error.value)
    mock_rpc_channel.send_command.assert_called_once()


async def test_timeout_propagates_without_retry(camera: CameraTrait, mock_rpc_channel: AsyncMock) -> None:
    mock_rpc_channel.send_command.side_effect = RoborockTimeout("timeout")
    with pytest.raises(RoborockTimeout):
        await camera.check_password("1234")
    mock_rpc_channel.send_command.assert_called_once()

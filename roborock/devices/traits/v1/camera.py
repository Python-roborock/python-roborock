"""Camera control and WebRTC signaling through the existing V1 RPC channel."""

from roborock.data.camera import CameraIceCandidate, CameraQuality, CameraSdpDescription, CameraTurnServer
from roborock.exceptions import RoborockException, RoborockParsingException
from roborock.protocols.camera_signaling import (
    decode_ice_candidates,
    decode_sdp_answer,
    encode_ice_candidate,
    encode_sdp_offer,
    hash_camera_password,
)
from roborock.protocols.v1_protocol import ParamsType, V1RpcChannel
from roborock.roborock_typing import RoborockCommand


class CameraTrait:
    """Control a camera session without owning a WebRTC connection.

    Callers own session ordering, bounded SDP/ICE polling and cleanup: pair
    a successful ``start_preview`` with ``stop_preview`` in a ``finally`` block, and stop
    voice chat if started. This trait creates no tasks, listeners or sockets.
    Only one viewer can use the robot's camera at a time.
    """

    requires_feature = "is_video_monitor_supported"
    # Use one existing channel strategy so a rejected PIN is not retried via
    # local/cloud fallback. Local camera signaling can be exposed separately.
    mqtt_rpc_channel = True

    def __init__(self) -> None:
        """Initialize the trait; device discovery supplies its RPC channel."""
        self._rpc_channel: V1RpcChannel | None = None

    @property
    def rpc_channel(self) -> V1RpcChannel:
        """Return the channel supplied by the device."""
        if self._rpc_channel is None:
            raise RoborockException("Camera trait has no RPC channel")
        return self._rpc_channel

    async def check_password(self, password: str) -> None:
        """Check PIN/pattern digits, raising if rejected; never retry a bad PIN."""
        await self._send_ack(RoborockCommand.CHECK_HOMESEC_PASSWORD, {"password": hash_camera_password(password)})

    async def start_preview(self, client_id: str, password: str, quality: CameraQuality = CameraQuality.HD) -> None:
        """Start preview using PIN/pattern digits and a caller-owned session ID."""
        if not client_id.strip():
            raise ValueError("Camera client ID cannot be empty")
        await self._send_ack(
            RoborockCommand.START_CAMERA_PREVIEW,
            {"client_id": client_id, "quality": quality.value, "password": hash_camera_password(password)},
        )

    async def stop_preview(self) -> None:
        """Stop the active preview; the command is not scoped to a client ID."""
        await self._send_ack(RoborockCommand.STOP_CAMERA_PREVIEW)

    async def set_quality(self, quality: CameraQuality) -> None:
        """Switch the active preview's video quality."""
        await self._send_ack(RoborockCommand.SWITCH_VIDEO_QUALITY, {"quality": quality.value})

    async def get_turn_server(self) -> CameraTurnServer:
        """Fetch ephemeral TURN credentials without retaining them on the trait."""
        response = await self.rpc_channel.send_command(RoborockCommand.GET_TURN_SERVER)
        try:
            if not isinstance(response, dict | list):
                raise TypeError("Expected a TURN response object or list")
            return CameraTurnServer.from_dict(response)
        except (TypeError, ValueError):
            # TURN parser errors may include credentials or URLs supplied by firmware.
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=RoborockCommand.GET_TURN_SERVER,
                payload={"type": type(response).__name__},
                inner_error="Invalid TURN server response",
            ) from None

    async def send_sdp_offer(self, sdp: str) -> None:
        """Send an SDP offer, preserving its line endings."""
        await self._send_ack(RoborockCommand.SEND_SDP_TO_ROBOT, {"app_sdp": encode_sdp_offer(sdp)})

    async def get_sdp_answer(self) -> CameraSdpDescription | None:
        """Fetch once; return None while the robot reports ``retry``."""
        response = await self.rpc_channel.send_command(RoborockCommand.GET_DEVICE_SDP)
        if not isinstance(response, str | dict | list):
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=RoborockCommand.GET_DEVICE_SDP,
                payload={"type": type(response).__name__},
                inner_error="Expected an SDP response object, list or string",
            )
        return decode_sdp_answer(response)

    async def send_ice_candidate(self, candidate: CameraIceCandidate) -> None:
        """Send one local ICE candidate, including its media identifiers."""
        await self._send_ack(RoborockCommand.SEND_ICE_TO_ROBOT, {"app_ice": encode_ice_candidate(candidate)})

    async def get_ice_candidates(self) -> list[CameraIceCandidate]:
        """Fetch remote ICE candidates once; the caller handles deduplication."""
        response = await self.rpc_channel.send_command(RoborockCommand.GET_DEVICE_ICE)
        if not isinstance(response, str | dict | list):
            raise RoborockParsingException(
                trait_name=type(self).__name__,
                command=RoborockCommand.GET_DEVICE_ICE,
                payload={"type": type(response).__name__},
                inner_error="Expected an ICE response object, list or string",
            )
        return decode_ice_candidates(response)

    async def start_voice_chat(self) -> None:
        """Enable the robot's microphone for the active WebRTC session."""
        await self._send_ack(RoborockCommand.START_VOICE_CHAT)

    async def stop_voice_chat(self) -> None:
        """Stop voice chat for the active session."""
        await self._send_ack(RoborockCommand.STOP_VOICE_CHAT)

    async def _send_ack(self, command: RoborockCommand, params: ParamsType = None) -> None:
        response = await self.rpc_channel.send_command(command, params=params)
        # decode_rpc_response normalizes a bare "ok" to {}; other firmware
        # sends ["ok"]. Do not treat arbitrary result dictionaries as success.
        if response not in ({}, ["ok"]):
            raise RoborockException(f"Camera command {command.value} was not accepted")

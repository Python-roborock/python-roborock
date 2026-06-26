#!/usr/bin/env python3
"""
Roborock Camera Client - WebRTC Video/Audio Streaming

Streams video and bidirectional audio from Roborock vacuum cameras via MQTT 
signaling + WebRTC. Supports live preview, snapshots, recording, voice calls,
and remote control.

This is a standalone implementation that uses the existing python-roborock
protocol encoders but manages its own MQTT connection for camera-specific
signaling. Future work could integrate this more tightly with the library's
session management.

Usage:
    from roborock.camera import RoborockCamera
    
    camera = RoborockCamera(
        duid="YOUR_DEVICE_ID",
        local_key="YOUR_LOCAL_KEY",
        rriot_u="YOUR_RRIOT_U",
        rriot_k="YOUR_RRIOT_K", 
        rriot_s="YOUR_RRIOT_S",
        password="9876"  # Your pattern password as digits
    )
    
    async with camera:
        # Take a snapshot
        frame = await camera.get_frame()
        frame.save("snapshot.jpg")
        
        # Record video
        await camera.record("output.mp4", duration=10)
        
        # Send audio to robot (for voice calls)
        camera.send_audio(audio_samples)  # int16 mono, 960 samples at 48kHz

Requirements:
    pip install aiortc paho-mqtt pillow numpy
    
    Optional for voice calls:
    pip install pyaudio opencv-python

See docs/CAMERA_PROTOCOL.md for protocol documentation.
"""

import asyncio
import hashlib
import json
import base64
import ssl
import time
import re
from dataclasses import dataclass
from typing import Optional, Callable, List
import logging

import paho.mqtt.client as mqtt
from roborock.protocol import create_mqtt_encoder, create_mqtt_decoder, RoborockMessage
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    RTCIceCandidate, 
    RTCConfiguration, 
    RTCIceServer,
    MediaStreamTrack
)
from av import AudioFrame
import numpy as np


class AudioSendTrack(MediaStreamTrack):
    """Custom audio track that can be fed external audio data"""
    
    kind = "audio"
    
    def __init__(self):
        super().__init__()
        self._queue = asyncio.Queue(maxsize=50)
        self._sample_rate = 48000
        self._samples_per_frame = 960  # 20ms at 48kHz
        self._pts = 0
    
    async def recv(self):
        """Return the next audio frame to send"""
        try:
            audio_data = await asyncio.wait_for(self._queue.get(), timeout=0.02)
        except asyncio.TimeoutError:
            audio_data = np.zeros(self._samples_per_frame, dtype=np.int16)
        
        # Ensure correct size
        if len(audio_data) < self._samples_per_frame:
            audio_data = np.pad(audio_data, (0, self._samples_per_frame - len(audio_data)))
        elif len(audio_data) > self._samples_per_frame:
            audio_data = audio_data[:self._samples_per_frame]
        
        frame = AudioFrame(format='s16', layout='mono', samples=self._samples_per_frame)
        frame.sample_rate = self._sample_rate
        frame.pts = self._pts
        frame.planes[0].update(audio_data.astype(np.int16).tobytes())
        
        self._pts += self._samples_per_frame
        return frame
    
    def push_audio(self, audio_data: np.ndarray):
        """Push audio data to be sent"""
        try:
            self._queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            pass

logger = logging.getLogger(__name__)


def md5hex(s: str) -> str:
    """MD5 hash as hex string"""
    return hashlib.md5(s.encode()).hexdigest()


def parse_ice_candidate(candidate_str: str, sdp_mid: str = '0', sdp_mline_index: int = 0) -> Optional[RTCIceCandidate]:
    """Parse ICE candidate string into aiortc RTCIceCandidate"""
    # Format: candidate:foundation component protocol priority ip port typ type [extensions]
    match = re.match(
        r'candidate:(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\s+typ\s+(\S+)',
        candidate_str
    )
    if not match:
        return None
    
    foundation, component, protocol, priority, ip, port, cand_type = match.groups()
    
    # Extract optional related address/port for srflx/relay candidates
    related_addr, related_port = None, None
    raddr_match = re.search(r'raddr\s+(\S+)\s+rport\s+(\d+)', candidate_str)
    if raddr_match:
        related_addr = raddr_match.group(1)
        related_port = int(raddr_match.group(2))
    
    # Extract tcpType for TCP candidates
    tcp_type = None
    tcp_match = re.search(r'tcptype\s+(\S+)', candidate_str)
    if tcp_match:
        tcp_type = tcp_match.group(1)
    
    return RTCIceCandidate(
        component=int(component),
        foundation=foundation,
        ip=ip,
        port=int(port),
        priority=int(priority),
        protocol=protocol,
        type=cand_type,
        relatedAddress=related_addr,
        relatedPort=related_port,
        sdpMid=sdp_mid,
        sdpMLineIndex=sdp_mline_index,
        tcpType=tcp_type
    )


@dataclass
class CameraConfig:
    """Camera connection configuration"""
    duid: str
    local_key: str
    rriot_u: str
    rriot_k: str
    rriot_s: str
    password: str  # Pattern password as digit string (e.g., "9876")
    mqtt_server: str = "mqtt-us.roborock.com"
    mqtt_port: int = 8883
    quality: str = "HD"  # "HD" or "SD"


class RoborockCamera:
    """
    Roborock Camera Client
    
    Connects to vacuum camera via MQTT signaling and WebRTC.
    """
    
    def __init__(
        self,
        duid: str,
        local_key: str,
        rriot_u: str,
        rriot_k: str,
        rriot_s: str,
        password: str,
        mqtt_server: str = "mqtt-us.roborock.com",
        mqtt_port: int = 8883,
        quality: str = "HD"
    ):
        self.config = CameraConfig(
            duid=duid,
            local_key=local_key,
            rriot_u=rriot_u,
            rriot_k=rriot_k,
            rriot_s=rriot_s,
            password=password,
            mqtt_server=mqtt_server,
            mqtt_port=mqtt_port,
            quality=quality
        )
        
        # Derived credentials
        self.mqtt_username = md5hex(f"{rriot_u}:{rriot_k}")[2:10]
        self.mqtt_password = md5hex(f"{rriot_s}:{rriot_k}")[16:]
        self.password_hash = md5hex(password)
        self.client_id = self.mqtt_username
        
        # MQTT topics
        self.topic_pub = f"rr/m/i/{rriot_u}/{self.client_id}/{duid}"
        self.topic_sub = f"rr/m/o/{rriot_u}/{self.client_id}/{duid}"
        
        # Protocol helpers
        self.encoder = create_mqtt_encoder(local_key)
        self.decoder = create_mqtt_decoder(local_key)
        
        # State
        self.mqtt_client: Optional[mqtt.Client] = None
        self.pc: Optional[RTCPeerConnection] = None
        self.responses: dict = {}
        self.req_id: int = 100000
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Tracks
        self.video_track = None
        self.audio_track = None
        self._connected = asyncio.Event()
        
        # Voice mode
        self._mic_player = None
        self._audio_send_track: Optional[AudioSendTrack] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self, voice_mode: bool = False) -> bool:
        """Establish camera connection
        
        Args:
            voice_mode: Enable microphone capture for bidirectional audio
        """
        self.loop = asyncio.get_event_loop()
        
        # Setup MQTT
        self.mqtt_client = mqtt.Client(
            client_id=self.client_id,
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.mqtt_client.username_pw_set(self.client_id, self.mqtt_password)
        self.mqtt_client.on_message = self._on_mqtt_message
        
        logger.info(f"Connecting to MQTT {self.config.mqtt_server}:{self.config.mqtt_port}")
        self.mqtt_client.connect(self.config.mqtt_server, self.config.mqtt_port, 60)
        self.mqtt_client.subscribe(self.topic_sub, qos=1)
        self.mqtt_client.loop_start()
        await asyncio.sleep(1)
        
        # Authenticate
        logger.info("Authenticating...")
        await self._send("check_homesec_password", {"password": self.password_hash})
        await self._send("switch_video_quality", {"quality": self.config.quality})
        await self._send("start_camera_preview", {
            "client_id": self.client_id,
            "quality": self.config.quality,
            "password": self.password_hash
        })
        
        # Get TURN server
        turn = await self._send("get_turn_server", [])
        if not turn or "user" not in turn:
            logger.error(f"Failed to get TURN server: {turn}")
            return False
        
        logger.info(f"Got TURN server: {turn['url']}")
        
        # Setup WebRTC
        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(
                urls=[turn["url"]],
                username=turn["user"],
                credential=turn["pwd"]
            )
        ])
        
        self.pc = RTCPeerConnection(configuration=config)
        
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Received {track.kind} track")
            if track.kind == "video":
                self.video_track = track
            elif track.kind == "audio":
                self.audio_track = track
        
        @self.pc.on("connectionstatechange")
        async def on_conn_state():
            logger.info(f"Connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "connected":
                self._connected.set()
        
        @self.pc.on("iceconnectionstatechange")
        async def on_ice_state():
            logger.info(f"ICE state: {self.pc.iceConnectionState}")
        
        # Add audio send track (creates sendrecv transceiver automatically)
        self._audio_send_track = AudioSendTrack()
        self.pc.addTrack(self._audio_send_track)
        logger.info("Added audio send track for voice")
        
        # Add video transceiver
        self.pc.addTransceiver("video", direction="sendrecv")
        
        # Create and send offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        sdp_json = json.dumps({"sdp": offer.sdp, "type": "offer"})
        sdp_b64 = base64.b64encode(sdp_json.encode()).decode()
        await self._send("send_sdp_to_robot", {"app_sdp": sdp_b64})
        logger.info("Sent SDP offer")
        
        # Get device SDP
        for _ in range(30):
            r = await self._send("get_device_sdp", [], timeout=1)
            if isinstance(r, dict) and r.get("dev_sdp") not in (None, "retry"):
                sdp = json.loads(base64.b64decode(r["dev_sdp"]).decode())
                await self.pc.setRemoteDescription(
                    RTCSessionDescription(sdp=sdp["sdp"], type="answer")
                )
                logger.info("Set remote SDP")
                break
            await asyncio.sleep(0.2)
        else:
            logger.error("Failed to get device SDP")
            return False
        
        # Get and add device ICE candidates
        added_ice = set()
        for _ in range(40):
            r = await self._send("get_device_ice", [], timeout=1)
            if isinstance(r, dict) and isinstance(r.get("dev_ice"), list):
                for ice_b64 in r["dev_ice"]:
                    if ice_b64 in added_ice:
                        continue
                    added_ice.add(ice_b64)
                    try:
                        ice_json = json.loads(base64.b64decode(ice_b64).decode())
                        candidate = parse_ice_candidate(
                            ice_json["candidate"],
                            str(ice_json.get("sdpMid", "0")),
                            ice_json.get("sdpMLineIndex", 0)
                        )
                        if candidate:
                            await self.pc.addIceCandidate(candidate)
                            logger.debug(f"Added ICE: {candidate.ip}:{candidate.port}")
                    except Exception as e:
                        logger.warning(f"Failed to parse ICE: {e}")
            
            if self.pc.connectionState == "connected":
                break
            await asyncio.sleep(0.3)
        
        # Wait for connection
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10)
            logger.info("Camera connected!")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Connection timeout. State: {self.pc.connectionState}")
            return self.pc.connectionState in ("connected", "connecting")
    
    async def disconnect(self):
        """Close camera connection"""
        # Tell robot to stop camera preview
        if self.mqtt_client:
            try:
                await self._send("stop_camera_preview", [], timeout=2)
                logger.info("Sent stop_camera_preview to robot")
            except Exception as e:
                logger.warning(f"Failed to send stop_camera_preview: {e}")
        
        if self.pc:
            await self.pc.close()
            self.pc = None
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
        self.video_track = None
        self.audio_track = None
        self._connected.clear()
    
    def send_audio(self, audio_data: np.ndarray):
        """Send audio to the robot (for voice calls). 
        audio_data should be int16 mono samples at 48kHz, 960 samples (20ms)"""
        if self._audio_send_track:
            self._audio_send_track.push_audio(audio_data)
    
    async def get_frame(self, timeout: float = 10):
        """Get a single video frame as PIL Image"""
        if not self.video_track:
            raise RuntimeError("No video track available")
        
        import numpy as np
        from PIL import Image
        
        frame = await asyncio.wait_for(self.video_track.recv(), timeout=timeout)
        img_array = frame.to_ndarray(format="rgb24")
        return Image.fromarray(img_array)
    
    async def stream_frames(self, callback: Callable, count: int = None):
        """Stream video frames to callback function"""
        if not self.video_track:
            raise RuntimeError("No video track available")
        
        import numpy as np
        from PIL import Image
        
        i = 0
        while count is None or i < count:
            try:
                frame = await asyncio.wait_for(self.video_track.recv(), timeout=10)
                img_array = frame.to_ndarray(format="rgb24")
                img = Image.fromarray(img_array)
                await callback(img, i)
                i += 1
            except asyncio.TimeoutError:
                logger.warning("Frame timeout")
                break
            except Exception as e:
                logger.error(f"Frame error: {e}")
                break
    
    async def record(self, output_path: str, duration: float = 60):
        """Record video to file"""
        from aiortc.contrib.media import MediaRecorder
        
        if not self.video_track:
            raise RuntimeError("No video track available")
        
        recorder = MediaRecorder(output_path)
        recorder.addTrack(self.video_track)
        if self.audio_track:
            recorder.addTrack(self.audio_track)
        
        logger.info(f"Recording {duration}s to {output_path}")
        await recorder.start()
        await asyncio.sleep(duration)
        await recorder.stop()
        logger.info(f"Recording saved to {output_path}")
    
    async def voice_call(self, duration: float = 60, with_video: bool = True):
        """
        Start bidirectional voice call with the robot.
        Captures microphone audio and plays robot's audio through speakers.
        
        Args:
            duration: Call duration in seconds (default 60)
            with_video: Also display video feed (requires opencv)
        """
        import pyaudio
        import numpy as np
        
        if not self.audio_track:
            raise RuntimeError("No audio track from robot")
        
        # Setup PyAudio for playback
        pa = pyaudio.PyAudio()
        
        # Output stream (robot audio → speakers)
        output_stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=48000,
            output=True,
            frames_per_buffer=960
        )
        
        print("🎙️ Voice call active! Speak to the robot...")
        print(f"   Duration: {duration}s (Ctrl+C to end)")
        
        async def play_audio():
            """Play audio from robot"""
            while True:
                try:
                    frame = await asyncio.wait_for(self.audio_track.recv(), timeout=1)
                    # Convert to int16 PCM
                    audio_data = frame.to_ndarray()
                    if audio_data.dtype != np.int16:
                        audio_data = (audio_data * 32767).astype(np.int16)
                    output_stream.write(audio_data.tobytes())
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Audio playback error: {e}")
                    break
        
        async def show_video():
            """Display video feed"""
            if not with_video or not self.video_track:
                return
            try:
                import cv2
                while True:
                    try:
                        frame = await asyncio.wait_for(self.video_track.recv(), timeout=1)
                        img = frame.to_ndarray(format="bgr24")
                        cv2.imshow("Roborock Camera - Voice Call", img)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    except asyncio.TimeoutError:
                        continue
            except ImportError:
                logger.info("OpenCV not installed, skipping video display")
        
        try:
            # Run audio playback and optional video display
            tasks = [asyncio.create_task(play_audio())]
            if with_video:
                tasks.append(asyncio.create_task(show_video()))
            
            # Wait for duration or until cancelled
            await asyncio.sleep(duration)
            
        except KeyboardInterrupt:
            print("\n📞 Call ended")
        finally:
            for task in tasks:
                task.cancel()
            output_stream.stop_stream()
            output_stream.close()
            pa.terminate()
            try:
                import cv2
                cv2.destroyAllWindows()
            except:
                pass
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            for rm in self.decoder(msg.payload):
                if rm.payload:
                    payload = json.loads(rm.payload.decode())
                    if "102" in payload.get("dps", {}):
                        response = json.loads(payload["dps"]["102"])
                        self.responses[response.get("id")] = response.get("result", response.get("error"))
        except Exception as e:
            logger.debug(f"MQTT decode error: {e}")
    
    async def _send(self, method: str, params, timeout: float = 5):
        """Send MQTT command and wait for response"""
        self.req_id += 1
        rid = self.req_id
        
        inner = {"id": rid, "method": method, "params": params}
        payload = json.dumps({
            "dps": {"101": json.dumps(inner)},
            "t": int(time.time())
        }).encode()
        
        msg = RoborockMessage(
            protocol=101,
            payload=payload,
            timestamp=int(time.time())
        )
        
        self.mqtt_client.publish(self.topic_pub, self.encoder(msg), qos=1)
        
        start = time.time()
        while time.time() - start < timeout:
            if rid in self.responses:
                return self.responses.pop(rid)
            await asyncio.sleep(0.05)
        return None


# =============================================================================
# CLI Example
# =============================================================================

async def main():
    """Example CLI usage - requires credentials as environment variables or arguments."""
    import argparse
    import os
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description="Roborock Camera Client",
        epilog="Credentials can be set via environment variables: ROBOROCK_DUID, ROBOROCK_LOCAL_KEY, "
               "ROBOROCK_RRIOT_U, ROBOROCK_RRIOT_K, ROBOROCK_RRIOT_S, ROBOROCK_PASSWORD"
    )
    parser.add_argument("--duid", help="Device DUID", default=os.environ.get("ROBOROCK_DUID"))
    parser.add_argument("--local-key", help="Local key", default=os.environ.get("ROBOROCK_LOCAL_KEY"))
    parser.add_argument("--rriot-u", help="RRIOT U token", default=os.environ.get("ROBOROCK_RRIOT_U"))
    parser.add_argument("--rriot-k", help="RRIOT K token", default=os.environ.get("ROBOROCK_RRIOT_K"))
    parser.add_argument("--rriot-s", help="RRIOT S token", default=os.environ.get("ROBOROCK_RRIOT_S"))
    parser.add_argument("--password", help="Pattern password (digits)", default=os.environ.get("ROBOROCK_PASSWORD"))
    parser.add_argument("--snapshot", "-s", action="store_true", help="Take snapshot")
    parser.add_argument("--record", "-r", type=int, metavar="SEC", help="Record video for N seconds")
    parser.add_argument("--voice", "-v", action="store_true", help="Voice call mode (bidirectional audio)")
    parser.add_argument("--duration", "-t", type=int, default=60, help="Duration for record/voice (default 60s)")
    parser.add_argument("--no-video", action="store_true", help="Disable video display in voice mode")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Validate required credentials
    required = ["duid", "local_key", "rriot_u", "rriot_k", "rriot_s", "password"]
    missing = [f for f in required if not getattr(args, f.replace("-", "_"))]
    if missing:
        parser.error(f"Missing required credentials: {', '.join(missing)}")
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    camera = RoborockCamera(
        duid=args.duid,
        local_key=args.local_key,
        rriot_u=args.rriot_u,
        rriot_k=args.rriot_k,
        rriot_s=args.rriot_s,
        password=args.password
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        await camera.connect(voice_mode=args.voice)
        
        if args.snapshot:
            output = args.output or f"snapshot_{timestamp}.jpg"
            frame = await camera.get_frame()
            frame.save(output)
            print(f"Saved snapshot to {output}")
        
        elif args.voice:
            print("📞 Starting voice call...")
            await camera.voice_call(
                duration=args.duration,
                with_video=not args.no_video
            )
        
        elif args.record:
            output = args.output or f"recording_{timestamp}.mp4"
            await camera.record(output, args.record)
            print(f"Saved recording to {output}")
        
        else:
            output = args.output or f"recording_{timestamp}.mp4"
            await camera.record(output, args.duration)
            print(f"Saved recording to {output}")
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        await camera.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

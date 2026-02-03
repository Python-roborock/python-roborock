# Roborock Camera Protocol Documentation

This document describes the protocol for streaming video/audio from Roborock vacuum cameras.

## Overview

The camera uses **MQTT for signaling** and **WebRTC for media transport**:

```
┌─────────────┐     MQTT      ┌──────────────┐
│   Client    │◄────────────►│  Roborock    │
│  (Python)   │   Signaling   │   Cloud      │
└─────────────┘               └──────────────┘
       │                             │
       │         WebRTC              │
       └─────────────────────────────┘
              Video + Audio
```

## Connection Flow

1. Connect to MQTT broker (`mqtt-{region}.roborock.com:8883`)
2. Authenticate with password hash
3. Start camera preview
4. Get TURN server credentials from Roborock cloud
5. Exchange SDP/ICE candidates via MQTT
6. Establish WebRTC peer connection
7. Receive video/audio tracks

## MQTT Topics

```
Publish:  rr/m/i/{rriot_u}/{client_id}/{duid}
Subscribe: rr/m/o/{rriot_u}/{client_id}/{duid}
```

Where:
- `rriot_u`: User identifier from Roborock account
- `client_id`: MD5-derived client identifier
- `duid`: Device unique identifier

## MQTT Credentials

```python
mqtt_username = md5(f"{rriot_u}:{rriot_k}")[2:10]
mqtt_password = md5(f"{rriot_s}:{rriot_k}")[16:]
```

## Commands

All commands are sent via protocol 101 in the `dps.101` field. Responses come in `dps.102`.

### Camera Control

| Command | Params | Response | Notes |
|---------|--------|----------|-------|
| `check_homesec_password` | `{password: md5_hash}` | `['ok']` | Authenticate with pattern password |
| `start_camera_preview` | `{client_id, quality, password}` | `['ok']` | Begin video session |
| `stop_camera_preview` | `[]` | `['ok']` | End video session |
| `switch_video_quality` | `{quality: "HD"/"SD"}` | `['ok']` | Change resolution |

### WebRTC Signaling

| Command | Params | Response | Notes |
|---------|--------|----------|-------|
| `get_turn_server` | `[]` | `{url, user, pwd}` | TURN credentials |
| `send_sdp_to_robot` | `{app_sdp: base64}` | `['ok']` | Send our SDP offer |
| `get_device_sdp` | `[]` | `{dev_sdp: base64}` or `"retry"` | Robot's SDP answer |
| `send_ice_to_robot` | `{app_ice: base64}` | `['ok']` | Send ICE candidates |
| `get_device_ice` | `[]` | `{dev_ice: [base64...]}` | Robot's ICE candidates |

### Voice Chat

| Command | Params | Response | Notes |
|---------|--------|----------|-------|
| `start_voice_chat` | `[]` | `['ok']` | Enable bidirectional audio |
| `stop_voice_chat` | `[]` | `['ok']` | Disable audio |

**Important:** Without calling `start_voice_chat`, the audio track exists but sends no frames!

### Remote Control

| Command | Params | Response | Notes |
|---------|--------|----------|-------|
| `app_rc_start` | `[]` | `['ok']` | Begin RC session |
| `app_rc_move` | `{omega, velocity, seqnum, duration}` | `['ok']` | Movement command |
| `app_rc_end` | `[]` | `['ok']` | End RC session |

RC Parameters:
- `velocity`: Forward/backward speed (±0.2 typical range)
- `omega`: Rotation speed in rad/s (±0.53 typical range)
- `seqnum`: Incrementing sequence number
- `duration`: Command duration in ms (500 typical)

## Audio Format

### Robot → Client
- **Format:** Stereo interleaved, 48kHz, 16-bit signed PCM
- **Frame size:** 960 samples per channel (20ms)
- **Raw frame:** 1920 int16 values in LRLRLR... pattern
- **To extract mono:** `audio[::2]` (take left channel)

### Client → Robot
- **Format:** Mono, 48kHz, 16-bit signed PCM
- **Frame size:** 960 samples (20ms)
- **Timing:** Send frames spaced ~18-20ms apart

## Message Format

### Request (dps.101)
```json
{
  "id": 100001,
  "method": "command_name",
  "params": {}
}
```

### Response (dps.102)
```json
{
  "id": 100001,
  "result": ["ok"]
}
```

Or on error:
```json
{
  "id": 100001,
  "error": {"code": -1, "message": "error description"}
}
```

## SDP/ICE Format

SDP and ICE candidates are base64-encoded JSON:

```python
# SDP
sdp_json = json.dumps({"sdp": sdp_string, "type": "offer"})
sdp_b64 = base64.b64encode(sdp_json.encode()).decode()

# ICE
ice_json = json.dumps({
    "candidate": "candidate:...",
    "sdpMid": "0",
    "sdpMLineIndex": 0
})
ice_b64 = base64.b64encode(ice_json.encode()).decode()
```

## Important Notes

1. **One session at a time** - Only one client can preview the camera. Close the phone app first.

2. **Password rate limiting** - Too many incorrect password attempts may disable remote viewing temporarily.

3. **TURN server required** - NAT traversal typically requires the TURN server; direct P2P connections are rare.

4. **Pattern password** - The password is your numeric pattern (e.g., "9876"), not your Roborock account password.

## Tested Devices

- Roborock Qrevo Curv (model a135)

Other camera-equipped Roborock models likely use the same protocol but are untested.

## Getting Credentials

The required credentials (`duid`, `local_key`, `rriot_u/k/s`) can be obtained from:
- Home Assistant's Roborock integration storage
- The python-roborock library's login flow
- Roborock app traffic analysis

## References

- [python-roborock](https://github.com/Python-roborock/python-roborock) - Protocol encoding/decoding
- [aiortc](https://github.com/aiortc/aiortc) - Python WebRTC implementation

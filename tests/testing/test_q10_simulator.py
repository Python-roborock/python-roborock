"""Unit tests for Q10VacuumSimulator."""

import json
from typing import Any

import pytest

from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.testing import DEFAULT_Q10_STATUS, Q10VacuumSimulator

B01_VERSION = b"B01"


@pytest.fixture(name="q10_sim")
def q10_sim_fixture() -> Q10VacuumSimulator:
    """Fixture to create a Q10VacuumSimulator instance."""
    return Q10VacuumSimulator(duid="test_q10_duid")


def test_default_status(q10_sim: Q10VacuumSimulator) -> None:
    """Test that the simulator initializes with default Q10 status."""
    assert q10_sim.status == DEFAULT_Q10_STATUS
    assert q10_sim.status[121] == 8  # Charging
    assert q10_sim.status[122] == 100  # Battery
    assert isinstance(q10_sim.status[101], dict)
    assert q10_sim.status[101][26] == 74  # Volume


async def test_request_dps(q10_sim: Q10VacuumSimulator) -> None:
    """Test that the simulator responds to REQUEST_DPS with a full status push."""
    notified_messages = []

    def mock_notify(message: RoborockMessage) -> None:
        notified_messages.append(message)

    await q10_sim.mqtt_channel.subscribe(mock_notify)

    # Send REQUEST_DPS command (102)
    req_payload: dict[str, Any] = {"dps": {"102": {}}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )

    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)

    assert len(notified_messages) == 1
    resp_msg = notified_messages[0]
    assert resp_msg.protocol == RoborockMessageProtocol.RPC_RESPONSE
    assert resp_msg.version == B01_VERSION
    assert resp_msg.payload is not None

    resp_payload = json.loads(resp_msg.payload.decode())
    assert "dps" in resp_payload
    # The response is keyed by strings representing DP integer codes
    assert resp_payload["dps"]["121"] == 8
    assert resp_payload["dps"]["122"] == 100
    # Nested dictionary 101 must also have string keys
    assert resp_payload["dps"]["101"]["26"] == 74


async def test_clean_pause_resume_stop(q10_sim: Q10VacuumSimulator) -> None:
    """Test clean, pause, resume, and stop command sequences on Q10 simulator."""
    notified_messages = []

    def mock_notify(message: RoborockMessage) -> None:
        notified_messages.append(message)

    await q10_sim.mqtt_channel.subscribe(mock_notify)

    # 1. Start Clean
    req_payload: dict[str, Any] = {"dps": {"201": 1}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert q10_sim.status[121] == 5  # Cleaning
    assert q10_sim.status[138] == 1  # Standard Clean
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"121": 5, "138": 1}

    # 2. Pause
    req_payload = {"dps": {"204": 0}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert q10_sim.status[121] == 10  # Paused
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"121": 10}

    # 3. Resume
    req_payload = {"dps": {"205": 0}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert q10_sim.status[121] == 5  # Cleaning
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"121": 5}

    # 4. Stop
    req_payload = {"dps": {"206": 0}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert q10_sim.status[121] == 3  # Idle
    assert q10_sim.status[138] == 0  # Task type idle
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"121": 3, "138": 0}


async def test_setters(q10_sim: Q10VacuumSimulator) -> None:
    """Test setting fan speed, water level, and sound volume."""
    notified_messages = []

    def mock_notify(message: RoborockMessage) -> None:
        notified_messages.append(message)

    await q10_sim.mqtt_channel.subscribe(mock_notify)

    # Set Fan level (123) to TURBO (3)
    req_payload: dict[str, Any] = {"dps": {"123": 3}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert q10_sim.status[123] == 3
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"123": 3}

    # Set Volume (26) to 50
    req_payload = {"dps": {"26": 50}}
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(req_payload).encode("utf-8"),
    )
    await q10_sim._handle_publish(msg, q10_sim.mqtt_channel)
    assert isinstance(q10_sim.status[101], dict)
    assert q10_sim.status[101][26] == 50
    # The output payload should map nested 101 dict keys to string
    last_msg = notified_messages[-1]
    assert last_msg.payload is not None
    assert json.loads(last_msg.payload.decode())["dps"] == {"101": {"26": 50}}

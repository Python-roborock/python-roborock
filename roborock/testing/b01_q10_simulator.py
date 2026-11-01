"""Stateful simulator for Roborock Q10 (B01) devices."""

import base64
import copy
import json
import logging
from typing import Any

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.testing.simulator import RoborockDeviceSimulator

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
DEFAULT_PRODUCT_ID = "product-id-q10"

DEFAULT_Q10_STATUS = {
    101: {
        104: 0,
        105: False,
        109: "us",
        207: 0,
        25: 1,
        26: 74,
        29: 0,
        30: 0,
        31: 0,
        37: 1,
        40: 1,
        45: 0,
        47: 0,
        50: 0,
        51: True,
        53: False,
        6: 0,
        60: 1,
        67: 0,
        7: 0,
        76: 0,
        78: 0,
        79: {"timeZoneCity": "America/Los_Angeles", "timeZoneSec": -28800},
        80: 0,
        81: {"ipAdress": "1.1.1.2", "mac": "99:AA:88:BB:77:CC", "signal": -50, "wifiName": "wifi-network-name"},
        83: 1,
        86: 1,
        87: 100,
        88: 0,
        90: 0,
        92: {"disturb_dust_enable": 1, "disturb_light": 1, "disturb_resume_clean": 1, "disturb_voice": 1},
        93: 1,
        96: 0,
    },
    121: 8,
    122: 100,
    123: 2,
    124: 1,
    125: 0,
    126: 0,
    127: 0,
    136: 1,
    137: 1,
    138: 0,
    139: 5,
}


class Q10VacuumSimulator(RoborockDeviceSimulator):
    """Stateful firmware simulator for Roborock Q10 (B01 ss07) devices."""

    def __init__(
        self,
        duid: str,
        status: dict[int, Any] | None = None,
        device_info: HomeDataDevice | None = None,
        product: HomeDataProduct | None = None,
    ):
        product = product or HomeDataProduct(
            id=DEFAULT_PRODUCT_ID,
            name="Roborock Q10",
            model="roborock.vacuum.ss07",
            category=RoborockCategory.VACUUM,
        )
        device_info = device_info or HomeDataDevice(
            duid=duid,
            name="Roborock Q10",
            local_key="fake_localkey_16bytes",
            product_id=product.id,
            sn="fake_serial_number",
            pv="B01",
        )
        super().__init__(duid, device_info, product, has_local_channel=False)
        self.status = copy.deepcopy(status or DEFAULT_Q10_STATUS)
        self._room_clean_settings: dict[int, tuple[int, int, int, int, int]] = {1: (1, 3, 1, 2, 2)}

    def _complete_room_clean_payload(self) -> str:
        """Build the simulator's complete ``dpCustomerClean`` response."""
        payload = bytearray((len(self._room_clean_settings),))
        for room_id, (fan, water, clean_type, count, line) in self._room_clean_settings.items():
            properties = bytearray(26)
            properties[0:2] = room_id.to_bytes(2, "big")
            properties[3:5] = b"\xff\xff"
            properties[5:7] = count.to_bytes(2, "big")
            properties[7:10] = bytes((clean_type, fan, water))
            properties[10] = 0xFF
            properties[11] = line
            name = f"Room {room_id}".encode()
            payload.extend(properties)
            payload.extend(bytes((len(name),)) + name + bytes(19 - len(name)))
            payload.append(0)
        return base64.b64encode(payload).decode()

    def _apply_compact_room_clean_payload(self, value: str) -> bool:
        """Apply a valid compact room-settings write to simulator state."""
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            return False
        if not raw or len(raw) != 1 + raw[0] * 6:
            return False
        for offset in range(1, len(raw), 6):
            room_id, fan, water, clean_type, count, line = raw[offset : offset + 6]
            self._room_clean_settings[room_id] = (fan, water, clean_type, count, line)
        return True

    async def _handle_publish(self, message: RoborockMessage, channel: Any) -> None:
        """Process incoming Q10 RPC command payload."""
        if not message.payload:
            return

        try:
            payload = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            _LOGGER.warning("Simulator failed to parse incoming B01 payload: %s", ex)
            return

        datapoints = payload.get("dps", {})
        if not isinstance(datapoints, dict):
            return

        updated_dps: dict[int, Any] = {}

        for code_str, params in datapoints.items():
            try:
                code = int(code_str)
            except ValueError:
                continue

            if code == 101 and isinstance(params, dict):
                common = self.status[101]
                if not isinstance(common, dict):
                    continue
                changed: dict[int, Any] = {}
                for nested_code_raw, nested_value in params.items():
                    try:
                        nested_code = int(nested_code_raw)
                    except (TypeError, ValueError):
                        continue
                    if nested_code == 62 and isinstance(nested_value, str):
                        if self._apply_compact_room_clean_payload(nested_value):
                            common[nested_code] = nested_value
                            changed[nested_code] = nested_value
                    elif nested_code == 63 and nested_value == 0:
                        changed[62] = self._complete_room_clean_payload()
                    elif nested_code in (25, 26, 37, 47, 50, 77, 78):
                        common[nested_code] = nested_value
                        changed[nested_code] = nested_value
                if changed:
                    updated_dps[101] = changed
                continue

            # Command: REQUEST_DPS (102) -> trigger status push
            if code == 102:
                # REQUEST_DPS triggers a dump of all status properties
                # (both root properties and nested properties under 101)
                self.trigger_push_update()
                continue

            # Command: START_CLEAN (201)
            elif code == 201:
                # 1 = sweep/mop, cmd inside dict = segment clean
                self.status[121] = 5  # YXDeviceState.CLEANING
                if isinstance(params, dict) and "cmd" in params:
                    self.status[138] = params.get("cmd", 0)  # clean_task_type
                else:
                    self.status[138] = 1  # CLEANING
                updated_dps[121] = self.status[121]
                updated_dps[138] = self.status[138]

            # Command: START_BACK (202)
            elif code == 202:
                # 5 = returning to charge
                self.status[121] = 6  # YXDeviceState.RETURNING_HOME
                self.status[139] = 5  # BACK_CHARGING
                updated_dps[121] = self.status[121]
                updated_dps[139] = self.status[139]

            # Command: START_DOCK_TASK (203)
            elif code == 203:
                # Empty dustbin
                self.status[121] = 22  # EMPTYING_THE_BIN
                updated_dps[121] = self.status[121]

            # Command: PAUSE (204)
            elif code == 204:
                self.status[121] = 10  # YXDeviceState.PAUSED
                updated_dps[121] = self.status[121]

            # Command: RESUME (205)
            elif code == 205:
                self.status[121] = 5  # YXDeviceState.CLEANING
                updated_dps[121] = self.status[121]

            # Command: STOP (206)
            elif code == 206:
                self.status[121] = 3  # YXDeviceState.IDLE
                self.status[138] = 0  # YXDeviceCleanTask.UNKNOWN/IDLE
                updated_dps[121] = self.status[121]
                updated_dps[138] = self.status[138]

            # Command: FAN_LEVEL (123)
            elif code == 123:
                self.status[123] = params
                updated_dps[123] = params

            # Command: WATER_LEVEL (124)
            elif code == 124:
                self.status[124] = params
                updated_dps[124] = params

            # Command: CLEAN_COUNT (136)
            elif code == 136:
                self.status[136] = params
                updated_dps[136] = params

            # Command: CLEAN_MODE (137)
            elif code == 137:
                self.status[137] = params
                updated_dps[137] = params

            # Custom settings properties routed to sub-traits (DND, child lock, volume, dust collections)
            elif code in (26, 47, 25, 37, 50):
                # These live in the nested dpCommon (101) dict
                common_dict = self.status[101]
                if isinstance(common_dict, dict):
                    common_dict[code] = params
                # We return them nested under 101
                if 101 not in updated_dps:
                    updated_dps[101] = {}
                updated_dps[101][code] = params

        if updated_dps:
            # Send the changed datapoints back to the client
            self.push_dps(updated_dps)

    def push_dps(self, dps_updates: dict[int, Any]) -> None:
        """Push a set of status datapoint changes to the client."""
        payload = {
            "dps": {
                str(k): ({str(sub_k): sub_v for sub_k, sub_v in v.items()} if isinstance(v, dict) and k == 101 else v)
                for k, v in dps_updates.items()
            }
        }
        message = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            version=B01_VERSION,
            payload=json.dumps(payload).encode("utf-8"),
        )
        self.mqtt_channel.notify_subscribers(message)

    def trigger_push_update(self) -> None:
        """Send the full status dump to the client."""
        self.push_dps(self.status)

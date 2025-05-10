import base64
import json
import logging
import math
import secrets
import time
from urllib.parse import urlparse

from . import RoborockCommand
from .containers import DeviceData, ModelStatus, S7MaxVStatus, Status, UserData
from .device_trait import ConsumableTrait, DeviceTrait, DndTrait
from .mqtt.roborock_session import MqttParams, RoborockMqttSession
from .protocol import MessageParser, Utils, md5hex
from .roborock_message import RoborockMessage, RoborockMessageProtocol
from .util import RoborockLoggerAdapter, get_next_int

_LOGGER = logging.getLogger(__name__)


class RoborockDevice:
    _mqtt_sessions: dict[str, RoborockMqttSession] = {}

    def __init__(self, user_data: UserData, device_info: DeviceData):
        self.user_data = user_data
        self.device_info = device_info
        self.data = None
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
        self._mqtt_endpoint = base64.b64encode(Utils.md5(user_data.rriot.k.encode())[8:14]).decode()
        rriot = user_data.rriot
        hashed_user = md5hex(rriot.u + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        mqtt_password = rriot.s

        self._local_endpoint = "abc"
        self._nonce = secrets.token_bytes(16)
        self._message_id_types: dict[int, DeviceTrait] = {}
        self._command_to_trait = {}
        self._all_supported_traits = []
        self._dnd_trait: DndTrait | None = self.determine_supported_traits(DndTrait)
        self._consumable_trait: ConsumableTrait | None = self.determine_supported_traits(ConsumableTrait)
        self._status_type: type[Status] = ModelStatus.get(device_info.model, S7MaxVStatus)
        # TODO: One per client EVER
        self.session = RoborockMqttSession(
            MqttParams(
                host=str(url.hostname),
                port=url.port,
                tls=True,
                username=hashed_user,
                password=md5hex(rriot.s + ":" + rriot.k)[16:],
            )
        )
        self.input_topic = f"rr/m/i/{rriot.u}/{hashed_user}/{device_info.duid}"
        self.output_topic = f"rr/m/o/{rriot.u}/{hashed_user}/{device_info.duid}"

    def determine_supported_traits(self, trait: type[DeviceTrait]):
        def _send_command(
            method: RoborockCommand | str, params: list | dict | int | None = None, use_cloud: bool = True
        ):
            return self.send_message(method, params, use_cloud)

        if trait.supported(self.device_info.device_features):
            trait_instance = trait(_send_command)
            self._all_supported_traits.append(trait(_send_command))
            self._command_to_trait[trait.handle_command] = trait_instance
            return trait_instance
        return None

    async def connect(self):
        """Connect via MQTT and Local if possible."""
        if not self.session.connected:
            await self.session.start()
            await self.session.subscribe(self.output_topic, callback=self.on_message)

    async def update(self):
        for trait in self._all_supported_traits:
            await trait.get()

    def _get_payload(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
        secured=False,
        use_cloud: bool = False,
    ):
        timestamp = math.floor(time.time())
        request_id = get_next_int(10000, 32767)
        inner = {
            "id": request_id,
            "method": method,
            "params": params or [],
        }
        if secured:
            inner["security"] = {
                "endpoint": self._mqtt_endpoint if use_cloud else self._local_endpoint,
                "nonce": self._nonce.hex().lower(),
            }
        payload = bytes(
            json.dumps(
                {
                    "dps": {"101": json.dumps(inner, separators=(",", ":"))},
                    "t": timestamp,
                },
                separators=(",", ":"),
            ).encode()
        )
        return request_id, timestamp, payload

    async def send_message(
        self, method: RoborockCommand | str, params: list | dict | int | None = None, use_cloud: bool = True
    ):
        request_id, timestamp, payload = self._get_payload(method, params, True, use_cloud)
        request_protocol = RoborockMessageProtocol.RPC_REQUEST
        roborock_message = RoborockMessage(timestamp=timestamp, protocol=request_protocol, payload=payload)
        if request_id in self._message_id_types:
            raise Exception("Duplicate id!")
        if method in self._command_to_trait:
            self._message_id_types[request_id] = self._command_to_trait[method]
        local_key = self.device_info.device.local_key
        msg = MessageParser.build(roborock_message, local_key, False)
        if use_cloud:
            await self.session.publish(self.input_topic, msg)
        else:
            # Handle doing local commands
            pass

    def on_message(self, message_bytes: bytes):
        messages = MessageParser.parse(message_bytes, self.device_info.device.local_key)[0]
        for message in messages:
            message_payload = message.get_payload()
            message_id = message.get_request_id()
            for data_point_number, data_point in message_payload.get("dps").items():
                if data_point_number == "102":
                    data_point_response = json.loads(data_point)
                    result = data_point_response.get("result")
                    if isinstance(result, list) and len(result) == 1:
                        result = result[0]
                    if result and (trait := self._message_id_types.get(message_id)) is not None:
                        trait.on_message(result)
                    if (error := result.get("error")) is not None:
                        print(error)
            print()
            # If message is command not supported - remove from self.update_commands

            # If message is an error - log it?

            # If message is 'ok' - ignore it

            # If message is anything else - store ids, and map back to id to determine message type.
            # Then update self.data

            # If we haven't received a message in X seconds, the device is likely offline. I think we can continue the connection,
            # but we should have some way to mark ourselves as unavailable.

            # This should also probably be split with on_cloud_message and on_local_message.
            print(message)

    @property
    def dnd(self) -> DndTrait | None:
        return self._dnd_trait

    @property
    def consumable(self) -> ConsumableTrait | None:
        return self._consumable_trait

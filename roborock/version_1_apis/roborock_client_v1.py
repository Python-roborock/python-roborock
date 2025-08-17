import asyncio
import dataclasses
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar, final

from roborock import (
    AppInitStatus,
    DeviceProp,
    DockSummary,
    RoborockCommand,
    RoborockDockTypeCode,
    RoborockException,
    UnknownMethodError,
    VacuumError,
)
from roborock.api import RoborockClient
from roborock.command_cache import (
    CacheableAttribute,
    CommandType,
    RoborockAttribute,
    find_cacheable_attribute,
    get_cache_map,
)
from roborock.containers import (
    ChildLockStatus,
    CleanRecord,
    CleanSummary,
    Consumable,
    DeviceData,
    DnDTimer,
    DustCollectionMode,
    FlowLedStatus,
    ModelStatus,
    MultiMapsList,
    NetworkInfo,
    RoborockBase,
    RoomMapping,
    S7MaxVStatus,
    ServerTimer,
    SmartWashParams,
    Status,
    ValleyElectricityTimer,
    WashTowelMode,
)
from roborock.protocols.v1_protocol import MapResponse, SecurityData, create_map_response_decoder
from roborock.roborock_message import (
    ROBOROCK_DATA_CONSUMABLE_PROTOCOL,
    ROBOROCK_DATA_STATUS_PROTOCOL,
    RoborockDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
)
from roborock.util import RepeatableTask, unpack_list

CUSTOM_COMMANDS = {RoborockCommand.GET_MAP_CALIBRATION}

COMMANDS_SECURED = {
    RoborockCommand.GET_MAP_V1,
    RoborockCommand.GET_MULTI_MAP,
}

CLOUD_REQUIRED = COMMANDS_SECURED.union(CUSTOM_COMMANDS)

WASH_N_FILL_DOCK = [
    RoborockDockTypeCode.empty_wash_fill_dock,
    RoborockDockTypeCode.s8_dock,
    RoborockDockTypeCode.p10_dock,
    RoborockDockTypeCode.p10_pro_dock,
    RoborockDockTypeCode.s8_maxv_ultra_dock,
    RoborockDockTypeCode.qrevo_s_dock,
    RoborockDockTypeCode.saros_r10_dock,
    RoborockDockTypeCode.qrevo_curv_dock,
]
RT = TypeVar("RT", bound=RoborockBase)
EVICT_TIME = 60


_SendCommandT = Callable[[RoborockCommand | str, list | dict | int | None], Any]


class AttributeCache:
    def __init__(self, attribute: RoborockAttribute, send_command: _SendCommandT):
        self.attribute = attribute
        self._send_command = send_command
        self.attribute = attribute
        self.task = RepeatableTask(self._async_value, EVICT_TIME)
        self._value: Any = None
        self._mutex = asyncio.Lock()
        self.unsupported: bool = False

    @property
    def value(self):
        return self._value

    async def _async_value(self):
        if self.unsupported:
            return None
        try:
            self._value = await self._send_command(self.attribute.get_command, None)
        except UnknownMethodError as err:
            # Limit the amount of times we call unsupported methods
            self.unsupported = True
            raise err
        return self._value

    async def async_value(self, force: bool = False):
        async with self._mutex:
            if self._value is None or force:
                return await self.task.reset()
            return self._value

    def stop(self):
        self.task.cancel()

    async def update_value(self, params) -> None:
        if self.attribute.set_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no set command")
        response = await self._send_command(self.attribute.set_command, params)
        await self._async_value()
        return response

    async def add_value(self, params):
        if self.attribute.add_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no add command")
        response = await self._send_command(self.attribute.add_command, params)
        await self._async_value()
        return response

    async def close_value(self, params=None) -> None:
        if self.attribute.close_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no close command")
        response = await self._send_command(self.attribute.close_command, params)
        await self._async_value()
        return response

    async def refresh_value(self):
        await self._async_value()


@dataclasses.dataclass
class ListenerModel:
    protocol_handlers: dict[RoborockDataProtocol, list[Callable[[Status | Consumable], None]]]
    cache: dict[CacheableAttribute, AttributeCache]


class RoborockClientV1(RoborockClient, ABC):
    """Roborock client base class for version 1 devices."""

    _listeners: dict[str, ListenerModel] = {}
    _map_response_decoder: Callable[[RoborockMessage], MapResponse] | None = None

    def __init__(self, device_info: DeviceData, security_data: SecurityData | None) -> None:
        """Initializes the Roborock client."""
        super().__init__(device_info)
        if security_data is not None:
            self._diagnostic_data.update({"misc_info": security_data.to_diagnostic_data()})
            self._map_response_decoder = create_map_response_decoder(security_data)

        self._status_type: type[Status] = ModelStatus.get(device_info.model, S7MaxVStatus)
        self.cache: dict[CacheableAttribute, AttributeCache] = {
            cacheable_attribute: AttributeCache(attr, self._send_command)
            for cacheable_attribute, attr in get_cache_map().items()
        }
        if device_info.device.duid not in self._listeners:
            self._listeners[device_info.device.duid] = ListenerModel({}, self.cache)
        self.listener_model = self._listeners[device_info.device.duid]

    async def async_release(self) -> None:
        await super().async_release()
        [item.stop() for item in self.cache.values()]

    @property
    def status_type(self) -> type[Status]:
        """Gets the status type for this device"""
        return self._status_type

    async def get_status(self) -> Status:
        data = self._status_type.from_dict(await self.cache[CacheableAttribute.status].async_value(force=True))
        if data is None:
            return self._status_type()
        return data

    async def get_dnd_timer(self) -> DnDTimer | None:
        return DnDTimer.from_dict(await self.cache[CacheableAttribute.dnd_timer].async_value())

    async def get_valley_electricity_timer(self) -> ValleyElectricityTimer | None:
        return ValleyElectricityTimer.from_dict(
            await self.cache[CacheableAttribute.valley_electricity_timer].async_value()
        )

    async def get_clean_summary(self) -> CleanSummary | None:
        clean_summary: dict | list | int = await self.send_command(RoborockCommand.GET_CLEAN_SUMMARY)
        if isinstance(clean_summary, dict):
            return CleanSummary.from_dict(clean_summary)
        elif isinstance(clean_summary, list):
            clean_time, clean_area, clean_count, records = unpack_list(clean_summary, 4)
            return CleanSummary(
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(clean_summary, int):
            return CleanSummary(clean_time=clean_summary)
        return None

    async def get_clean_record(self, record_id: int) -> CleanRecord | None:
        record: dict | list = await self.send_command(RoborockCommand.GET_CLEAN_RECORD, [record_id])
        if isinstance(record, dict):
            return CleanRecord.from_dict(record)
        elif isinstance(record, list):
            if isinstance(record[-1], dict):
                records = [CleanRecord.from_dict(rec) for rec in record]
                final_record = records[-1]
                try:
                    # This code is semi-presumptions - so it is put in a try finally to be safe.
                    final_record.begin = records[0].begin
                    final_record.begin_datetime = records[0].begin_datetime
                    final_record.start_type = records[0].start_type
                    for rec in records[0:-1]:
                        final_record.duration += rec.duration if rec.duration is not None else 0
                        final_record.area += rec.area if rec.area is not None else 0
                        final_record.avoid_count += rec.avoid_count if rec.avoid_count is not None else 0
                        final_record.wash_count += rec.wash_count if rec.wash_count is not None else 0
                        final_record.square_meter_area += (
                            rec.square_meter_area if rec.square_meter_area is not None else 0
                        )
                finally:
                    return final_record
            # There are still a few unknown variables in this.
            begin, end, duration, area = unpack_list(record, 4)
            return CleanRecord(begin=begin, end=end, duration=duration, area=area)
        else:
            self._logger.warning("Clean record was of a new type, please submit an issue request: %s", record)
            return None

    async def get_consumable(self) -> Consumable:
        data = Consumable.from_dict(await self.cache[CacheableAttribute.consumable].async_value())
        if data is None:
            return Consumable()
        return data

    async def get_wash_towel_mode(self) -> WashTowelMode | None:
        return WashTowelMode.from_dict(await self.cache[CacheableAttribute.wash_towel_mode].async_value())

    async def get_dust_collection_mode(self) -> DustCollectionMode | None:
        return DustCollectionMode.from_dict(await self.cache[CacheableAttribute.dust_collection_mode].async_value())

    async def get_smart_wash_params(self) -> SmartWashParams | None:
        return SmartWashParams.from_dict(await self.cache[CacheableAttribute.smart_wash_params].async_value())

    async def get_dock_summary(self, dock_type: RoborockDockTypeCode) -> DockSummary:
        """Gets the status summary from the dock with the methods available for a given dock.

        :param dock_type: RoborockDockTypeCode"""
        commands: list[
            Coroutine[
                Any,
                Any,
                DustCollectionMode | WashTowelMode | SmartWashParams | None,
            ]
        ] = [self.get_dust_collection_mode()]
        if dock_type in WASH_N_FILL_DOCK:
            commands += [
                self.get_wash_towel_mode(),
                self.get_smart_wash_params(),
            ]
        [dust_collection_mode, wash_towel_mode, smart_wash_params] = unpack_list(
            list(await asyncio.gather(*commands)), 3
        )  # type: DustCollectionMode, WashTowelMode | None, SmartWashParams | None # type: ignore

        return DockSummary(dust_collection_mode, wash_towel_mode, smart_wash_params)

    async def get_prop(self) -> DeviceProp | None:
        """Gets device general properties."""
        # Mypy thinks that each one of these is typed as a union of all the others. so we do type ignore.
        status, clean_summary, consumable = await asyncio.gather(
            *[
                self.get_status(),
                self.get_clean_summary(),
                self.get_consumable(),
            ]
        )  # type: Status, CleanSummary, Consumable # type: ignore
        last_clean_record = None
        if clean_summary and clean_summary.records and len(clean_summary.records) > 0:
            last_clean_record = await self.get_clean_record(clean_summary.records[0])
        dock_summary = None
        if status and status.dock_type is not None and status.dock_type != RoborockDockTypeCode.no_dock:
            dock_summary = await self.get_dock_summary(status.dock_type)
        if any([status, clean_summary, consumable]):
            return DeviceProp(
                status,
                clean_summary,
                consumable,
                last_clean_record,
                dock_summary,
            )
        return None

    async def get_multi_maps_list(self) -> MultiMapsList | None:
        return await self.send_command(RoborockCommand.GET_MULTI_MAPS_LIST, return_type=MultiMapsList)

    async def get_networking(self) -> NetworkInfo | None:
        return await self.send_command(RoborockCommand.GET_NETWORK_INFO, return_type=NetworkInfo)

    async def get_room_mapping(self) -> list[RoomMapping] | None:
        """Gets the mapping from segment id -> iot id. Only works on local api."""
        mapping: list = await self.send_command(RoborockCommand.GET_ROOM_MAPPING)
        if isinstance(mapping, list):
            if len(mapping) == 2 and not isinstance(mapping[0], list):
                return [RoomMapping(segment_id=mapping[0], iot_id=mapping[1])]
            return [
                RoomMapping(segment_id=segment_id, iot_id=iot_id)  # type: ignore
                for segment_id, iot_id in [unpack_list(room, 2) for room in mapping if isinstance(room, list)]
            ]
        return None

    async def get_child_lock_status(self) -> ChildLockStatus:
        """Gets current child lock status."""
        return ChildLockStatus.from_dict(await self.cache[CacheableAttribute.child_lock_status].async_value())

    async def get_flow_led_status(self) -> FlowLedStatus:
        """Gets current flow led status."""
        return FlowLedStatus.from_dict(await self.cache[CacheableAttribute.flow_led_status].async_value())

    async def get_sound_volume(self) -> int | None:
        """Gets current volume level."""
        return await self.cache[CacheableAttribute.sound_volume].async_value()

    async def get_server_timer(self) -> list[ServerTimer]:
        """Gets current server timer."""
        server_timers = await self.cache[CacheableAttribute.server_timer].async_value()
        if server_timers:
            if isinstance(server_timers[0], list):
                return [ServerTimer(*server_timer) for server_timer in server_timers]
            return [ServerTimer(*server_timers)]
        return []

    async def load_multi_map(self, map_flag: int) -> None:
        """Load the map into the vacuum's memory."""
        await self.send_command(RoborockCommand.LOAD_MULTI_MAP, [map_flag])

    async def get_app_init_status(self) -> AppInitStatus:
        """Gets the app init status (needed for determining vacuum capabilities)."""
        return await self.send_command(RoborockCommand.APP_GET_INIT_STATUS, return_type=AppInitStatus)

    @abstractmethod
    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ) -> Any:
        """Send a command to the Roborock device."""

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        try:
            self._last_device_msg_in = time.monotonic()
            for data in messages:
                protocol = data.protocol
                if data.payload and protocol in [
                    RoborockMessageProtocol.RPC_RESPONSE,
                    RoborockMessageProtocol.GENERAL_REQUEST,
                ]:
                    payload = json.loads(data.payload.decode())
                    for data_point_number, data_point in payload.get("dps").items():
                        if data_point_number == "102":
                            data_point_response = json.loads(data_point)
                            request_id = data_point_response.get("id")
                            queue = self._waiting_queue.get(request_id)
                            if queue and queue.protocol == protocol:
                                error = data_point_response.get("error")
                                if error:
                                    queue.set_exception(
                                        VacuumError(
                                            error.get("code"),
                                            error.get("message"),
                                        ),
                                    )
                                else:
                                    result = data_point_response.get("result")
                                    if isinstance(result, list) and len(result) == 1:
                                        result = result[0]
                                    queue.set_result(result)
                            else:
                                self._logger.debug("Received response for unknown request id %s", request_id)
                        else:
                            try:
                                data_protocol = RoborockDataProtocol(int(data_point_number))
                                self._logger.debug(f"Got device update for {data_protocol.name}: {data_point}")
                                if data_protocol in ROBOROCK_DATA_STATUS_PROTOCOL:
                                    if data_protocol not in self.listener_model.protocol_handlers:
                                        self._logger.debug(
                                            f"Got status update({data_protocol.name}) before get_status was called."
                                        )
                                        return
                                    value = self.listener_model.cache[CacheableAttribute.status].value
                                    value[data_protocol.name] = data_point
                                    status = self._status_type.from_dict(value)
                                    for listener in self.listener_model.protocol_handlers.get(data_protocol, []):
                                        listener(status)
                                elif data_protocol in ROBOROCK_DATA_CONSUMABLE_PROTOCOL:
                                    if data_protocol not in self.listener_model.protocol_handlers:
                                        self._logger.debug(
                                            f"Got consumable update({data_protocol.name})"
                                            + "before get_consumable was called."
                                        )
                                        return
                                    value = self.listener_model.cache[CacheableAttribute.consumable].value
                                    value[data_protocol.name] = data_point
                                    consumable = Consumable.from_dict(value)
                                    for listener in self.listener_model.protocol_handlers.get(data_protocol, []):
                                        listener(consumable)
                                elif data_protocol in {
                                    RoborockDataProtocol.ADDITIONAL_PROPS,
                                    RoborockDataProtocol.DRYING_STATUS,
                                }:
                                    # Known data protocol, but not yet sure how to correctly utilize it.
                                    return
                                else:
                                    self._logger.warning(
                                        f"Unknown data protocol {data_point_number}, please create an "
                                        f"issue on the python-roborock repository"
                                    )
                                    self._logger.info(data)
                                return
                            except ValueError:
                                self._logger.warning(
                                    f"Got listener data for {data_point_number}, data: {data_point}. "
                                    f"This lets us update data quicker, please open an issue "
                                    f"at https://github.com/humbertogontijo/python-roborock/issues"
                                )

                                pass
                            dps = {data_point_number: data_point}
                            self._logger.debug(f"Got unknown data point {dps}")
                elif data.payload and protocol == RoborockMessageProtocol.MAP_RESPONSE:
                    if self._map_response_decoder is not None:
                        map_response = self._map_response_decoder(data)
                        queue = self._waiting_queue.get(map_response.request_id)
                        if queue:
                            queue.set_result(map_response.data)
                        else:
                            self._logger.debug(
                                "Received unsolicited map response for request_id %s", map_response.request_id
                            )
                else:
                    queue = self._waiting_queue.get(data.seq)
                    if queue:
                        queue.set_result(data.payload)
                    else:
                        self._logger.debug("Received response for unknown request id %s", data.seq)
        except Exception as ex:
            self._logger.exception(ex)

    async def get_from_cache(self, key: CacheableAttribute) -> AttributeCache | None:
        val = self.cache.get(key)
        if val is not None:
            return await val.async_value()
        return None

    def add_listener(
        self, protocol: RoborockDataProtocol, listener: Callable, cache: dict[CacheableAttribute, AttributeCache]
    ) -> None:
        self.listener_model.cache = cache
        if protocol not in self.listener_model.protocol_handlers:
            self.listener_model.protocol_handlers[protocol] = []
        self.listener_model.protocol_handlers[protocol].append(listener)

    def remove_listener(self, protocol: RoborockDataProtocol, listener: Callable) -> None:
        self.listener_model.protocol_handlers[protocol].remove(listener)

    @final
    async def send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
        return_type: type[RT] | None = None,
    ) -> RT:
        cacheable_attribute_result = find_cacheable_attribute(method)

        cache = None
        command_type = None
        if cacheable_attribute_result is not None:
            cache = self.cache[cacheable_attribute_result.attribute]
            command_type = cacheable_attribute_result.type

        response: Any = None
        if cache is not None and command_type == CommandType.GET:
            response = await cache.async_value()
        else:
            response = await self._send_command(method, params)
            if cache is not None and command_type == CommandType.CHANGE:
                await cache.refresh_value()

        if return_type:
            return return_type.from_dict(response)
        return response

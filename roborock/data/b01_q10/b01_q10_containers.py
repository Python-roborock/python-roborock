from ..containers import RoborockBase


class dpCleanRecord(RoborockBase):
    op: str
    result: int
    id: str
    data: list


class dpMultiMap(RoborockBase):
    op: str
    result: int
    data: list


class dpGetCarpet(RoborockBase):
    op: str
    result: int
    data: str


class dpSelfIdentifyingCarpet(RoborockBase):
    op: str
    result: int
    data: str


class dpNetInfo(RoborockBase):
    wifiName: str
    ipAdress: str
    mac: str
    signal: int


class dpNotDisturbExpand(RoborockBase):
    disturb_dust_enable: int
    disturb_light: int
    disturb_resume_clean: int
    disturb_voice: int


class dpCurrentCleanRoomIds(RoborockBase):
    room_id_list: list


class dpVoiceVersion(RoborockBase):
    version: int


class dpTimeZone(RoborockBase):
    timeZoneCity: str
    timeZoneSec: int

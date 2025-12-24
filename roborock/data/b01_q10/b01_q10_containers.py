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


class Q10Status(RoborockBase):
    """Status for Q10 devices."""

    clean_time: int | None = None
    clean_area: int | None = None
    battery: int | None = None
    status: int | None = None
    fun_level: int | None = None
    water_level: int | None = None
    clean_count: int | None = None
    clean_mode: int | None = None
    clean_task_type: int | None = None
    back_type: int | None = None
    cleaning_progress: int | None = None


class Q10Consumable(RoborockBase):
    """Consumable status for Q10 devices."""

    main_brush_life: int | None = None
    side_brush_life: int | None = None
    filter_life: int | None = None
    rag_life: int | None = None
    sensor_life: int | None = None


class Q10DND(RoborockBase):
    """DND status for Q10 devices."""

    enabled: bool | None = None
    start_time: str | None = None
    end_time: str | None = None


class Q10Volume(RoborockBase):
    """Volume status for Q10 devices."""

    volume: int | None = None


class Q10ChildLock(RoborockBase):
    """Child lock status for Q10 devices."""

    enabled: bool | None = None

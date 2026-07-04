import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    B01_Q10_DP,
    YXCleaningResult,
    YXCleanScope,
    YXCleanType,
    YXStartMethod,
)
from roborock.data.b01_q10.b01_q10_containers import Q10CleanRecord
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.clean_history import CleanHistoryTrait, CleanRecordConverter

from .conftest import FakeB01Q10Channel

# 12 underscore fields: recordId, startTime, cleanTime, cleanArea, mapLen, pathLen,
# virtualLen, cleanMode, workMode, cleaningResult, startMethod, collectDustCount.
RECORD_A = "abc123def456_1781226271_27_19_6692_12053_4_0_2_1_1_1"
RECORD_B = "def456abc789_1781139871_41_25_7100_18420_5_1_1_0_2_1"


@pytest.fixture(name="clean_history")
def clean_history_fixture(q10_api: Q10PropertiesApi) -> CleanHistoryTrait:
    return q10_api.clean_history


def _list_push(*records: str) -> dict[B01_Q10_DP, object]:
    """Build a decoded DPS update carrying a clean-record list."""
    return {B01_Q10_DP.CLEAN_RECORD: {"op": "list", "result": 1, "id": "", "data": list(records)}}


def _notify_push(record: str) -> dict[B01_Q10_DP, object]:
    """Build a decoded DPS update carrying a single clean-finished notify push."""
    return {B01_Q10_DP.CLEAN_RECORD: {"op": "notify", "result": 1, "id": record}}


def test_parse_clean_record() -> None:
    record = CleanRecordConverter.parse_record(RECORD_A)  # cleanMode/workMode/result/start = 0/2/1/1
    assert record is not None
    assert record.raw == RECORD_A
    assert record.record_id == "abc123def456"
    assert record.start_time == 1781226271
    assert record.clean_time == 27
    assert record.clean_area == 19
    assert record.map_len == 6692
    assert record.path_len == 12053
    assert record.virtual_len == 4
    assert record.collect_dust_count == 1
    assert record.start_datetime is not None
    # Enum-typed fields (no separate property converters).
    assert record.clean_mode is YXCleanScope.FULL
    assert record.work_mode is YXCleanType.VACUUM
    assert record.cleaning_result is YXCleaningResult.COMPLETED
    assert record.start_method is YXStartMethod.APP

    record_b = CleanRecordConverter.parse_record(RECORD_B)  # 1/1/0/2
    assert record_b is not None
    assert record_b.clean_mode is YXCleanScope.SELECTIVE_ROOM
    assert record_b.work_mode is YXCleanType.VAC_AND_MOP
    assert record_b.cleaning_result is YXCleaningResult.INTERRUPTED
    assert record_b.start_method is YXStartMethod.TIMER


@pytest.mark.parametrize(
    "raw",
    [
        "too_few_fields",
        "a_b_c_d_e_f_g_h_i_j_k_l_m",  # 13 fields
        "id_NOTANUMBER_27_19_6692_12053_4_0_2_1_1_1",  # non-int where int expected
    ],
)
def test_parse_clean_record_malformed_returns_none(raw: str) -> None:
    assert CleanRecordConverter.parse_record(raw) is None


def test_unmapped_enum_code_is_crash_safe() -> None:
    """An unmapped code (cleanMode 2) yields None on the field; the raw string is kept."""
    record = CleanRecordConverter.parse_record("x_1781226271_1_1_0_0_0_2_2_1_0_0")  # cleanMode=2, startMethod=0
    assert record is not None
    assert record.clean_mode is None  # code 2 unmapped -> None, never raises
    assert record.raw.split("_")[7] == "2"  # the original is retained in raw
    assert record.start_method is YXStartMethod.REMOTE  # 0 maps even though unobserved live
    assert Q10CleanRecord(raw="").clean_mode is None  # an unset field -> None


def test_update_from_dps_populates_records_newest_first(clean_history: CleanHistoryTrait) -> None:
    updates = 0

    def _on_update() -> None:
        nonlocal updates
        updates += 1

    clean_history.add_update_listener(_on_update)

    # RECORD_B starts earlier than RECORD_A; supply oldest-first to prove sorting.
    clean_history.update_from_dps(_list_push(RECORD_B, RECORD_A))

    assert [r.record_id for r in clean_history.records] == ["abc123def456", "def456abc789"]
    assert clean_history.last_record is not None
    assert clean_history.last_record.start_time == 1781226271
    assert updates == 1


def test_update_from_dps_skips_malformed_entries(clean_history: CleanHistoryTrait) -> None:
    clean_history.update_from_dps(_list_push(RECORD_A, "garbage", "1_2_3"))
    assert len(clean_history.records) == 1
    assert clean_history.records[0].record_id == "abc123def456"


@pytest.mark.parametrize(
    "dps",
    [
        {},  # no clean-record key at all
        {B01_Q10_DP.CLEAN_RECORD: {"op": "notify", "result": 1, "id": "x"}},  # malformed notify id
        {B01_Q10_DP.CLEAN_RECORD: False},  # bool sentinel, not a dict
    ],
)
def test_update_from_dps_ignores_unusable_pushes(
    clean_history: CleanHistoryTrait, dps: dict[B01_Q10_DP, object]
) -> None:
    updates = 0

    def _on_update() -> None:
        nonlocal updates
        updates += 1

    clean_history.add_update_listener(_on_update)
    clean_history.update_from_dps(dps)  # type: ignore[arg-type]

    assert clean_history.records == []
    assert clean_history.last_record is None
    assert updates == 0


def test_update_from_dps_notify_inserts_record(clean_history: CleanHistoryTrait) -> None:
    updates = 0

    def _on_update() -> None:
        nonlocal updates
        updates += 1

    clean_history.add_update_listener(_on_update)
    clean_history.update_from_dps(_notify_push(RECORD_A))

    assert [r.record_id for r in clean_history.records] == ["abc123def456"]
    assert updates == 1


def test_update_from_dps_notify_upserts_newest_first(clean_history: CleanHistoryTrait) -> None:
    clean_history.update_from_dps(_list_push(RECORD_B))  # older record present
    clean_history.update_from_dps(_notify_push(RECORD_A))  # newer -> prepend

    assert [r.record_id for r in clean_history.records] == ["abc123def456", "def456abc789"]

    # A notify for an existing record_id replaces it (no duplicate).
    updated_a = RECORD_A.replace("_27_", "_99_")  # same id, clean_time 27 -> 99
    clean_history.update_from_dps(_notify_push(updated_a))

    assert [r.record_id for r in clean_history.records] == ["abc123def456", "def456abc789"]
    assert clean_history.records[0].clean_time == 99


def test_update_from_dps_notify_ignores_malformed(clean_history: CleanHistoryTrait) -> None:
    clean_history.update_from_dps(_list_push(RECORD_A))
    clean_history.update_from_dps(_notify_push("garbage"))  # malformed id -> ignored

    assert [r.record_id for r in clean_history.records] == ["abc123def456"]


async def test_refresh_sends_op_list(q10_api: Q10PropertiesApi, fake_channel: FakeB01Q10Channel) -> None:
    await q10_api.clean_history.refresh()

    assert len(fake_channel.published_commands) == 1
    assert fake_channel.published_commands[0] == (
        B01_Q10_DP.COMMON,
        {"52": {"op": "list"}},
    )

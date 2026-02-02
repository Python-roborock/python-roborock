"""Tests for CleanSummaryTrait class for B01/Q7 devices."""

import json
import logging

import pytest

from roborock.data.b01_q7 import CleanRecordList
from roborock.devices.traits.b01.q7.clean_summary import CleanSummaryTrait
from roborock.exceptions import RoborockException
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder

CLEAN_RECORD_LIST_DATA = {
    "total_time": 34980,
    "total_area": 28540,
    "total_count": 2,
    "record_list": [
        {
            "url": "/userdata/record_map/1766368207_1766368283_0_clean_map.bin",
            "detail": json.dumps(
                {
                    "record_start_time": 1766368207,
                    "method": 0,
                    "record_use_time": 60,
                    "clean_count": 1,
                    "record_clean_area": 85,
                    "record_clean_mode": 0,
                    "record_clean_way": 0,
                    "record_task_status": 20,
                    "record_faultcode": 0,
                    "record_dust_num": 0,
                    "clean_current_map": 0,
                    "record_map_url": "/userdata/record_map/1766368207_1766368283_0_clean_map.bin",
                }
            ),
        },
        {
            "url": "/userdata/record_map/1766369000_1766369200_0_clean_map.bin",
            "detail": json.dumps(
                {
                    "record_start_time": 1766369000,
                    "method": 1,
                    "record_use_time": 120,
                    "clean_count": 1,
                    "record_clean_area": 150,
                    "record_clean_mode": 1,
                    "record_clean_way": 0,
                    "record_task_status": 20,
                    "record_faultcode": 0,
                    "record_dust_num": 1,
                    "clean_current_map": 1,
                    "record_map_url": "/userdata/record_map/1766369000_1766369200_0_clean_map.bin",
                }
            ),
        },
    ],
}


@pytest.fixture(name="clean_summary_trait")
def clean_summary_trait_fixture(fake_channel: FakeChannel) -> CleanSummaryTrait:
    return CleanSummaryTrait(fake_channel)  # type: ignore[arg-type]


async def test_refresh_success(
    clean_summary_trait: CleanSummaryTrait,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
) -> None:
    """Test successfully refreshing clean summary."""
    fake_channel.response_queue.append(message_builder.build(CLEAN_RECORD_LIST_DATA))
    await clean_summary_trait.refresh()

    assert clean_summary_trait.total_time == 34980
    assert clean_summary_trait.total_area == 28540
    assert clean_summary_trait.total_count == 2
    assert clean_summary_trait.last_record_detail is not None
    assert clean_summary_trait.last_record_detail.record_start_time == 1766369000


async def test_refresh_with_no_records(
    clean_summary_trait: CleanSummaryTrait,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
) -> None:
    """Test refreshing with no records."""
    empty_response = {
        "total_time": 0,
        "total_area": 0,
        "total_count": 0,
        "record_list": [],
    }
    fake_channel.response_queue.append(message_builder.build(empty_response))
    await clean_summary_trait.refresh()

    assert clean_summary_trait.total_time == 0
    assert clean_summary_trait.total_area == 0
    assert clean_summary_trait.total_count == 0
    assert clean_summary_trait.last_record_detail is None


async def test_refresh_propagates_exceptions(
    clean_summary_trait: CleanSummaryTrait,
    fake_channel: FakeChannel,
) -> None:
    """Test that exceptions from channel are propagated during refresh."""
    fake_channel.publish_side_effect = RoborockException("Communication error")

    with pytest.raises(RoborockException, match="Communication error"):
        await clean_summary_trait.refresh()


async def test_get_clean_record_details_with_none_detail(
    clean_summary_trait: CleanSummaryTrait,
) -> None:
    """Test getting clean record details when some items have None detail."""
    response_with_none = {
        "total_time": 34980,
        "total_area": 28540,
        "total_count": 2,
        "record_list": [
            {
                "url": "/userdata/record_map/record1.bin",
                "detail": json.dumps(
                    {
                        "record_start_time": 1766368207,
                        "method": 0,
                        "record_use_time": 60,
                        "clean_count": 1,
                        "record_clean_area": 85,
                        "record_clean_mode": 0,
                        "record_clean_way": 0,
                        "record_task_status": 20,
                        "record_faultcode": 0,
                        "record_dust_num": 0,
                        "clean_current_map": 0,
                        "record_map_url": "/userdata/record_map/record1.bin",
                    }
                ),
            },
            {
                "url": "/userdata/record_map/record2.bin",
                "detail": None,
            },
        ],
    }

    details = await clean_summary_trait._get_clean_record_details(
        record_list=CleanRecordList.from_dict(response_with_none)
    )

    assert len(details) == 1
    assert details[0].record_start_time == 1766368207


async def test_get_clean_record_details_invalid_json(
    clean_summary_trait: CleanSummaryTrait,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that invalid JSON in detail is logged and skipped."""
    response_with_invalid_json = {
        "total_time": 34980,
        "total_area": 28540,
        "total_count": 1,
        "record_list": [
            {
                "url": "/userdata/record_map/record1.bin",
                "detail": "invalid json{",
            },
        ],
    }

    with caplog.at_level(logging.DEBUG):
        details = await clean_summary_trait._get_clean_record_details(
            record_list=CleanRecordList.from_dict(response_with_invalid_json)
        )

    assert len(details) == 0
    assert any("Failed to parse record detail" in record.message for record in caplog.records)

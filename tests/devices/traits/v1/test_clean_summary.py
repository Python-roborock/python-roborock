"""Tests for the CleanSummary class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import CleanSummary
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.clean_summary import CleanSummaryTrait
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockCommand
from tests.mock_data import CLEAN_RECORD

CLEAN_SUMMARY_DATA = [
    1442559,
    24258125000,
    296,
    [
        1756848207,
        1754930385,
        1753203976,
        1752183435,
        1747427370,
        1746204046,
        1745601543,
        1744387080,
        1743528522,
        1742489154,
        1741022299,
        1740433682,
        1739902516,
        1738875106,
        1738864366,
        1738620067,
        1736873889,
        1736197544,
        1736121269,
        1734458038,
    ],
]

CLEAN_RECORD_DATA = [
    1738864366,
    1738868964,
    4358,
    81122500,
    0,
    0,
    1,
    1,
    21,
]


@pytest.fixture
def clean_summary_trait(device: RoborockDevice) -> CleanSummaryTrait:
    """Create a DoNotDisturbTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.clean_summary


@pytest.fixture
def sample_clean_summary() -> CleanSummary:
    """Create a sample CleanSummary for testing."""
    return CleanSummary(
        clean_area=100,
        clean_time=3600,
    )


async def test_get_clean_summary_success(
    clean_summary_trait: CleanSummaryTrait, mock_rpc_channel: AsyncMock, sample_clean_summary: CleanSummary
) -> None:
    """Test successfully getting clean summary."""
    # Setup mock to return the sample clean summary
    mock_rpc_channel.send_command.side_effect = [CLEAN_SUMMARY_DATA, CLEAN_RECORD_DATA]

    # Call the method
    await clean_summary_trait.refresh()

    # Verify the result
    assert clean_summary_trait.clean_area == 24258125000
    assert clean_summary_trait.clean_time == 1442559
    assert clean_summary_trait.square_meter_clean_area == 24258.1
    assert clean_summary_trait.clean_count == 296
    assert clean_summary_trait.records
    assert len(clean_summary_trait.records) == 20
    assert clean_summary_trait.records[0] == 1756848207
    assert clean_summary_trait.last_clean_record
    assert clean_summary_trait.last_clean_record.begin == 1738864366

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [call(RoborockCommand.GET_CLEAN_SUMMARY), call(RoborockCommand.GET_CLEAN_RECORD, params=[1734458038])]
    )


async def test_get_clean_summary_clean_time_only(
    clean_summary_trait: CleanSummaryTrait, mock_rpc_channel: AsyncMock, sample_clean_summary: CleanSummary
) -> None:
    """Test successfully getting clean summary where the response only has the clean time."""

    mock_rpc_channel.send_command.return_value = [1442559]

    # Call the method
    await clean_summary_trait.refresh()

    # Verify the result
    assert clean_summary_trait.clean_area is None
    assert clean_summary_trait.clean_time == 1442559
    assert clean_summary_trait.square_meter_clean_area is None
    assert clean_summary_trait.clean_count is None
    assert not clean_summary_trait.records

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CLEAN_SUMMARY)


async def test_get_clean_summary_propagates_exception(
    clean_summary_trait: CleanSummaryTrait, mock_rpc_channel: AsyncMock
) -> None:
    """Test that exceptions from RPC channel are propagated in get_clean_summary."""

    # Setup mock to raise an exception
    mock_rpc_channel.send_command.side_effect = RoborockException("Communication error")

    # Verify the exception is propagated
    with pytest.raises(RoborockException, match="Communication error"):
        await clean_summary_trait.refresh()


async def test_get_clean_record_success(
    clean_summary_trait: CleanSummaryTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully getting the last clean record."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        CLEAN_RECORD_DATA,
    ]

    # Call the method
    clean_record = await clean_summary_trait.get_clean_record(1738864366)

    # Verify the result
    assert clean_record.begin == 1738864366
    assert clean_record.end == 1738868964
    assert clean_record.duration == 4358
    assert clean_record.area == 81122500
    assert clean_record.complete is None
    assert clean_record.start_type is None
    assert clean_record.clean_type is None
    assert clean_record.finish_reason is None

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_CLEAN_RECORD, params=[1738864366]),
        ]
    )


async def test_get_clean_record_dict_response(
    clean_summary_trait: CleanSummaryTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully getting the last clean record as a dictionary."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        CLEAN_RECORD,
    ]

    # Call the method
    clean_record = await clean_summary_trait.get_clean_record(1738864366)

    # Verify the result
    assert clean_record.begin == 1672543330
    assert clean_record.end == 1672544638
    assert clean_record.duration == 1176
    assert clean_record.area == 20965000
    assert clean_record.complete == 1
    assert clean_record.start_type == 2
    assert clean_record.clean_type == 3
    assert clean_record.finish_reason == 56
    assert clean_record.dust_collection_status == 1
    assert clean_record.avoid_count == 19
    assert clean_record.wash_count == 2
    assert clean_record.map_flag == 0

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_CLEAN_RECORD, params=[1738864366]),
        ]
    )


async def test_get_clean_summary_no_records(
    clean_summary_trait: CleanSummaryTrait, mock_rpc_channel: AsyncMock
) -> None:
    """Test successfully getting clean summary with no records."""
    # Setup mock to return the sample clean summary with no records
    mock_rpc_channel.send_command.return_value = [
        1442559,
        24258125000,
        296,
        [],
    ]

    # Call the method
    await clean_summary_trait.refresh()

    # Verify the result
    assert clean_summary_trait.clean_area == 24258125000
    assert clean_summary_trait.clean_time == 1442559
    assert clean_summary_trait.clean_count == 296
    assert not clean_summary_trait.records
    assert clean_summary_trait.last_clean_record is None

    # Verify the RPC call was made correctly
    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CLEAN_SUMMARY)

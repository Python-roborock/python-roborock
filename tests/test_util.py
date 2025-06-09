import datetime

import pytest

from roborock.util import parse_time_to_datetime


@pytest.mark.skip
def validate(start: datetime.datetime, end: datetime.datetime) -> bool:
    duration = end - start
    return duration > datetime.timedelta()


# start_date < now < end_date
def test_start_date_lower_than_now_lower_than_end_date():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() - datetime.timedelta(hours=2)).time(),
        (datetime.datetime.now() - datetime.timedelta(hours=1)).time(),
    )
    assert validate(start, end)


# start_date > now > end_date
def test_start_date_greater_than_now_greater_than_end_date():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() + datetime.timedelta(hours=1)).time(),
        (datetime.datetime.now() + datetime.timedelta(hours=2)).time(),
    )
    assert validate(start, end)


# start_date < now > end_date
def test_start_date_lower_than_now_greater_than_end_date():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() - datetime.timedelta(hours=1)).time(),
        (datetime.datetime.now() + datetime.timedelta(hours=1)).time(),
    )
    assert validate(start, end)


# start_date > now < end_date
def test_start_date_greater_than_now_lower_than_end_date():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() + datetime.timedelta(hours=1)).time(),
        (datetime.datetime.now() - datetime.timedelta(hours=1)).time(),
    )
    assert validate(start, end)


# start_date < end_date < now
def test_start_date_lower_than_end_date_lower_than_now():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() - datetime.timedelta(hours=2)).time(),
        (datetime.datetime.now() - datetime.timedelta(hours=1)).time(),
    )
    assert validate(start, end)


# start_date > end_date > now
def test_start_date_greater_than_end_date_greater_than_now():
    start, end = parse_time_to_datetime(
        (datetime.datetime.now() + datetime.timedelta(hours=2)).time(),
        (datetime.datetime.now() + datetime.timedelta(hours=1)).time(),
    )
    assert validate(start, end)

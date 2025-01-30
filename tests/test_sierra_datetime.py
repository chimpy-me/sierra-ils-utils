import pytest
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

from sierra_ils_utils import SierraDateTime, SierraDate

#
# SierraDateTime Tests
#

def test_from_string_with_explicit_offset_milliseconds():
    """Test parsing a datetime string with explicit UTC offset and milliseconds."""
    sdt = SierraDateTime.from_string("2020-07-07 08:55:00.000 -0400")
    # The expected UTC time would be 12:55:00 UTC
    assert sdt == datetime(2020, 7, 7, 12, 55, 0, tzinfo=timezone.utc)
    assert str(sdt) == "2020-07-07T12:55:00Z"

def test_from_string_with_explicit_offset_no_milliseconds():
    """Test parsing a datetime string with explicit UTC offset (no milliseconds)."""
    sdt = SierraDateTime.from_string("2020-07-07 08:55:00 -0400")
    # The expected UTC time would be 12:55:00 UTC
    assert sdt == datetime(2020, 7, 7, 12, 55, 0, tzinfo=timezone.utc)
    assert str(sdt) == "2020-07-07T12:55:00Z"

def test_from_string_with_named_tz_milliseconds():
    """Test parsing a datetime string and specifying a named timezone (with milliseconds)."""
    sdt = SierraDateTime.from_string("2025-06-10 18:45:00.0", "America/Los_Angeles")
    # 2025-06-10 18:45 in Los Angeles is UTC+8h => 2025-06-11 01:45:00 UTC
    assert sdt == datetime(2025, 6, 11, 1, 45, 0, tzinfo=timezone.utc)
    assert str(sdt) == "2025-06-11T01:45:00Z"

def test_from_string_with_named_tz_no_milliseconds():
    """Test parsing a datetime string and specifying a named timezone (no milliseconds)."""
    sdt = SierraDateTime.from_string("2025-06-10 18:45:00", "America/New_York")
    # 2025-06-10 18:45 in New York is UTC+4h => 2025-06-10 22:45:00 UTC
    assert sdt == datetime(2025, 6, 10, 22, 45, 0, tzinfo=timezone.utc)
    assert str(sdt) == "2025-06-10T22:45:00Z"

def test_from_string_fallback_to_utc_if_unparseable():
    with pytest.raises(ValueError):
        SierraDateTime.from_string("2025/06/10 18:45:00")

def test_from_iso():
    """Test creating from a standard ISO8601 string with 'Z' as UTC indicator."""
    sdt = SierraDateTime.from_iso("2025-06-10T18:45:00Z")
    assert sdt == datetime(2025, 6, 10, 18, 45, 0, tzinfo=timezone.utc)
    assert str(sdt) == "2025-06-10T18:45:00Z"

def test_from_datetime():
    """Test conversion from a regular datetime object to SierraDateTime."""
    regular_dt = datetime(2025, 6, 10, 18, 45, 0, tzinfo=timezone.utc)
    sdt = SierraDateTime.from_datetime(regular_dt)
    assert sdt == regular_dt.replace(microsecond=0)
    assert str(sdt) == "2025-06-10T18:45:00Z"

def test_now():
    """
    Test that SierraDateTime.now() returns a UTC datetime with zero microseconds.
    We'll just check tzinfo and microsecond, because exact equality to 'datetime.now()'
    might be too finicky (time difference).
    """
    sdt_now = SierraDateTime.now()
    assert sdt_now.tzinfo == timezone.utc
    assert sdt_now.microsecond == 0

#
# SierraDate Tests
#

def test_sierra_date_from_iso():
    """Test creating SierraDate from an ISO date string."""
    sdate = SierraDate.from_iso("2025-06-10")
    assert sdate == date(2025, 6, 10)
    assert str(sdate) == "2025-06-10"

def test_sierra_date_from_date():
    """Test creating SierraDate from a standard datetime.date object."""
    d = date(2025, 6, 10)
    sdate = SierraDate.from_date(d)
    assert sdate == d
    assert str(sdate) == "2025-06-10"

def test_sierra_date_today():
    """Test that SierraDate.today() returns today's date."""
    today = date.today()
    sdate_today = SierraDate.today()
    # Check that it matches the year, month, and day of 'today'
    assert sdate_today == today
    assert sdate_today.isoformat() == today.isoformat()

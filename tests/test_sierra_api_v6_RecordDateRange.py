import pytest
from datetime import datetime, timedelta
from sierra_ils_utils import RecordDateRange

def test_start_datetime():
    start_date = '2023-11-27T00:00:00'
    date_range = RecordDateRange(start_date=start_date)
    assert str(date_range) == '[2023-11-27T00:00:00Z,]'

def test_start_date():
    start_date = '2023-11-27'
    date_range = RecordDateRange(start_date=start_date)
    assert str(date_range) == '[2023-11-27,]'

def test_start_unixepoch():
    start_date = 1701139326
    date_range = RecordDateRange(start_date=start_date)
    assert str(date_range) == '[2023-11-27T21:42:06Z,]'

def test_end_datetime():
    end_date = '2023-11-27T00:00:00'
    date_range = RecordDateRange(end_date=end_date)
    assert str(date_range) == '[,2023-11-27T00:00:00Z]'

def test_end_date():
    end_date = '2023-11-27'
    date_range = RecordDateRange(end_date=end_date)
    assert str(date_range) == '[,2023-11-27]'

def test_end_unixepoch():
    end_date = 1701139326
    date_range = RecordDateRange(end_date=end_date)
    assert str(date_range) == '[,2023-11-27T21:42:06Z]'

def test_exact_date():
    exact_date = '2023-11-27'
    date_range = RecordDateRange(exact_date=exact_date)
    assert str(date_range) == '2023-11-27'


"""
"""

def test_range():
    update_dates = RecordDateRange(
        start_date='2021-12-21T00:00:00',
        end_date='2021-12-22T00:00:00'
    )
    assert str(update_dates) == '[2021-12-21T00:00:00Z,2021-12-22T00:00:00Z]'

def test_advance_range():
    update_dates = RecordDateRange(
        start_date='2021-12-21T00:00:00',
        end_date='2021-12-22T00:00:00'
    )
    assert str(update_dates) == '[2021-12-21T00:00:00Z,2021-12-22T00:00:00Z]'
 
    update_dates.advance_range('minutes=5')  # advance the interval by 5 minutes
    assert str(update_dates) == '[2021-12-22T00:00:01Z,2021-12-22T00:05:00Z]'
    
    update_dates.advance_range('minutes=5')  # advance the interval by 5 minutes
    assert str(update_dates) == '[2021-12-22T00:05:01Z,2021-12-22T00:10:00Z]'

def test_advance_range_error():
    update_date = RecordDateRange(exact_date='2021-12-21')
    try:
        # expect this to fail because we can't advance the range of an exact date
        update_date.advance_range('minutes=5')
        
    except TypeError as e:
        assert isinstance(e, TypeError)

"""
    update_date = RecordDateRange(
    start_date='2021-12-21T00:00:00',
    end_date='2021-12-22T00:00:00'
)
print(str(update_date))

try:
    update_date.advance_range('minutes=5')  # advance the interval by 5 minutes
    print(str(update_date))
except TypeError as e:
    print(e)  # this should NOT fail

try:
    update_date.advance_range('minutes=5')  # advance the interval by 5 minutes
    print(str(update_date))
except TypeError as e:
    print(e)  # this should NOT fail


    assert str(update_dates) == '[2021-12-21T00:00:00Z,2021-12-22T00:00:00Z]'
    """

# update_date = RecordDateRange(exact_date='2021-12-21')
# print(str(update_date))

# try:
#     update_date.advance_range('minutes=5')
#     isinstance(error, TypeError)
# except TypeError as e:
#     print(e)  # this should fail
#     error = e


# try:
#     update_date.advance_range('minutes=5')  # advance the interval by 5 minutes
#     print(str(update_date))
# except TypeError as e:
#     print(e)  # this should NOT fail

# try:
#     update_date.advance_range('minutes=5')  # advance the interval by 5 minutes
#     print(str(update_date))
# except TypeError as e:
#     print(e)  # this should NOT fail

# def test_date_parsing():
#     # Test parsing of different date formats
#     test_cases = [
#         {'input': '2023-11-01T00:00:00Z', 'expected': datetime(2023, 11, 1, 0, 0)},
#         {'input': '2023-11-01', 'expected': datetime(2023, 11, 1).date()},
#         {'input': 1669852800, 'expected': datetime.utcfromtimestamp(1669852800).date()}  # Example Unix timestamp
#     ]

#     for case in test_cases:
#         record = RecordDateRange(start_date=case['input'])
#         assert record.start_date == case['expected']

# def test_advance_range():
#     # Test advancing the range
#     record = RecordDateRange(start_date='2023-11-01T00:00:00Z', end_date='2023-11-10T00:00:00Z')
#     record.advance_range('days=5')
#     assert record.start_date == datetime(2023, 11, 10, 0, 0, 1)  # One second after the old end_date
#     assert record.end_date == datetime(2023, 11, 15, 0, 0)  # Advanced by 5 days

def test_advance_range_error_handling():
    # Test error handling in advance_range
    record = RecordDateRange(start_date='2023-11-01', end_date='2023-11-10')  # date objects, not datetime

    with pytest.raises(TypeError):
        record.advance_range('days=5')

# def test_format_for_api():
#     # Test the format_for_api method
#     record = RecordDateRange(start_date='2023-11-01T00:00:00Z', end_date='2023-11-10T00:00:00Z')
#     assert record.format_for_api() == '[2023-11-01T00:00:00Z,2023-11-10T00:00:00Z]'

#     record = RecordDateRange(start_date='2023-11-01')
#     assert record.format_for_api() == '[2023-11-01,]'
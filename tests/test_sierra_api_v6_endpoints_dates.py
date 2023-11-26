"""
replaced by RecordDateRange
"""

# import pytest
# from pydantic import ValidationError

# # Importing the DateOnlyRange class from the provided file
# from sierra_ils_utils.sierra_api_v6_endpoints import DateOnlyRange

# def test_instantiation():
#     dr = DateOnlyRange(exact="2021-01-01")
#     assert dr.exact == "2021-01-01"
#     assert dr.start_date is None
#     assert dr.end_date is None


# def test_exact_date():
#     dr = DateOnlyRange(exact="2021-01-01")
#     assert dr.format_for_api() == "2021-01-01"

# def test_date_range():
#     dr = DateOnlyRange(start="2021-01-01", end="2021-01-31")
#     assert dr.format_for_api() == "[2021-01-01,2021-01-31]"

#     dr2 = DateOnlyRange(start="2021-01-01")
#     assert dr2.format_for_api() == "[2021-01-01,]"

#     dr3 = DateOnlyRange(end="2021-01-31")
#     assert dr3.format_for_api() == "[,2021-01-31]"

# def test_api_format():
#     dr = DateOnlyRange(start="2021-01-01", end="2021-01-01")
#     assert dr.format_for_api() == "2021-01-01"

#     dr2 = DateOnlyRange(start="2021-01-01", end="2021-01-31")
#     assert dr2.format_for_api() == "[2021-01-01,2021-01-31]"
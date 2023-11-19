import json
import logging
import pytest
from sierra_ils_utils import BibResultSet, Bib

def test_bib_result_set_model_initialization():
    """
    Create a BibResultSet object with the bare minimum of params
    """

    test = BibResultSet(
        start=0,
        total=0,
        entries=[]
    )

    assert (test.total, test.start, test.entries) == (0, 0, [])

def test_bib_model_initialization():
    """
    create a Bib object from raw json
    """

    raw_json = """\
    {
      "id": "1000001",
      "updatedDate": "2021-10-07T13:52:27Z",
      "createdDate": "2012-06-19T22:48:06Z",
      "deleted": false,
      "suppressed": false,
      "isbn": "0899080871",
      "lang": {
        "code": "eng",
        "name": "English"
      },
      "title": "Water monsters : opposing viewpoints",
      "author": "Garinger, Alan, 1932-",
      "materialType": {
        "code": "a  ",
        "value": "Book"
      },
      "bibLevel": {
        "code": "m",
        "value": "MONOGRAPH"
      },
      "publishYear": 1991,
      "catalogDate": "1992-05-11",
      "country": {
        "code": "cau",
        "name": "California"
      },
      "callNumber": "001.944 G232, 1991"
    } \
    """

    # Parsing JSON data
    data = json.loads(raw_json)

    # Creating an instance of Bib
    bib_instance = Bib(**data)

    # Assertions for each field
    assert bib_instance.id == "1000001"
    assert bib_instance.updatedDate == "2021-10-07T13:52:27Z"
    assert bib_instance.createdDate == "2012-06-19T22:48:06Z"
    assert bib_instance.deletedDate is None
    assert bib_instance.deleted is False
    assert bib_instance.suppressed is False
    assert bib_instance.available is None
    assert bib_instance.lang.code == "eng"
    assert bib_instance.lang.name == "English"
    assert bib_instance.title == "Water monsters : opposing viewpoints"
    assert bib_instance.author == "Garinger, Alan, 1932-"
    assert bib_instance.materialType.code == "a  "
    assert bib_instance.materialType.value == "Book"
    assert bib_instance.bibLevel.code == "m"
    assert bib_instance.bibLevel.value == "MONOGRAPH"
    assert bib_instance.publishYear == 1991
    assert bib_instance.catalogDate == "1992-05-11"
    assert bib_instance.country.code == "cau"
    assert bib_instance.country.name == "California"
    assert bib_instance.orders is None
    assert bib_instance.normTitle is None
    assert bib_instance.normAuthor is None
    assert bib_instance.locations is None
    assert bib_instance.holdCount is None
    assert bib_instance.copies is None
    assert bib_instance.callNumber == "001.944 G232, 1991"
    assert bib_instance.volumes is None
    assert bib_instance.items is None
    assert bib_instance.fixedFields is None
    assert bib_instance.varFields is None
    assert bib_instance.marc is None

# from sierra_ils_utils import SierraRESTAPI
# import sierra_ils_utils
# import sierra_api_v6_endpoints.py

# import traceback

# def test_bib_result_set_with_valid_input():
#     # Example of valid input data based on the JSON you provided
#     valid_data = {
#         "total": 1,
#         "start": 0,
#         "entries": [
#             {
#                 "id": "1000001",
#                 "title": "Water monsters : opposing viewpoints",
#                 "author": "Garinger, Alan, 1932-",
#                 # ... other fields ...
#             }
#         ]
#     }

#     # Create an instance of BibResultSet with valid data
#     result_set = BibResultSet(**valid_data)
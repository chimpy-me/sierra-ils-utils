import logging
import pytest
from sierra_ils_utils import JsonManipulator
# import traceback

# logging.basicConfig(filename='app.log', level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
# logger.error(traceback.format_exc())
# logger.info(traceback.format_exc())

def test_initialize_jsonmanipulator():

    json_data = {
        'total': 3,
        'start': 0,
        'entries': [
            {
                'id': 'https://example.com/checkouts/123',
                'patron': 'https://example.com/patrons/123',
                'item': 'https://example.com/items/123',
                'barcode': 'A1234',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/124',
                'patron': 'https://example.com/patrons/124',
                'item': 'https://example.com/items/123',
                'barcode': 'A1235',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/125',
                'patron': 'https://example.com/patrons/123',
                'item': 'https://example.com/items/125',
                'barcode': 'A1236',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
        ]
    }

    # Validate the attributes after initialization
    assert JsonManipulator(json_data).json_obj == json_data


    

def test_remove_paths():
    # Validate the method remove_paths

    json_data = {
        'total': 3,
        'start': 0,
        'entries': [
            {
                'id': 'https://example.com/checkouts/123',
                'patron': 'https://example.com/patrons/123',
                'item': 'https://example.com/items/123',
                'barcode': 'A1234',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/124',
                'patron': 'https://example.com/patrons/124',
                'item': 'https://example.com/items/123',
                'barcode': 'A1235',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/125',
                'patron': 'https://example.com/patrons/123',
                'item': 'https://example.com/items/125',
                'barcode': 'A1236',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
        ]
    }

    assert JsonManipulator(json_data) \
    .remove_paths([['entries', 'patron']]) \
    .json_obj == {
        'total': 3,
        'start': 0,
        'entries': [
            {
                'id': 'https://example.com/checkouts/123',
                'item': 'https://example.com/items/123',
                'barcode': 'A1234',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/124',
                'item': 'https://example.com/items/123',
                'barcode': 'A1235',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/125',
                'item': 'https://example.com/items/125',
                'barcode': 'A1236',
                'dueDate': '2023-10-21T08:00:00Z',
                'callNumber': '005.133 PYT',
                'numberOfRenewals': 0,
                'outDate': '2023-10-07T08:00:00Z'
            },
        ]
    }

    # remove three paths
    assert JsonManipulator(json_data) \
    .remove_paths(
        [
            ['entries', 'patron'], 
            ['entries', 'dueDate'],
            ['entries', 'numberOfRenewals'],
        ]
    ) \
    .json_obj == {
        'total': 3,
        'start': 0,
        'entries': [
            {
                'id': 'https://example.com/checkouts/123',
                'item': 'https://example.com/items/123',
                'barcode': 'A1234',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/124',
                'item': 'https://example.com/items/123',
                'barcode': 'A1235',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/125',
                'item': 'https://example.com/items/125',
                'barcode': 'A1236',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
        ]
    }

    assert JsonManipulator(json_data) \
    .remove_paths(
        [
            ['entries', 'patron'], 
            ['entries', 'dueDate'],
            ['entries', 'numberOfRenewals'],
        ]
    ) \
    .json_obj == {
        'total': 3,
        'start': 0,
        'entries': [
            {
                'id': 'https://example.com/checkouts/123',
                'item': 'https://example.com/items/123',
                'barcode': 'A1234',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/124',
                'item': 'https://example.com/items/123',
                'barcode': 'A1235',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
            {
                'id': 'https://example.com/checkouts/125',
                'item': 'https://example.com/items/125',
                'barcode': 'A1236',
                'callNumber': '005.133 PYT',
                'outDate': '2023-10-07T08:00:00Z'
            },
        ]
    }

    # using remove_paths without a param should resut in a type error
    try:
        assert JsonManipulator(json_data).remove_paths() \
        .json_obj == {
            'total': 3,
            'start': 0,
            'entries': [
                {
                    'id': 'https://example.com/checkouts/123',
                    'patron': 'https://example.com/patrons/123',
                    'item': 'https://example.com/items/123',
                    'barcode': 'A1234',
                    'dueDate': '2023-10-21T08:00:00Z',
                    'callNumber': '005.133 PYT',
                    'numberOfRenewals': 0,
                    'outDate': '2023-10-07T08:00:00Z'
                },
                {
                    'id': 'https://example.com/checkouts/124',
                    'patron': 'https://example.com/patrons/124',
                    'item': 'https://example.com/items/123',
                    'barcode': 'A1235',
                    'dueDate': '2023-10-21T08:00:00Z',
                    'callNumber': '005.133 PYT',
                    'numberOfRenewals': 0,
                    'outDate': '2023-10-07T08:00:00Z'
                },
                {
                    'id': 'https://example.com/checkouts/125',
                    'patron': 'https://example.com/patrons/123',
                    'item': 'https://example.com/items/125',
                    'barcode': 'A1236',
                    'dueDate': '2023-10-21T08:00:00Z',
                    'callNumber': '005.133 PYT',
                    'numberOfRenewals': 0,
                    'outDate': '2023-10-07T08:00:00Z'
                },
            ]
        }
    except Exception as e:
        # should require a param
        assert type(e) == TypeError

    # 
    assert JsonManipulator(json_data).remove_paths(
        [
            ['entries']

        ],
    ) \
        .json_obj == {
            'total': 3,
            'start': 0,
        }
    
def test_nested_path_removal():
    """
    Nested Path Removal:

    Ensure that you can remove nested paths (e.g., paths within paths within paths...)
    """
    json_data = {"a": {"b": {"c": {"d": 1}}}}
    assert JsonManipulator(json_data).remove_paths([['a', 'b', 'c', 'd']]).json_obj == {"a": {"b": {"c": {}}}}

def test_multiple_path_removal_different_depths():
    """
    Multiple Path Removal At Different Depths:

    This test will ensure that you can remove multiple paths at various nesting levels in a single call
    """
    json_data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    assert JsonManipulator(json_data).remove_paths([['a'], ['b', 'd']]).json_obj == {"b": {"c": 2}}

def test_invalid_path_removal():
    """
    Invalid Path Removal:

    Ensure that the method behaves correctly when provided with paths that don't exist in the JSON object
    """
    json_data = {"a": 1}
    assert JsonManipulator(json_data).remove_paths([['b']]).json_obj == {"a": 1}

def test_empty_json_object():
    """
    Empty JSON Object:

    Test the behavior with an empty JSON object to ensure it doesn't error out or behave unexpectedly
    """
    assert JsonManipulator({}).remove_paths([['a']]).json_obj == {}

def test_non_dict_non_list_object():
    """
    Non-Dictionary/Non-List JSON Object:

    If the root of the JSON object isn't a dictionary or a list (e.g., a string, integer, etc.), the method should return the JSON object unchanged.
    """
    assert JsonManipulator(1).remove_paths([['a']]).json_obj == 1

def test_complex_json(): 
    """
    Complex JSON Structures:

    Mix dictionaries and lists in various nesting structures and test path removal. This will ensure the method can handle complex JSON structures.
    """
    json_data = {
        "a": [
            {
                "b": 1
            }, 
            {
                "c": {
                    "d": 2
                }
            }, 
            3
        ]
    }
    assert JsonManipulator(json_data).remove_paths([['a', 'c']]).json_obj == {"a": [{"b": 1}, {}, 3]}

def test_invalid_path_format():
    """
    Invalid Path Format:

    Test with invalid path formats (e.g., not a list, or containing non-string/non-int elements) and ensure the method behaves gracefully (e.g., raises an appropriate exception or ignores the invalid path).
    """
    json_data = {"a": 1}
    try:
        JsonManipulator(json_data).remove_paths('a')
    except Exception as e:
        assert isinstance(e, ValueError)
    finally:
        assert True
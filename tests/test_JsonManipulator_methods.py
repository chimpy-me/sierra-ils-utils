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
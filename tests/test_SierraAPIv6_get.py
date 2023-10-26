import logging
import pytest
from sierra_ils_utils import SierraRESTAPI
import traceback

# logging.basicConfig(filename='app.log', level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
# logger.error(traceback.format_exc())
# logger.info(traceback.format_exc())


def test_get_raw_response(mocker):
    # Mock the requests.post method to always return a successful response for the auth
    mock_auth_response = mocker.Mock()
    mock_auth_response.status_code = 200
    mock_auth_response.text = "{}"
    mock_auth_response.json.return_value = {
        'access_token': 'mocked_test_token',
        'expires_in': '3600'
    }
    mocker.patch('requests.Session.post', return_value=mock_auth_response)  # patch requests.Session.post so that it responds with the above
    
    # Initialize the API object
    sierra_api = SierraRESTAPI(
        sierra_api_base_url="http://sierra.library.org/",
        sierra_api_key="api_key", 
        sierra_api_secret="api_secret"
    )
    
    # Mock the requests.get method to return a successful response for the actual GET request
    mock_get_response = mocker.Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
            "total": 640865,
            "start": 0,
            "entries": [
                {
                    "id": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/patrons/checkouts/82748936",
                    "patron": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/patrons/123",
                    "item": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/items/123",
                    "barcode": "A000000000001",
                    "dueDate": "2023-10-20T08:00:00Z",
                    "callNumber": "973.933 T871Zta 2023",
                    "numberOfRenewals": 0,
                    "outDate": "2023-09-08T14:48:42Z"
                }
            ]
        }
    mocker.patch('requests.Session.get', return_value=mock_get_response)  # patch requests.Session.get so that it responds with the above

    results = sierra_api.get('items/checkouts', params={"limit": 1, "offset": 0})
    
    assert results.raw_response.json()['total'] == 640865

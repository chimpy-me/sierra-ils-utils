import logging
import pytest
from sierra_ils_utils import SierraAPIv6
import traceback


logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.error(traceback.format_exc())
logger.info(traceback.format_exc())

def test_initialize_session():
    # Initialize the API object
    sierra_api = SierraAPIv6(
        sierra_api_base_url="http://sierra.library.org/", 
        sierra_api_key="api_key", 
        sierra_api_secret="api_secret"
    )
    
    # Validate the attributes after initialization
    assert sierra_api.request_count == 0
    assert sierra_api.expires_at == 0
    assert sierra_api.session.headers == {
        'accept': 'application/json',
        'Authorization': '',
    }


def test_authenticate(mocker):
    # Mock the requests.post method to always return a successful response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "{}"
    # mock_response.text = "{}"  # This simulates an empty JSON body
    # mock_response.json.side_effect = ValueError("No JSON object could be decoded")  # This will raise an error if .json() is called
    mock_response.json.return_value = {
        'access_token': 'mocked_test_token',
        'expires_in': '3600'
    }
    
    mocker.patch('requests.Session.post', return_value=mock_response)  # patch requests.Session.post so that it responds with the above
    
    # Initialize the API object and call the authenticate decorated method
    sierra_api = SierraAPIv6(
        sierra_api_base_url="http://sierra.library.org/",
        sierra_api_key="api_key", 
        sierra_api_secret="api_secret"
    )
    
    # For demonstration purposes, I'm just calling the 'get' method which uses the 'authenticate' decorator
    response = sierra_api.get('info/token')
    
    # Validate that the Authorization header was set correctly
    assert sierra_api.session.headers['Authorization'] == 'Bearer mocked_test_token'
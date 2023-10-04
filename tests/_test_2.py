from unittest.mock import patch, Mock
import pytest
from sierra_ils_utils import SierraAPIv6

mock_auth_response = Mock()
mock_auth_response.status_code = 200

mock_auth_response.json.return_value = {
    'keyId': 'mock_key',
    'grantType': 'client_credentials',
    'authorizationScheme': 'Bearer',
    'expiresIn': 3600,
    'roles': []
}

@patch('requests.Session.post', return_value=mock_auth_response)
def test_authentication(mock_post):
    config = {
        'sierra_api_base_url': 'http://mock.url/',
        'sierra_api_key': 'mock_key',
        'sierra_api_secret': 'mock_secret'
    }
    
    sierra_api = SierraAPIv6(
        sierra_api_base_url=config['sierra_api_base_url'],
        sierra_api_key=config['sierra_api_key'],
        sierra_api_secret=config['sierra_api_secret']
    )

    sierra_api.get('info/token')

    # Check if your class correctly set the authorization token
    assert sierra_api.session.headers['Authorization'] == 'Bearer mock_token'

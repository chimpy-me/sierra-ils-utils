# TODO: rewrite expand on this


# import logging
# import pytest
# from sierra_ils_utils import SierraRESTAPI, SierraAPIResponse
# import traceback
# from pydantic import BaseModel
# import requests

# class MockResponse(BaseModel):
#     # Assuming SierraAPIResponse has these fields
#     response_model_name: str
#     data: dict
#     raw_response: requests.Response

#     class Config:
#         arbitrary_types_allowed = True

# def test_get_raw_response(mocker):
#     # Mock the requests.post method for authentication
#     mock_auth_response = mocker.Mock()
#     mock_auth_response.status_code = 200
#     mock_auth_response.json.return_value = {
#         'access_token': 'mocked_test_token',
#         'expires_in': '3600'
#     }
#     mocker.patch('requests.Session.post', return_value=mock_auth_response)

#     # Initialize the API object
#     sierra_api = SierraRESTAPI(
#         sierra_api_base_url="http://sierra.library.org/",
#         sierra_api_key="api_key", 
#         sierra_api_secret="api_secret"
#     )
    
#     # Mock the requests.get method for the actual GET request
#     mock_get_response = mocker.Mock()
#     mock_get_response.status_code = 200
#     mock_get_response.json.return_value = {
#             "total": 640865,
#             "start": 0,
#             "entries": [
#                 {
#                     "id": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/patrons/checkouts/82748936",
#                     "patron": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/patrons/123",
#                     "item": "https://classic.cincinnatilibrary.org/iii/sierra-api/v6/items/123",
#                     "barcode": "A000000000001",
#                     "dueDate": "2023-10-20T08:00:00Z",
#                     "callNumber": "973.933 T871Zta 2023",
#                     "numberOfRenewals": 0,
#                     "outDate": "2023-09-08T14:48:42Z"
#                 }
#             ]
#         }
#     mocker.patch('requests.Session.get', return_value=mock_get_response)

#     # Call the API and get the result
#     results = sierra_api.get('items/checkouts', params={"limit": 1, "offset": 0})
    
#     # Create a mock SierraAPIResponse object for assertion
#     mock_api_response = MockResponse(
#         response_model_name='TestModel',
#         data=mock_get_response.json(),
#         raw_response=mock_get_response,
#         status_code=200
#     )

#     # Assert the result using the mock SierraAPIResponse
#     assert results.data == mock_api_response.data
#     assert results.raw_response.json()['total'] == mock_api_response.data['total']

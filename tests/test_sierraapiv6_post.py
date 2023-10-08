# import logging
# import pytest
# from sierra_ils_utils import SierraAPIv6
# import traceback

# logging.basicConfig(filename='app.log', level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
# logger.error(traceback.format_exc())
# logger.info(traceback.format_exc())

# def test_initialize_session():
#     # Initialize the API object
#     sierra_api = SierraAPIv6(
#         sierra_api_base_url="http://sierra.library.org/", 
#         sierra_api_key="api_key", 
#         sierra_api_secret="api_secret"
#     )
    
#     # Validate the attributes after initialization
#     assert sierra_api.request_count == 0
#     assert sierra_api.expires_at == 0
#     assert sierra_api.session.headers == {
#         'accept': 'application/json',
#         'Authorization': '',
#     }


# mock_response.text = "{}"
#     # mock_response.text = "{}"  # This simulates an empty JSON body
#     # mock_response.json.side_effect = ValueError("No JSON object could be decoded")  # This will raise an error if .json() is called
#     mock_response.json.return_value = {
#         'access_token': 'mocked_test_token',
#         'expires_in': '3600'
#     }
    
#     mocker.patch('requests.Session.post', return_value=mock_response)  # patch requests.Session.post so that it responds with the above
    
#     # Initialize the API object and call the authenticate decorated method
#     sierra_api = SierraAPIv6(
#         sierra_api_base_url="http://sierra.library.org/",
#         sierra_api_key="api_key", 
#         sierra_api_secret="api_secret"
#     )

# def test_post(mocker):
#     # Mock the requests.post method to always return a successful response
#     mock_response = mocker.Mock()
#     mock_response.status_code = 201
#     mock_response.text = '{"result": "success"}'
#     mock_response.json.return_value = {
#         'result': 'success'
#     }
    
#     mocker.patch('requests.Session.post', return_value=mock_response)
    
#     # Initialize the API object
#     sierra_api = SierraAPIv6(
#         sierra_api_base_url="http://sierra.library.org/",
#         sierra_api_key="api_key", 
#         sierra_api_secret="api_secret"
#     )
    
#     # Call the post method
#     data_payload = {"key": "value"}
#     response = sierra_api.post('test_endpoint', data=data_payload)
    
#     # Validate that the response is as expected
#     assert response.json()['result'] == 'success'
    

# def test_post_fail(mocker):
#     # Mock the requests.post method to return a failed response
#     mock_response = mocker.Mock()
#     mock_response.status_code = 400
#     mock_response.text = '{"error": "bad request"}'
#     mock_response.json.return_value = {
#         'error': 'bad request'
#     }
    
#     mocker.patch('requests.Session.post', return_value=mock_response)
    
#     # Initialize the API object
#     sierra_api = SierraAPIv6(
#         sierra_api_base_url="http://sierra.library.org/",
#         sierra_api_key="api_key", 
#         sierra_api_secret="api_secret"
#     )
    
#     # Call the post method and expect it to raise an exception
#     with pytest.raises(Exception, match=r"POST response non-200 : .*"):
#         data_payload = {"key": "value"}
#         sierra_api.post('test_endpoint', data=data_payload)
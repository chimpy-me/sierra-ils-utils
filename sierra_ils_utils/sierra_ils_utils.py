from .decorators import hybrid_retry_decorator, authenticate
import logging
from random import uniform
import requests
from .sierra_api_v6_models import BibResultSet, ErrorCode
from time import sleep, time
from typing import Any, Dict

# Set up the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set default level, but this can be configured elsewhere

class SierraAPIv6:
    """
    SierraAPIv6 class provides methods for tasks involving interacting with the Sierra API
    
    Expects:
    sierra_api_base_url : URL for the base of the API e.g. `https://sierra.library.edu/iii/sierra-api/v6/`
    sierra_api_key,
    sierra_api_secret

    Dates in this API are in ISO 8601 date-time string format. 
    Ranges of dates can be represted as a string like this:
    `[2013-09-03T13:17:45Z,2013-09-03T13:37:45Z]`
    """
    def __init__(
            self,
            sierra_api_base_url,
            sierra_api_key,
            sierra_api_secret,
        ):
        self.logger = logger
        
        self.base_url = sierra_api_base_url
        self.api_key = sierra_api_key
        self.api_secret = sierra_api_secret

        self._endpoints = {
            "bibs": {
                "GET": {
                    "path": "bibs/",
                    "responses": {
                        200: BibResultSet,
                        400: ErrorCode,
                        404: ErrorCode
                        # ... other potential status codes and their corresponding models
                    },
                    "model": BibResultSet
                },
                "DELETE": {
                    "path": "bibs/",
                    "responses": {
                        200: None,
                        204: None,
                        400: ErrorCode,
                        404: ErrorCode
                    },
                    "model": ErrorCode
                }
            }
        }

        # store common urls here?
        self.token_url = self.base_url + 'token'

        # finally init the session
        self._initialize_session()

    def _initialize_session(self):
        self.request_count = 0
        # (expires_at is an interger "timestamp" --seconds since UNIX Epoch
        self.expires_at = 0
        
         # set up a requests session object
        self.session = requests.Session()

        # set the default session headers
        self.session.headers = {
            'accept': 'application/json',
            'Authorization': '',
        }

    @hybrid_retry_decorator()
    @authenticate
    def get(self, endpoint, params=None):
        """
        Sends a GET request to the specified endpoint.
        
        Args:
        - endpoint (str): The API endpoint (relative to the base URL).
        - params (dict, optional): Query parameters for the GET request.

        Returns:
        - Response object from the request.
        - None if the response is not 200, but indicates that there are no records 
          (404 is not an error, just part of the sierra rest design)
        """
        
        endpoint = self.base_url + endpoint

        self.request_count += 1

        # Send the GET request
        # self.logger.info(f"Session.get ({self.request_count} / {self.max_request_count} before session refresh) {endpoint} ...")
        # self.logger.info(f"GET {\"enpoint\": \"{endpoint}\", \"params\": \"{params}\"}")
        self.logger.info(f'GET {{"endpoint": "{endpoint}"}}')
        self.logger.info(f'GET {{"params": "{params}"}}')
        
        # send the get request
        response = self.session.get(
            self.base_url.rstrip('/') + '/info/token'
        )

        response = self.session.get(endpoint, params=params)
        if response.status_code != 200:
            self.logger.info(f"GET response non-200 : {response.text}")
            # 404 responses are "ok" in this context ... maybe other status codes?
            if response.status_code not in (404,):
                self.logger.info(f"Error: {response.text}")
                raise Exception(f"GET response non-200 : {response.text}")
            else:
                self.logger.info(f"GET {response.url} {response.status_code} ❎")
                return None

        self.logger.info(f"GET {response.url} {response.status_code} ✅")
        
        return response
    
    @hybrid_retry_decorator()
    @authenticate
    def post(self, endpoint, data=None, json=None, headers=None):
        """
        Sends a POST request to the specified endpoint.
        
        Args:
        - endpoint (str): The API endpoint (relative to the base URL).
        - data (dict or bytes or str, optional): Data to send in the POST request body.
        - json (dict, optional): JSON data to send in the POST request body.
        - headers (dict, optional): Additional headers to include in the request.

        Returns:
        - Response object from the request.
        """
        
        endpoint = self.base_url + endpoint

        self.request_count += 1

        if headers:
            # Merge with existing session headers
            headers = {**self.session.headers, **headers}
        else:
            headers = self.session.headers

        # Send the POST request
        self.logger.info(f'POST {{"endpoint": "{endpoint}"}}')
        if data:
            self.logger.info(f'POST data {{"data": "{data}"}}')
        if json:
            self.logger.info(f'POST json {{"json": "{json}"}}')
        
        response = self.session.post(endpoint, data=data, json=json, headers=headers)
        
        if response.status_code not in (200, 201, 204):  # 200 OK, 201 Created, 204 No Content
            self.logger.info(f"POST response non-200 : {response.text}")
            raise Exception(f"POST response non-200 : {response.text}")

        self.logger.info(f"POST {response.url} {response.status_code} ✅")
        
        return response
    
    def request_endpoint(
        self, 
        endpoint: str, 
        http_method: str, 
        params: Dict[str, Any] = {}, 
        **path_params
    ) -> Any:
        """
        Make a generic request to a defined endpoint in the Sierra API.
        """
        # Get the endpoint configuration
        endpoint_data = self._endpoints[endpoint][http_method]

        # Format the path with any provided path parameters (e.g., bib_id for DELETE)
        path = endpoint_data["path"].format(**path_params)

        # Use existing methods to ensure authentication and make the request

        if http_method == "GET":
            response = self.get(
                endpoint_data["path"].format(**path_params), 
                params=params
            )
        elif http_method == "POST":
            response = self.post()

        # Check the HTTP status code and parse the response using the associated model
        model = endpoint_data["responses"].get(response.status_code)
        if model:
            return model(**response.json())
        else:
            response.raise_for_status()  # Raise an exception for unexpected status codes


class JsonManipulator:
    def __init__(self, json_obj):
        self._json_obj = json_obj

    def remove_paths(self, paths, current_obj=None):
        """
        Remove specified paths from a JSON object. A path represents 
        a precise sequence of keys leading to a specific value.
    
        This method is particularly useful when wanting certain parts 
        of the JSON object to be ignored, e.g., during a json_diff operation.

        Parameters:
        - paths (List[List[str]]): 
            A list of paths to be removed. Each path is represented
            as a list of keys.
        - current_obj (Optional[dict]): 
            The current JSON object being operated on during 
            recursion. This parameter is mostly used internally and 
            typically doesn't need to be provided by the user.

        Returns:
        - None: The input JSON object is modified in place.
        """
        if current_obj is None:
            current_obj = self._json_obj

        # Base cases
        if not paths or not isinstance(current_obj, dict):
            return self  # Always return self for method chaining

        for path in paths:
            # If the first key of the path exists in the dictionary:
            if path and path[0] in current_obj:
                # If this is the last key in the path, delete it from the object
                if len(path) == 1:
                    del current_obj[path[0]]
                else:
                    # If the next object is a list:
                    if isinstance(current_obj[path[0]], list):
                        for item in current_obj[path[0]]:
                            if isinstance(item, dict) and path[1] in item:
                                self.remove_paths([path[1:]], current_obj=item)
                    else:
                        # Recursively navigate to the next level with the shortened path
                        self.remove_paths([path[1:]], current_obj=current_obj[path[0]])

        return self  # Ensure that we always return self for method chaining

    @property
    def json_obj(self):
        return self._json_obj
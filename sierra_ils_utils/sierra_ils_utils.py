from .decorators import hybrid_retry_decorator, authenticate
import json
from .sierra_api_v6_endpoints import endpoints
import logging
from pydantic import BaseModel
import requests
from typing import Literal
from time import sleep, time

# Set up the logger at the module level
logger = logging.getLogger(__name__)

class SierraAPIResponse:
    """
    SierraAPIResponse is the default return type for SierraRESTAPI
    """
    def __init__(
            self,
            response_model_name: str,
            data: BaseModel, 
            raw_response: requests.Response
        ):
        self.response_model_name = response_model_name
        self.data = data
        self.raw_response = raw_response
        self.status_code = raw_response.status_code

    def __str__(self) -> str:
        """
        implements the string method for the response
        """
        
        data_str  = f"\"status code\":         \"{self.status_code}\"\n"
        data_str += f"\"response model data\": "
        data_str += self.data.json(indent=4) if self.data else "{}"
        
        return data_str
    
    def __repr__(self):
        """
        this is so the notebook automatically displays the string representation of the last expression
        """
        return self.__str__()

class SierraRESTAPI:
    """
    SierraAPIv6 class provides methods for tasks involving interacting with the Sierra API
    
    Expects:
    sierra_api_base_url : URL for the base of the API e.g. `https://sierra.library.edu/iii/sierra-api/v6/`
    sierra_api_key,
    sierra_api_secret

    Dates in this API are in ISO 8601 date-time string format. 
    Ranges of dates can be represented as a string like this:
    `[2013-09-03T13:17:45Z,2013-09-03T13:37:45Z]`
    """
    def __init__(
            self,
            sierra_api_base_url,
            sierra_api_key,
            sierra_api_secret,
            endpoints=endpoints,  # default to the latest set of endpoints. e.g. .sierra_api_v6_endpoints import endpoints
            log_level=logging.WARNING,  # default the logger to only display warnings
        ):

        self.logger = logger
        self.logger.setLevel(log_level)
        
        self.base_url = sierra_api_base_url
        self.api_key = sierra_api_key
        self.api_secret = sierra_api_secret

        self.endpoints = endpoints

        # store common urls here?
        self.token_url = self.base_url + 'token'

        # finally init the session
        self._initialize_session()

    def _initialize_session(self):
        self.request_count = 0
        # (expires_at is an integer "timestamp" --seconds since UNIX Epoch
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
    def get(self, template, *args, **kwargs):
        """
        Sends a GET request to the specified endpoint.

        Args:
        - template (str): The API endpoint (relative to the base URL).
        - *args: Variable list of arguments to be passed to the requests.get() method.
        - **kwargs: Arbitrary keyword arguments to be passed to the requests.get() method. 
                Commonly used ones include 'params' for query parameters and 'headers' for request headers.
                NOTE : use path_params for dynamic endpoints ... 
                e.g. : sierra_api.get("items/{id}/", path_params={'id': 1234})

        Returns:
        - SierraAPIResponse object containing:
        - .data: The parsed data as a Pydantic model.
        - .raw_response: The raw Response object from the request.
        
        Note:
        A 404 status code is not treated as an error; it indicates that there are no records 
        as per the Sierra REST design.
        """

        # Extract path parameters from kwargs
        path_params = kwargs.pop('path_params', {})
        path = template.format(**path_params)

        # Validate that the endpoint is defined 
        if template not in self.endpoints['GET']:
            raise ValueError(f"Endpoint: {path} not defined in endpoints")

        # ensure that the endpoint_url is properly formatted
        endpoint_url = self.base_url.rstrip('/') + '/' + path.lstrip('/')

        self.request_count += 1

        # Log the request being made
        self.logger.info(f'GET {{"endpoint": "{endpoint_url}", "params": "{kwargs.get("params", {})}"}}')

        # Send the GET request
        response = self.session.get(endpoint_url, *args, **kwargs)

        # Check for non-200 responses
        if response.status_code != 200:
            self.logger.warning(f"GET response non-200 : {response.text}")
            if response.status_code not in (404,):
                self.logger.error(f"Error: {response.text}")
                raise Exception(f"GET response non-200 : {response.text}")
            else:
                self.logger.info(f"GET {response.url} {response.status_code} ❎")
                return None

        self.logger.info(f"GET {response.url} {response.status_code} ✅")

        # Parse the response using the appropriate Pydantic model
        expected_model = self.endpoints["GET"][template]["response_model"]
        
        # initialize the model name to None
        model_name = None

        try:
            # parsed_data = expected_model.model_validate(response.json())  # pydantic v2
            parsed_data = expected_model.parse_obj(response.json())
            model_name = expected_model.__name__
        except Exception as e:
            self.logger.error(f"Error: {e}")
            parsed_data = None

        return SierraAPIResponse(model_name, parsed_data, response)
    
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
            self.logger.warning(f"POST response non-200 : {response.text}")  # warn of a non-200 response
            raise Exception(f"POST response non-200 : {response.text}")

        self.logger.info(f"POST {response.url} {response.status_code} ✅")
        
        return response


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


# Define the Pydantic models for the SierraQueryBuilder

class Target(BaseModel):
    record_type: Literal['bib', 'item']   # TODO more / others
    field_tag: str                        # TODO Literals? Fixed Fields?


class Expression(BaseModel):
    operation: Literal['has', 'equals']   # TODO more / others
    operands: list


class LogicalOperator(BaseModel):
    operator: Literal['and', 'or', 'not']  # TODO is this it?


class Query(BaseModel):
    target: Target
    expression: Expression


class SierraQueryBuilder:
    """
    Builds queries for Create Lists and SierraRESTAPI endpoints 
    """
    def __init__(self):
        self.query = {
            "queries": []
        }

    def add_simple_query(
        self,
        query: Query  # Target, and Expression 
    ):
        self.query["queries"].append(query)

    def add_logical_operator(
        self,
        logical_operator:LogicalOperator
    ):
        # ensure that the previous element of queries is a Query
        if self.query["queries"] and isinstance(self.query["queries"][-1], Query):
            self.queries.append(logical_operator)
        else:
            raise ValueError("Cannot add a LogicalOperator before adding a Query or after another LogicalOperator.")
        
    def build_query(self):
        """
        Validate and build the final query.
        :return: String representation of the JSON query.
        """
            
        return self.query

    def __str__(self):
        """
        Returns the string representation of the JSON query.
        :return: String representation of the JSON query.
        """
        return json.dumps(self.build_query(), indent=2)


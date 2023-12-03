from .decorators import hybrid_retry_decorator, authenticate
import json
from .sierra_api_v6_endpoints import endpoints, Version
import logging
from pydantic import BaseModel
import requests
from typing import Literal, Dict
from time import sleep, time

# Set up the logger at the module level
logger = logging.getLogger(__name__)

class SierraAPIResponse:
    """
    SierraAPIResponse is the default return type for SierraRESTAPI / SierraAPI
    """
    def __init__(
            self,
            response_model_name: str,
            data: BaseModel, 
            raw_response: requests.Response,
            # prepared_request: requests.PreparedRequest
        ):

        self.response_model_name = response_model_name
        self.data = data
        self.raw_response = raw_response
        # self.prepared_request = prepared_request
        self.status_code = raw_response.status_code

    def __str__(self) -> str:
        """
        implements the string method for the response
        """
        
        data_str  = f"\"status_code\"          : \"{self.status_code}\"\n"
        data_str += f"\"response_model_name\"  : \"{self.response_model_name}\"\n"
        data_str += f"\"response_model_data\"  : \""
        data_str += self.data.json(indent=4) if self.data else "{}"
        
        return data_str
    
    def __repr__(self):
        """
        this is so a notebook automatically displays the string representation of the last expression
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

        # TODO make it easier to switch versions of the endpoints?

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

        # Log the init
        # self.logger.debug(f"INIT base_url: {self.base_url} endpoints version : {Version}")
        # self.logger.debug(f"INIT session.headers: {self.session.headers} self. : {Version}")
        self.logger.debug(f"INIT {self.info()}")

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
    
    def info(self) -> Dict:
        """
        returns a dict of the current status of the class
        """

        try:
            # mask all but 8 chars of the key
            masked_key = self.api_key[:8] + '*' * (len(self.api_key) - 8)
        except Exception as e:
            self.logger.warning(f"Error creating masked_key: {e}")
            masked_key = ""

        return {
            "base_url":         self.base_url,
            # "api_key":          self.api_key,
            "api_key":          masked_key,
            "request_count":    self.request_count,
            "expires_at":       self.expires_at,
            "session_headers":  self.session.headers,
            "endpoints":        self.endpoints,
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
                Currently used kwargs include: 
                    - 'params' for query parameters
                    - 'path_params' for dynamic endpoints
                        NOTE
                        e.g. : sierra_api.get("items/{id}", path_params={'id': 1234})
                    - TODO: consider others, like adding to the headers? .. possibly?
                
        Returns:
        - SierraAPIResponse object containing:
            - .data: The parsed data as a Pydantic model.
            - .raw_response: The raw Response object from the request.
        
        Note:
        A 404 status code is not treated as an error; it indicates that there are no records 
        as per the Sierra REST design.
        """

        # extract the params from the kwarg
        params = kwargs.pop('params', {})

        # Extract path parameters from kwargs
        path_params = kwargs.pop('path_params', {})
        
        # use the extracted path parameters to format the template 
        # e.g. 'items/{id}' -> 'items/{123}'
        path = template.format(**path_params)

        # ensure that the endpoint_url is properly formatted with the given path
        endpoint_url = self.base_url.rstrip('/') + '/' + path.lstrip('/')

        # Validate that the endpoint is defined 
        if template not in self.endpoints['GET']:
            raise ValueError(f"Endpoint: {template} not defined in endpoints")
        
        # ensure that the endpoint_url is properly formatted
        endpoint_url = self.base_url.rstrip('/') + '/' + path.lstrip('/')

        # Log the request being made
        self.logger.debug(f'GET {{"endpoint": "{endpoint_url}", "params": "{params}"}}')

        # Send the GET request
        response = self.session.get(
            endpoint_url, 
            params=params, 
            **kwargs
        )
        
        self.request_count += 1
        self.logger.debug(f'request count: {self.request_count}')

        # Check for non-200 responses
        if response.status_code != 200:
            self.logger.warning(f"GET response non-200 : {response.text}")
            if response.status_code not in (404,):
                self.logger.error(f"Error: {response.text}")
                raise Exception(f"GET response non-200 : {response.text}")
            else:
                self.logger.debug(f"GET {response.url} {response.status_code} ❎")
                return None

        self.logger.debug(f"GET {response.url} {response.status_code} ✅")

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

        return SierraAPIResponse(
            model_name, 
            parsed_data, 
            response
        )
    
    @hybrid_retry_decorator()
    @authenticate
    # def post(self, template, json_body, *args, **kwargs):
    def post(
        self, 
        template, 
        params=None, 
        json_body=None
    ):
        """
        Sends a POST request to the specified endpoint.

        Args:
        - template (str): The API endpoint (relative to the base URL).
        - *args: Variable list of arguments to be passed to the requests.post() method.
        - **kwargs: Arbitrary keyword arguments to be passed to the requests.post() method. 
                Currently used kwargs include: 
                    - 'params' for query parameters
                    - 'json_str' the json for the body of the post request 
                        NOTE
                        this should be the string representation of the json:
                        e.g. '{}'
        - json_body: either a string, or a python dict can be sent as the body
                
        Returns:
        - SierraAPIResponse object containing:
            - .data: The parsed data as a Pydantic model.
            - .raw_response: The raw Response object from the request.
        """

        # extract the params from the kwarg
        params = params if params else {}

        # we shouldn't need to format a path parameter for post endpoints ... i don't think
        # # Extract path parameters from kwargs
        # path_params = kwargs.pop('path_params', {})
        # path = template.format(**path_params)
        path = template

        # ensure that the endpoint_url is properly formatted with the given path
        endpoint_url = self.base_url.rstrip('/') + '/' + path.lstrip('/')

        # Validate that the endpoint is defined 
        logger.debug(f'"template": {template}')
        if template not in self.endpoints['POST']:
            raise ValueError(f"Endpoint: {path} not defined in endpoints")

        # check if the json_body is a dict or a string ... else raise a value error
        if isinstance(json_body, dict):
            # kwargs['json'] = json_body
            json_body = json_body if json_body else {}
        
        elif isinstance(json_body, str):
            # convert the json_body to a dict
            try:
                json_body = json.loads(json_body)
            except:
                e = ValueError('json_body: must be valid json')
                raise e
                # self.logger.error(f"Error: {e}")
        else:
            raise ValueError('json_body: must be of type `str` or `dict`')
        
        # Log the request being made
        self.logger.debug(f'POST {{"endpoint": "{endpoint_url}", "params": "{params}", "json_body": "{json_body}"}}')
        
        # create a request object and then prepare it
        request = requests.Request(
            method='POST', 
            url=endpoint_url,
            params=params,
            json=json_body
        )
        # prepare the request with the session
        prepared_request = self.session.prepare_request(request)

        # send the prepared request (POST)
        response = self.session.send(prepared_request)
        self.request_count += 1

        debug_text = (
            f'"response.status_code": {response.status_code}, ' +
            f'"prepared_request.url": {prepared_request.url}, ' +
            f'"prepared_request.params": {json.dumps(params)}, ' +  # Convert params to a JSON string
            f'"prepared_request.body": {prepared_request.body.decode("utf-8")}, ' +
            f'"request_count": {self.request_count}'
        )
        self.logger.debug(debug_text)

        # Check for non-200 responses
        if response.status_code != 200:
            self.logger.warning(f"POST response non-200 : {response.text}")
            if response.status_code not in (404,):
                self.logger.error(f"Error: {response.text}")
                raise Exception(f"GET response non-200 : {response.text}")
            else:
                self.logger.debug(f"POST {response.url} {response.status_code} ❎")
                return None

        self.logger.debug(f"POST {response.url} {response.status_code} ✅")

        # Parse the response using the appropriate Pydantic model
        expected_model = self.endpoints["POST"][template]["response_model"]
        
        # initialize the model name to None
        model_name = None

        try:
            # parsed_data = expected_model.model_validate(response.json())  # pydantic v2
            parsed_data = expected_model.parse_obj(response.json())
            model_name = expected_model.__name__
        except Exception as e:
            self.logger.error(f"Error: {e}")
            parsed_data = None

        return SierraAPIResponse(
            model_name, 
            parsed_data,
            # prepared_request, 
            response,
        )


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


class SierraQueryBuilder:
    def __init__(self):
        self.queries = []
        self.current_query = None

    def start_query(self, record_type, field_tag):
        if self.current_query is not None:
            raise ValueError("Previous query not ended. Use end_query to finish.")
        self.current_query = {
            "target": {
                "record": {"type": record_type},
                "field": {"tag": field_tag}
            },
            "expr": []
        }
        return self

    def add_expression(self, op, operands):
        if self.current_query is None:
            raise ValueError("No active query. Use start_query to begin.")
        if not isinstance(operands, list):
            operands = [operands]
        self.current_query["expr"].append(
            {
                "op": op, 
                "operands": operands
            }
        )
        return self

    # def end_query(self):
    #     if self.current_query is None:
    #         raise ValueError("No active query to end.")
    #     if len(self.current_query["expr"]) == 1:
    #         self.current_query["expr"] = self.current_query["expr"][0]
    #     self.queries.append(self.current_query)
    #     self.current_query = None
    #     return self

    def end_query(self):
        if self.current_query is None:
            raise ValueError("No active query to end.")
        if not self.current_query["expr"]:
            raise ValueError("No expression added to the query.")
        """
        TODO:

        I don't know if there's a mistake in the manual, or if this works
        differently for different situations, but it seems like the docs
        present the `expr` portion of the query as simply being an object
        and in the case of compiling barcodes, it's an array.

        Here's a bit of code that could make it produce just a single
        object when there's only one, but I don't know if it's intended
        to "piece multiple expressions together" or what.

        if len(self.current_query["expr"]) == 1:
            self.current_query["expr"] = self.current_query["expr"][0]
        """
        self.queries.append(self.current_query)
        self.current_query = None
        return self

    def build(self):
        if self.current_query is not None:
            raise ValueError("Query not ended. Use end_query to finish.")
        if len(self.queries) == 1:
            return self.queries[0]
        return {"queries": self.queries}

    def json(self):
        return json.dumps(self.build(), indent=2)

    def __str__(self):
        return self.json()

    def __repr__(self):
        return self.__str__()


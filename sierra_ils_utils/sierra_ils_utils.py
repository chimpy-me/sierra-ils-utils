import asyncio
from .decorators import hybrid_retry_decorator, authenticate
import httpx
import json
from .sierra_api_v6_endpoints import endpoints, Version
import logging
from pydantic import BaseModel
from pymarc import Record
from time import sleep, time
from typing import Literal, Dict, Union, Any, Optional

# Set up the logger at the module level
logger = logging.getLogger(__name__)

class SierraAPIResponse(BaseModel):
    """
    SierraAPIResponse is the default return type for SierraRESTAPI / SierraAPI

    response_model_name: str  # the name of the Sierra model that has been returned
    data: Optional[Any]  # the model itself
    raw_response: httpx.Response  # the raw response from the httpx request
    """

    response_model_name: str
    data: Optional[Any]  # Adjust this type hint as needed
    # raw_response: requests.Response
    raw_response: httpx.Response

    class Config:
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        """
        Implements the string method for the response.
        """

        # Check if self.data is a Pydantic model and convert to dict, else use as is
        data_repr = self.data.dict() if hasattr(self.data, "dict") else self.data

        return json.dumps(
            {
                'raw_response': str(self.raw_response),  # should display the Request string representation 
                'response_model_name': self.response_model_name,
                'data': data_repr
            },
            indent=4
        )

    def __repr__(self):
        """
        This is so a notebook automatically displays the string representation of the last expression.
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
            sierra_api_base_url: str,
            sierra_api_key: str,
            sierra_api_secret: str,
            endpoints: Dict = endpoints,       # default to the latest set of endpoints
                                               #   ... e.g. .sierra_api_v6_endpoints import endpoints
            log_level: int = logging.WARNING,  # default the logger to only display warnings
            log_level_httpx: int = logging.WARNING,  # default the httpx logger to warnings
            httpx_timeout: httpx.Timeout = httpx.Timeout(None)  # default to no httpx timeout
        ):

        # TODO make it easier to switch versions of the endpoints?

        # set this log level accordingly
        self.logger = logger
        self.logger.setLevel(log_level)

        # set the log level of httpx accordingly
        logging.getLogger('httpx').setLevel(log_level_httpx)

        self.session = None  # will contain the http client after init
        
        self.base_url = sierra_api_base_url
        self.api_key = sierra_api_key
        self.api_secret = sierra_api_secret

        self.endpoints = endpoints

        # store common urls here?
        self.token_url = self.base_url + 'token'

        # set the default timeout
        self.httpx_timeout = httpx_timeout

        # finally init the session
        self._initialize_session()

        # Log the init
        self.logger.debug(f"INIT {self.info()}")

    def _initialize_session(self):
        self.request_count = 0
        # (expires_at is an integer "timestamp" --seconds since UNIX Epoch
        self.expires_at = 0

        # For now, use the synchronous `httpx.Client()` 
        # TODO: Maybe use the Async Client only for fetching multiple "pages"?
        # ... self.session = httpx.AsyncClient() maybe?
        
        # Check if there is an existing session and it is an instance of httpx.Client
        if self.session and isinstance(self.session, httpx.Client):
            # Close the existing session to release resources
            self.session.close()    
        
        # Initialize a new HTTPX client
        self.session = httpx.Client(
            timeout=self.httpx_timeout
        )

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
    def get(
        self, 
        template: str,
        params: Dict = None,
        path_params: Dict = None
    ) -> SierraAPIResponse:
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

        if params is None:
            params = {}
        if path_params is None:
            path_params = {}

        # # Set the default limit to 2000 if not specified in params
        # if 'limit' not in params:
        #     params['limit'] = 2000
        # self.logger.debug(f"After setting default limit, params: {params}")
        
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
        try:
            expected_model = self.endpoints["GET"][template]["responses"][response.status_code] 
        except KeyError as e:
            self.logger.error(f"Error: {e}")
            # should halt the program
        
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
            response_model_name=model_name,
            data=parsed_data,
            raw_response=response
        )
    
    @hybrid_retry_decorator()
    @authenticate
    # def post(self, template, json_body, *args, **kwargs):
    def post(
        self, 
        template: str, 
        params: Optional[Dict] = None, 
        json_body: Union[str, dict, None] = None
    ) -> SierraAPIResponse:
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

        if params is None:
            params = {}
        # if path_params is None:
        #     path_params = {}

        # if 'limit' not in params:
        #     params['limit'] = 2000
        # self.logger.debug(f"After setting default limit, params: {params}")


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
        
        # # create a request object and then prepare it
        # request = requests.Request(
        #     method='POST', 
        #     url=endpoint_url,
        #     params=params,
        #     json=json_body
        # )
        # # prepare the request with the session
        # prepared_request = self.session.prepare_request(request)

        # # send the prepared request (POST)
        # response = self.session.send(prepared_request)
        # self.request_count += 1

        # debug_text = (
        #     f'"response.status_code": {response.status_code}, ' +
        #     f'"prepared_request.url": {prepared_request.url}, ' +
        #     f'"prepared_request.params": {json.dumps(params)}, ' +  # Convert params to a JSON string
        #     f'"prepared_request.body": {prepared_request.body.decode("utf-8")}, ' +
        #     f'"request_count": {self.request_count}'
        # )
        # self.logger.debug(debug_text)

        response = self.session.post(
            url=endpoint_url,
            params=params,
            json=json_body
        )

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
            response_model_name=model_name,
            data=parsed_data,
            raw_response=response
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
        self.last_was_operator = False

    def start_query(
            self, 
            record_type: str,
            field: Optional[Dict] = None,
            field_tag: Optional[str] = None,
            id: Optional[int] = None
        ):
        """
        the beginning of a simple query
        e.g.  
        
            `q.start_query(record_type='bib', field={'marcTag': '264' 'ind1': ' ', 'ind2': '1', 'subfields': 'c'})`
              
            `q.start_query(record_type='bib', field_tag='a')`
              
            `q.start_query(record_type='item', id=88)`
        """
        if self.current_query is not None:
            raise ValueError("Previous query not ended. Use end_query to finish.")
        
        if self.last_was_operator:
            self.last_was_operator = False
        
        # make sure only one param is set for the group
        if sum(p is not None for p in [field, field_tag, id]) > 1:
            raise ValueError("Only one of field, field_tag, or id can be set.")
        
        if field:
            # TODO should have some sort of check that the dict is properly formatted
            # ... but for now, just take a dict, hopefully it should look like this
            # ... {"marcTag": "264", "ind1": " ", "ind2": "1", "subfields": "c"}
            self.current_query = {
                "target": {
                    "record": {"type": record_type},
                    "field": field
                },
                "expr": []
            }
            return self
        elif field_tag:
            self.current_query = {
                "target": {
                    "record": {"type": record_type},
                    "field": {"tag": field_tag}
                },
                "expr": []
            }
            return self
        elif id:
            # if id is given, then it's a fixed field id
            self.current_query = {
                "target": {
                    "record": {"type": record_type},
                    "id": id
                },
                "expr": []
            }
            return self
        else:
            raise ValueError('query must target either a varfield or a fixed field')

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

    def add_logical_operator(self, operator):
        if operator not in ['and', 'or', 'and not']:
            raise ValueError("Operator must be 'and' or 'or' or 'and not'.")
        if self.current_query and not isinstance(self.current_query["expr"][-1], str):
            self.current_query["expr"].append(operator)
        elif not self.queries or self.last_was_operator:
            raise ValueError("Cannot add a logical operator at this point.")
        else:
            self.queries.append(operator)
            self.last_was_operator = True
        return self

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
        if self.current_query is not None:
            return "<SierraQueryBuilder: Unfinished Query>"
        
        return self.json()

    def __repr__(self):
        return self.__str__()
    
    def __add__(self, other):
        # define behavior for the + operator
        try:
            return {
                "queries": [
                    self.build(),
                    'and',
                    other.build()
                ]
            }
        except Exception as e:
            print(f'Error: {e}')


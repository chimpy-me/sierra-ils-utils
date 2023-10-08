import functools
import logging
from time import sleep, time
from typing import Optional, List, Dict, Union, Any
import requests

# Set up the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set default level, but this can be configured elsewhere

# Define the data models
class ErrorCode:
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str]

class Language:
    code: str
    name: Optional[str]

class MarcSubField:
    code: str
    data: str

class FieldData:
    subfields: List[MarcSubField]
    ind1: str
    ind2: str

class MarcField:
    tag: str
    value: Optional[str]
    data: Optional[FieldData]

class Marc:
    leader: str
    fields: List[MarcField]

class MaterialType:
    code: str
    value: Optional[str]

class BibLevel:
    code: str
    value: Optional[str]

class Country:
    code: str
    name: str

class Location:
    code: str
    name: str

class OrderInfo:
    orderId: str
    location: Location
    copies: int
    date: Optional[str]

class FixedFieldVal:
    value: Union[str, bool, int, float]  # Assuming T can be one of these types

class FixedField:
    label: str
    value: Optional[FixedFieldVal]
    display: Optional[str]

class SubField:
    tag: str
    content: str

class VarField:
    fieldTag: str
    marcTag: Optional[str]
    ind1: Optional[str]
    ind2: Optional[str]
    content: Optional[str]
    subfields: Optional[List[SubField]]

class Bib:
    id: str
    updatedDate: Optional[str]
    createdDate: Optional[str]
    deletedDate: Optional[str]
    deleted: bool
    suppressed: Optional[bool]
    available: Optional[bool]
    lang: Optional[Language]
    title: Optional[str]
    author: Optional[str]
    marc: Optional[Marc]
    materialType: Optional[MaterialType]
    bibLevel: Optional[BibLevel]
    publishYear: Optional[int]
    catalogDate: Optional[str]
    country: Optional[Country]
    orders: List[OrderInfo]
    normTitle: Optional[str]
    normAuthor: Optional[str]
    locations: List[Location]
    holdCount: Optional[int]
    copies: Optional[int]
    callNumber: Optional[str]
    volumes: Optional[List[str]]
    items: Optional[List[str]]
    fixedFields: Dict[int, FixedField]
    varFields: List[VarField]

class BibResultSet:
    total: Optional[int]
    start: Optional[int]
    entries: List[Bib]

ENDPOINTS = {
    "bibs": {
        "GET": {
            "path": "/v6/bibs/",
            "responses": {
                200: BibResultSet,
                400: ErrorCode,
                404: ErrorCode
                # ... other potential status codes and their corresponding models
            },
            "model": BibResultSet
        },
        "DELETE": {
            "path": "/v6/bibs/",
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
            ENDPOINTS=ENDPOINTS
        ):

        self.logger = logger

        # maximum number of requests we should make for our given session
        # TODO, should this be a max lifetime of like 3-5 hours perhaps?
        self.max_request_count = 100  # TODO: set in the config, or at least in the params?
        
        self.base_url = sierra_api_base_url
        self.api_key = sierra_api_key
        self.api_secret = sierra_api_secret

        self._endpoints = ENDPOINTS

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

    def hybrid_retry_decorator(max_retries=5, initial_wait_time=3):
        """
        Decorator factory to add retry with a hybrid back-off
        functionality to functions or methods.

        This will effectively catch any exceptions raised in the
        function it wraps, retrying them with the back-off strategy 
        """
        # Define parameters for the hybrid strategy
        initial_exponential_factor = 2
        initial_retries = 4
        fixed_interval = 300  # 5 minutes
    
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                retries = 0
                wait_time = initial_wait_time
                while retries < max_retries:
                    try:
                        result = func(self, *args, **kwargs)
                        return result
                    except Exception as e:
                        self.logger.info(
                            f"Retry attempt {retries + 1} after failure: {str(e)}. Waiting {wait_time} seconds before retrying."
                        )
                        if retries == max_retries - 1:
                            self.logger.error(f"Max retries reached. Function {func.__name__} failed with exception: {str(e)}")
                            raise e
                        sleep(wait_time)
                        retries += 1
                        if retries < initial_retries:
                            wait_time *= initial_exponential_factor
                        else:
                            wait_time += fixed_interval
            return wrapper
        return decorator

    def authenticate(func):
        """
        Decorator for use on any of the request functions

        Sets the access token for authenticated requests
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # if self.request_count >= self.max_request_count:
            #     self.logger.info("Refreshing Session ...")
            #     self._initialize_session()  # refresh our session
            #     self.request_count = 0      # Reset request counter after reinitializing session

            # decide if we need to get a new access token...
            if (
                self.session.headers['Authorization'] == ''  # Authorization header not set 
                or self.expires_at < time()                  # ... or expires_at is in the past
            ):
                # Set the request parameters (for authentication and
                # the grant type)
                auth = requests.auth.HTTPBasicAuth(
                    username=self.api_key, 
                    password=self.api_secret
                )
                data = {
                    "grant_type": "client_credentials"
                }
                
                response = self.session.post(
                    url=self.token_url, 
                    auth=auth, 
                    data=data
                )
                
                if response.status_code == 200:
                    self.session.headers['Authorization'] = \
                        'Bearer ' + response.json().get('access_token')
                    
                    # set the variable for when this expires at
                    self.logger.info(f"Authorization Success. response.json.get('expires_in'): {response.json().get('expires_in')}")
                    self.expires_at = time() + int(response.json().get('expires_in')) - 60  # pad our expiration time by -60 seconds to be safe
                else:
                    # If the request failed, raise an exception
                    raise Exception(f"Failed to obtain access token: {response.text}\n")


                self.logger.info(f"Sierra session authenticated")
                
                # get some info about our token: e.g. /v6/info/token
                response = self.session.get(
                    self.base_url + 'info/token'
                )

                try:
                    status_code = response.status_code
                except ValueError:
                    status_code = ''
                try:
                    expires_in = response.json().get('expiresIn')
                except ValueError:
                    expires_in = ''
                try:
                    url = response.url
                except ValueError:
                    url = ''

                self.logger.info(f"Sierra response status code                  : {status_code}")
                self.logger.info(f"Sierra 'expiresIn'                           : {expires_in}")
                self.logger.info(f"session expires at (UNIX Epoch)              : {self.expires_at}")
                self.logger.info(f"seconds left                                 : {self.expires_at - time()}")
                self.logger.info(f"request url                                  : {url}")
                # self.logger.info(f"resonse json                                 : {response.json()}\n")

            return func(self, *args, **kwargs)   
        return wrapper

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
        Remove specified paths or patterns from a JSON object or list. A path 
        typically represents a precise sequence of keys and/or indices leading to 
        a specific value--however, for a list, this function will attempt to 
        remove the specified key from all items in the list.
      
        This method is particularly useful when wanting certain parts of the JSON 
        object to be ignored, e.g., during a json_diff operation.

        Parameters:
        - paths (List[List[Union[str, int]]]): 
            A list of paths to be removed. Each path is represented
            as a list of keys (for dictionaries) or indices (for lists).
        - current_obj (Optional[Union[dict, list]]): 
            The current JSON object or list being operated on during 
            recursion. This parameter is mostly used internally and 
            typically doesn't need to be provided by the user.

        Returns:
        - None: The input JSON object or list is modified in place.
        """
        if current_obj is None:
            current_obj = self._json_obj

        # Base cases
        if not paths or (
            not isinstance(current_obj, dict) 
            and not isinstance(current_obj, list)
        ):
            return self  # Always return self for method chaining

        # If the object is a dictionary:
        if isinstance(current_obj, dict):
            for path in paths:
                # If the first key of the path exists in the dictionary:
                if path and path[0] in current_obj:
                    # If this is the last key in the path, delete it from the object
                    if len(path) == 1:
                        del current_obj[path[0]]
                    else:
                        # Recursively navigate to the next level with the shortened path
                        self.remove_paths([path[1:]], current_obj=current_obj[path[0]])

        # If the object is a list:
        elif isinstance(current_obj, list):
            # For each item in the list:
            for item in current_obj:
                # Call the function recursively with the same set of paths
                self.remove_paths(paths, current_obj=item)

        return self  # Ensure that we always return self for method chaining

    @property
    def json_obj(self):
        return self._json_obj

    # TODO: other possible methods
    #   - transform key / value (to replace a patron record id with a pseudonym)    
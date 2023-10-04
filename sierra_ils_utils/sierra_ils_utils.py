import functools
import logging
from time import sleep
import requests
from time import time

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
            sierra_api_secret
        ):

        self.logger = logger

        # maximum number of requests we should make for our given session
        # TODO, should this be a max lifetime of like 3-5 hours perhaps?
        self.max_request_count = 100  # TODO: set in the config, or at least in the params?
        
        self.base_url = sierra_api_base_url
        self.api_key = sierra_api_key
        self.api_secret = sierra_api_secret

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
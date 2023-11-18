import logging
from random import uniform
from time import sleep, time
import requests
import functools

logger = logging.getLogger(__name__)

def hybrid_retry_decorator(
        max_retries=5, 
        initial_wait_time=3,
        initial_exponential_factor=2,
        initial_retries=3,
        fixed_interval=150,  # 2.5 minutes
        retry_on_exceptions=None,
        retry_on_status_codes=None
    ):
    """
    A decorator factory that adds a hybrid retry mechanism to functions/methods.
    
    This decorator wraps the given function and catches any exceptions raised within it. 
    If an exception is caught, it employs a hybrid back-off strategy for retries.

    The hybrid back-off strategy consists of two parts:
    1. Exponential back-off for the first few attempts.
    2. Fixed interval retries for the remaining attempts.

    Parameters:
    - max_retries (int): Maximum number of retries before giving up. Default is 7.
    - initial_wait_time (float): Initial waiting time in seconds before the first retry. Default is 3 seconds.
    - initial_exponential_factor (float): Factor by which the wait time is multiplied after each retry during the exponential back-off phase. Default is 1.5.
    - initial_retries (int): Number of times to employ the exponential back-off before switching to fixed interval retries. Default is 5.
    - fixed_interval (float): Time in seconds to wait between retries after the exponential back-off phase. Default is 150 seconds (2.5 minutes).
    - retry_on_exceptions (tuple): Exceptions on which to retry. Defaults to requests' transient errors.
    - retry_on_status_codes (list): List of HTTP status codes on which to retry.

    Notes:
    - Random jitter (a random value between +/- 10% of the wait time) is added to the wait time for each retry to avoid synchronized retries.
    - If all retries fail, the last exception raised in the wrapped function will be re-raised.
    
    Returns:
    - A decorated function that will retry upon failure using the hybrid back-off strategy.
    """
    if retry_on_exceptions is None:
        # Default exceptions for requests that are generally considered transient
        retry_on_exceptions = (requests.ConnectionError, requests.Timeout, requests.TooManyRedirects)
    
    if retry_on_status_codes is None:
        # Default status codes to retry on (5XX server errors)
        retry_on_status_codes = [500, 502, 503, 504]

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            retries = 0
            wait_time = initial_wait_time
            while retries <= max_retries:
                try:
                    response = func(self, *args, **kwargs)
                    if response.status_code in retry_on_status_codes:
                        raise requests.HTTPError(f"HTTP {response.status_code} Error")
                    return response
                except retry_on_exceptions as e:
                    self.logger.info(
                        f"Retry attempt {retries + 1} after failure: {str(e)}. Waiting {wait_time} seconds before retrying."
                    )
                    if retries == max_retries - 1:
                        self.logger.error(f"Max retries reached. Function {func.__name__} failed with exception: {str(e)}")
                        raise e
                    sleep(wait_time)
                    retries += 1
                    if retries < initial_retries:
                        # Increase the wait time with random jitter
                        wait_time = initial_exponential_factor \
                            * (wait_time * uniform(0.9, 1.1))
                    else:
                        # Add fixed interval with random jitter
                        wait_time += fixed_interval \
                            * uniform(0.9, 1.1)
        return wrapper
    return decorator

def authenticate(func):
    """
    Decorator for use on any of the request functions

    Sets the access token for authenticated requests
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
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
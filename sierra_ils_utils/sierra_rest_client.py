import httpx
import asyncio
import threading
import time
import logging

# get a module-level logger
logger = logging.getLogger(__name__)

class SierraRESTClient:
    """
    AKA: SierraAPI
    
    A client for interacting with the Sierra REST API, supporting both
    synchronous and asynchronous operations.

    This class provides methods for making authenticated HTTP requests to the 
    Sierra REST API:
    
        - request(self, method, url, *args, **kwargs)
            Makes a synchronous (blocking) HTTP request to the API
        
        - async_request(self, method, url, *args, **kwargs)
            Makes an asynchronous (non-blocking) HTTP request to the API
    
    These methods handle token-based authentication using client credentials
    and automatically obtains and refreshes tokens as needed.
    
    Example Uses:
    
        ```
        client = SierraRESTClient(
            base_url='https://catalog.library.org/iii/sierra-api/v6/', 
            client_id='CLIENT_ID_HERE',
            client_secret='CLIENT_SECRET_HERE'
        )
        
        # Synchronous request example
        response = client.request('GET', 'info/token')
        
        # Asynchronous request example
        response = await client.async_request('GET', 'info/token')
        ```
    """
    def __init__(
        self, 
        base_url,
        client_id,
        client_secret,
        max_retries=3,
        backoff_factor=1.0,
        timeout=30.0,
        *args, 
        **kwargs
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = 0
        self._async_lock = asyncio.Lock()  # Async lock for async operations
        self._thread_lock = threading.Lock()  # Thread lock for sync operations
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Initialize clients with base_url 
        # (one for synchronous/blocking requests)
        self._sync_client = httpx.Client(
            base_url=base_url, 
            timeout=timeout,
            *args, 
            **kwargs
        )
        # (and one for asynchronous/non-blocking requests)
        self._async_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
            *args,
            **kwargs
        )

        logger.debug("SierraRESTClient initialized...")
        logger.debug(
            "base_url=%s, sierra_api_key=%s, max_retries=%d, backoff_factor=%.2f, timeout=%.2f",
            base_url, client_id, max_retries, backoff_factor, timeout
        )
        

    def _get_new_token_sync(self):
        with self._thread_lock:
            if self.access_token and time.time() < self.token_expiry:
                logger.debug("Sync token still valid; skipping refresh.")
                return
            logger.info("Fetching a new sync token from %s/token", self._sync_client.base_url)
            response = self._sync_client.post(
                "token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.token_expiry = time.time() + token_data.get("expires_in", 3600)
            logger.info("Sync token fetched. Expires at %f", self.token_expiry)

    async def _get_new_token_async(self):
        async with self._async_lock:
            if self.access_token and time.time() < self.token_expiry:
                logger.debug("Async token still valid; skipping refresh.")
                return
            logger.info("Fetching a new async token from %s/token", self._async_client.base_url)
            response = await self._async_client.post(
                "token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.token_expiry = time.time() + token_data.get("expires_in", 3600)
            logger.info("Async token fetched. Expires at %f", self.token_expiry)


    def _ensure_valid_token_sync(self):
        logger.debug("Ensuring sync token validity.")
        if not self.access_token or time.time() >= self.token_expiry:
            self._get_new_token_sync()


    async def _ensure_valid_token_async(self):
        logger.debug("Ensuring async token validity.")
        if not self.access_token or time.time() >= self.token_expiry:
            await self._get_new_token_async()

    
    def request(
        self, 
        method, 
        url, 
        *args, 
        retries=None, 
        backoff_factor=None, 
        **kwargs
    ):
        """
        For making a synchronous (blocking) request with retry and backoff logic,
        including handling of transient 5xx errors.
        """
        retries = retries or self.max_retries
        backoff_factor = backoff_factor or self.backoff_factor

        for attempt in range(retries):
            try:
                self._ensure_valid_token_sync()

                # Add the Authorization header explicitly for clarity:
                kwargs.setdefault("headers", {})
                kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"

                logger.debug(
                    "Sync request attempt %d/%d: %s %s [token=%s]",
                    attempt + 1,
                    retries,
                    method,
                    url,
                    self.access_token[:8] + "..." if self.access_token else None
                )

                response = self._sync_client.request(method, url, *args, **kwargs)

                # Check for 401 => possibly refresh token and retry once
                if response.status_code == 401:
                    logger.warning("Got 401 on sync request. Refreshing token and retrying.")
                    self._get_new_token_sync()
                    kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
                    response = self._sync_client.request(method, url, *args, **kwargs)
                    if response.status_code == 401:
                        logger.error("Still 401 after token refresh. Returning response.")
                        return response

                # Check if it's a 5xx transient error
                if 500 <= response.status_code < 600:
                    if attempt < retries - 1:
                        backoff_time = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Sync request got %d on attempt %d. Retrying in %.2f seconds...",
                            response.status_code, attempt + 1, backoff_time
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        logger.error(
                            "Sync request got %d on final attempt; returning response.",
                            response.status_code
                        )
                        return response

                # For any other code (including 2xx, 3xx, or other 4xx) return
                return response

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                logger.warning("Timeout on sync attempt %d/%d: %s", attempt + 1, retries, str(exc))
                if attempt < retries - 1:
                    backoff_time = backoff_factor * (2 ** attempt)
                    logger.debug("Retrying in %.2f seconds...", backoff_time)
                    time.sleep(backoff_time)
                else:
                    logger.error("Maximum sync retries reached. Raising exception.")
                    raise

    async def async_request(
        self, 
        method, 
        url, 
        *args, 
        retries=None, 
        backoff_factor=None, 
        **kwargs
    ):
        """
        For making an asynchronous request with retry and backoff logic,
        including handling of transient 5xx errors.
        """
        retries = retries or self.max_retries
        backoff_factor = backoff_factor or self.backoff_factor

        await self._ensure_valid_token_async()

        # Always add the Authorization header explicitly for clarity
        kwargs.setdefault("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"

        for attempt in range(retries):
            try:
                logger.debug(
                    "Async request attempt %d/%d: %s %s [token=%s]",
                    attempt + 1,
                    retries,
                    method,
                    url,
                    self.access_token[:8] + "..." if self.access_token else None
                )
                response = await self._async_client.request(method, url, *args, **kwargs)

                # -- Handle 401 (Unauthorized) --
                if response.status_code == 401:
                    logger.warning("Got 401 on async request. Refreshing token and retrying.")
                    await self._get_new_token_async()
                    kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
                    response = await self._async_client.request(method, url, *args, **kwargs)
                    if response.status_code == 401:
                        logger.error("Still 401 after async token refresh. Returning response.")
                        return response

                # -- Handle 5xx (transient server errors) --
                if 500 <= response.status_code < 600:
                    if attempt < retries - 1:
                        backoff_time = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Async request got %d on attempt %d. Retrying in %.2f seconds...",
                            response.status_code, attempt + 1, backoff_time
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error(
                            "Async request got %d on final attempt; returning response.",
                            response.status_code
                        )
                        return response

                # If it's not a 401 that we can fix or a 5xx we want to retry,
                # return the response immediately.
                return response

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                logger.warning("Timeout on async attempt %d/%d: %s", attempt + 1, retries, str(exc))
                if attempt < retries - 1:
                    backoff_time = backoff_factor * (2 ** attempt)
                    logger.debug("Retrying async request in %.2f seconds...", backoff_time)
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error("Maximum async retries reached. Raising exception.")
                    raise

            except asyncio.CancelledError:
                logger.warning("Async request cancelled.")
                raise

    async def _fetch_page_async(
        self,
        endpoint,
        start_id,
        limit=2000,
        extra_params=None
    ):
        """
        Helper function for `async_yield_entries`
        
        Fetch a single page of results using an 'open range' starting at 
        `start_id`

        Returns a list of 'entries' on success, or an empty list if none found
        """
        if extra_params is None:
            extra_params = {}
        params = {
            "id": f"[{start_id},]",  # e.g. '[0,]' means "from ID=0 up to ???"
            "limit": limit,
            **extra_params
        }
        response = await self.async_request(
            "GET",
            endpoint, 
            params=params
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("entries", [])
        else:
            logger.warning(
                "Page fetch returned status %s: %s", 
                response.status_code, 
                response.text
            )
            return []
        
    async def async_yield_entries(
        self, 
        endpoint, 
        start_id=0, 
        limit=2000, 
        concurrency=10, 
        params={}
    ):
        """
        Stream all records from `endpoint`, beginning at `start_id`.
        
        This uses concurrent 'page fetches' to speed things up:
          - concurrency=N => fetch up to N pages at once.
          
        Yields individual entries (one at a time) so you can consume them 
        in a streaming fashion.
        
        Args:
            endpoint (str): API endpoint (e.g., 'items/' or 'patrons/')
            start_id (int): Starting ID to fetch from.
            limit (int): Number of records per page.
            concurrency (int): Number of concurrent requests per batch.
            extra_params (dict): Optional extra query parameters.

        Yields:
            dict: A single API record (entry).
        """

        # Continuously fetch pages until we get no results
        while True:
            # Build tasks for one "batch" of concurrent page fetches
            tasks = []
            for i in range(concurrency):
                page_start_id = start_id + (i * limit)
                tasks.append(
                    self._fetch_page_async(endpoint, page_start_id, limit, params)
                )

            # Run the tasks concurrently and gather results
            results = await asyncio.gather(*tasks)

            # Flatten all results from this batch
            batch_entries = [entry for page in results for entry in page]

            if not batch_entries:
                # No more entries -> stop
                break

            # Sort by ID so we know the highest one 
            # (or remove if you don't need strict ID ordering).
            batch_entries.sort(key=lambda x: int(x["id"]))

            # Yield the entries one-by-one
            for entry in batch_entries:
                yield entry

            # Update `start_id` for the next batch 
            # using the highest ID from this batch
            last_id = int(batch_entries[-1]["id"])
            start_id = last_id + 1

    def close(self):
        logger.debug("Closing sync client.")
        self._sync_client.close()

    async def aclose(self):
        logger.debug("Closing async client.")
        await self._async_client.aclose()

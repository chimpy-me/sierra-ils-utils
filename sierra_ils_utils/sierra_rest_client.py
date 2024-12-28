import asyncio
import httpx
import logging
import queue
import threading
import time

# Set up a module-level logger
logger = logging.getLogger(__name__)

class SierraRESTClient:
    """
    A client for interacting with the Sierra REST API, supporting both
    synchronous and asynchronous operations.

    This class provides methods for making authenticated HTTP requests to the 
    Sierra REST API and handles token-based authentication using client credentials.
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

        # Initialize HTTP clients
        self._sync_client = httpx.Client(
            base_url=base_url, 
            timeout=timeout,
            *args, 
            **kwargs
        )
        self._async_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
            *args,
            **kwargs
        )

        logger.debug("SierraRESTClient initialized...")
        logger.debug(
            "base_url=%s, client_id=%s, max_retries=%d, backoff_factor=%.2f, timeout=%.2f",
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
        if not self.access_token or time.time() >= self.token_expiry:
            self._get_new_token_sync()

    async def _ensure_valid_token_async(self):
        if not self.access_token or time.time() >= self.token_expiry:
            await self._get_new_token_async()

    def request(self, method, url, *args, retries=None, backoff_factor=None, **kwargs):
        retries = retries or self.max_retries
        backoff_factor = backoff_factor or self.backoff_factor

        for attempt in range(retries):
            try:
                self._ensure_valid_token_sync()
                kwargs.setdefault("headers", {})
                kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"

                response = self._sync_client.request(method, url, *args, **kwargs)
                if response.status_code == 401:
                    self._get_new_token_sync()
                    kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
                    response = self._sync_client.request(method, url, *args, **kwargs)

                if response.status_code >= 500:
                    if attempt < retries - 1:
                        time.sleep(backoff_factor * (2 ** attempt))
                        continue
                return response

            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt >= retries - 1:
                    raise

    async def async_request(self, method, url, *args, retries=None, backoff_factor=None, **kwargs):
        retries = retries or self.max_retries
        backoff_factor = backoff_factor or self.backoff_factor

        await self._ensure_valid_token_async()
        kwargs.setdefault("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"

        for attempt in range(retries):
            try:
                response = await self._async_client.request(method, url, *args, **kwargs)
                if response.status_code == 401:
                    await self._get_new_token_async()
                    kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
                    response = await self._async_client.request(method, url, *args, **kwargs)

                if response.status_code >= 500:
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                        continue
                return response

            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt >= retries - 1:
                    raise

    async def _fetch_page_async(self, endpoint, start_id, limit=2000, extra_params=None):
        extra_params = extra_params or {}
        params = {"id": f"[{start_id},]", "limit": limit, **extra_params}
        response = await self.async_request("GET", endpoint, params=params)
        return response.json().get("entries", [])

    def yield_entries(
        self,
        endpoint,
        start_id=0,
        limit=2000,
        batch_size=10,
        params=None,
    ):
        """
        Synchronous generator that yields items from `endpoint`, fetching
        records in batches using async concurrency in a separate thread.
        """
        if params is None:
            params = {}

        # A queue for transferring items from the worker thread to the main thread
        q = queue.Queue()
        SENTINEL = object()  # A unique marker to signal 'no more entries'

        async def __fetch_and_queue():
            """
            Async function that fetches records in batches and queues them.
            """
            nonlocal start_id
            while True:
                # Create tasks for a batch of concurrent requests
                tasks = [
                    self._fetch_page_async(
                        endpoint,
                        start_id + (i * limit),
                        limit,
                        extra_params=params,
                    )
                    for i in range(batch_size)
                ]

                # Run all tasks concurrently and gather results
                results = await asyncio.gather(*tasks)

                # Flatten all results into a single batch
                current_batch = [
                    record for page in results if page for record in page
                ]

                if not current_batch:
                    # No more records, signal the end
                    q.put(SENTINEL)
                    break

                # Sort the batch by ID for consistency
                current_batch.sort(key=lambda x: int(x["id"]))

                # Enqueue records for processing
                for record in current_batch:
                    q.put(record)

                # Update `start_id` to the highest ID in the current batch
                last_record_id = int(current_batch[-1]["id"])
                start_id = last_record_id + 1

        def __worker_thread():
            """
            Worker thread to run the async fetcher.
            """
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(__fetch_and_queue())
            finally:
                loop.close()

        # Start the worker thread
        t = threading.Thread(target=__worker_thread, daemon=True)
        t.start()

        # Yield items from the queue, blocking in the main thread
        while True:
            item = q.get()  # Block until next item or sentinel
            if item is SENTINEL:
                break
            yield item



    def close(self):
        self._sync_client.close()

    async def aclose(self):
        await self._async_client.aclose()

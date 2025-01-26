# sierra-ils-utils

**sierra-ils-utils** is a Python library / wrapper around [HTTPX](https://www.python-httpx.org/) -- providing largely the same fully featured HTTP client for Python 3).

The library provides convenient synchronous and asynchronous methods for working with the Sierra ILS REST API. The client provided by the library automatically handles the token-based authentication (client-credentials flow) and includes configurable retry and backoff logic.

---

## Installation

```bash
# You can install sierra-ils-utils from PyPI:
pip install sierra-ils-utils
```

## Quick Start

```python
from sierra_ils_utils import SierraAPI

client = SierraRESTClient(
    base_url="https://catalog.library.org/iii/sierra-api/v6/",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)

# Make a synchronous request (returns a httpx.Response)
response = client.request("GET", "info/token")  # <Response [200 200]>
response.raise_for_status()

# Or, make an async request (returns a httpx.Response)
response = await client.async_request("GET", "info/token")  # <Response [200 200]>
response.raise_for_status()
```

The `request()` and `async_request()` client methods will return [httpx.Response](https://www.python-httpx.org/api/#response) objects.

## License

This project is released under the [MIT License](./LICENSE).

## Authors

Ray Voelker – [ray.voelker@gmail.com](mailto:ray.voelker@gmail.com)

## Issues and Support

Please open an issue on GitHub if you encounter problems, bugs, or have feature requests. We welcome all contributions and feedback!
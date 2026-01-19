# sierra-ils-utils

[![Tests](https://github.com/chimpy-me/sierra-ils-utils/actions/workflows/test.yml/badge.svg)](https://github.com/chimpy-me/sierra-ils-utils/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/sierra-ils-utils.svg)](https://badge.fury.io/py/sierra-ils-utils)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python wrapper around [HTTPX](https://www.python-httpx.org/) for working with the Sierra ILS REST API.

## Features

- **Sync and async support** - Use `request()` for blocking calls or `async_request()` for async/await
- **Automatic authentication** - Handles OAuth2 client credentials flow automatically
- **Token management** - Automatically refreshes tokens when expired or on 401 responses
- **Retry logic** - Configurable retries with exponential backoff for 5xx errors and timeouts
- **Context manager support** - Use `with` or `async with` for automatic resource cleanup
- **Custom client injection** - Inject your own httpx client (e.g., for caching with hishel)
- **Type hints** - Full type annotations with `py.typed` marker for IDE support

## Installation

```bash
# Install from PyPI
pip install sierra-ils-utils

# Or with uv
uv add sierra-ils-utils
```

**Requires Python 3.10+**

## Quick Start

```python
from sierra_ils_utils import SierraRESTClient

# Using context manager (recommended)
with SierraRESTClient(
    base_url="https://catalog.library.org/iii/sierra-api/v6/",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
) as client:
    response = client.request("GET", "bibs/", params={"limit": 10})
    response.raise_for_status()
    print(response.json())
```

### Async Usage

```python
import asyncio
from sierra_ils_utils import SierraRESTClient

async def main():
    async with SierraRESTClient(
        base_url="https://catalog.library.org/iii/sierra-api/v6/",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET"
    ) as client:
        response = await client.async_request("GET", "bibs/", params={"limit": 10})
        response.raise_for_status()
        print(response.json())

asyncio.run(main())
```

### Configuration Options

```python
client = SierraRESTClient(
    base_url="https://catalog.library.org/iii/sierra-api/v6/",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    max_retries=3,        # Number of retries for 5xx errors (default: 3)
    backoff_factor=1.0,   # Exponential backoff multiplier (default: 1.0)
    timeout=30.0,         # Request timeout in seconds (default: 30.0)
)
```

### Custom Client Injection

You can inject a custom httpx client for advanced use cases like caching:

```python
import httpx
from sierra_ils_utils import SierraRESTClient

# Example: custom client with different timeout
custom_client = httpx.Client(
    base_url="https://catalog.library.org/iii/sierra-api/v6/",
    timeout=60.0
)

client = SierraRESTClient(
    base_url="https://catalog.library.org/iii/sierra-api/v6/",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    sync_client=custom_client  # or async_client for async
)
```

## Utilities

### SierraDateTime and SierraDate

Helpers for Sierra API-compatible date formatting:

```python
from sierra_ils_utils import SierraDateTime, SierraDate
from datetime import timedelta

# Current timestamp in Sierra format
now = SierraDateTime.now()
print(now)  # 2025-01-30T19:31:43Z

# Date arithmetic works
yesterday = now - timedelta(days=1)

# Create date ranges for API queries
date_range = f"[{yesterday},{now}]"

# Query items created in the last day
response = client.request(
    "GET", "items/",
    params={"createdDate": date_range, "limit": 2000}
)
```

### Timezone Support

```python
# Parse dates with timezone conversion
dt = SierraDateTime.from_string('2025-01-06 00:00:00', 'America/New_York')
print(dt)  # 2025-01-06T05:00:00Z (converted to UTC)
```

### get_max_record_id()

Find the maximum valid record ID using efficient binary search:

```python
from sierra_ils_utils import SierraRESTClient, get_max_record_id

with SierraRESTClient(...) as client:
    max_bib_id = get_max_record_id(client, "bibs/")
    print(f"Max bib ID: {max_bib_id}")  # e.g., 3934049
```

## Development

```bash
# Clone and install
git clone https://github.com/chimpy-me/sierra-ils-utils.git
cd sierra-ils-utils
uv sync --all-extras

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest -v
```

## Version

```python
from sierra_ils_utils import __version__
print(__version__)  # 0.1.0
```

## License

This project is released under the [MIT License](./LICENSE).

## Author

Ray Voelker – [ray.voelker@gmail.com](mailto:ray.voelker@gmail.com)

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/chimpy-me/sierra-ils-utils).

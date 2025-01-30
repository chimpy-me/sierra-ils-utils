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

## Other Utilities

### `SierraDateTime` and `SierraDate`

Some Sierra REST API endpoints expect dates and times in a specific ISO8601-like format. The library provides two helpers:

1. `SierraDateTime`: A thin wrapper around Python’s `datetime`, ensuring:

    * timezone-aware date / datetime creation -- defaulting to UTC
    * microseconds removed
    * output in ISO 8601 format ending with Z (e.g. `2020-07-07T12:55:00Z`)

2. `SierraDate`: A thin wrapper around Python's `date`, ensuring:

    * output is in YYYY-MM-DD format

Example Usage:

```python
from sierra_ils_utils import SierraDateTime
from datetime import timedelta

# generate a current timestamp for use with the REST API
datetime_now  = SierraDateTime.now()
print(datetime_now)  # 2025-01-30T19:31:43Z

# SierraDateTime is a `datetime` object, so you can use `timedelta` with it
datetime_prev = datetime_now - timedelta(days=1)
print(datetime_prev)  # 2025-01-29T19:31:43Z

# date ranges in Sierra REST API look like this:
# [2025-01-27T19:21:59Z,2025-01-30T19:21:59Z]
range_string = f"[{datetime_prev},{datetime_now}]"

# Get a list of items created in the last 1 day
response = client.request(
    'GET',
    'items/',
    params={
        'createdDate': range_string,  # using the range from above
        'limit': 2000
    }
)
response.raise_for_status()  # handle errors

print(response.json().get('total', 0))  # 1664
```

```python
# You can also use timezones to create dates that are in your local timezone ...
first_monday_2025 = SierraDateTime.from_string(
  '2025-01-06 00:00:00', 'America/New_York'
)
print(first_monday_2025)  # 2025-01-06T05:00:00Z
```

## License

This project is released under the [MIT License](./LICENSE).

## Authors

Ray Voelker – [ray.voelker@gmail.com](mailto:ray.voelker@gmail.com)

## Issues and Support

Please open an issue on GitHub if you encounter problems, bugs, or have feature requests. We welcome all contributions and feedback!

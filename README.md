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
from sierra_ils_utils import SierraDateTime, SierraDate

# 1) Create a Sierra REST API compatible time string for the current datetime

# 1) Parse a string with an explicit UTC offset
dt1 = SierraDateTime.from_string("2020-07-07 08:55:00.000 -0400")
print(dt1)  # "2020-07-07T12:55:00Z"

# 2) Parse a string and specify a named time zone
dt2 = SierraDateTime.from_string("2025-06-10 18:45:00", "America/New_York")
print(dt2)  # "2025-06-10T22:45:00Z"

# 3) Convert an existing Python datetime to a SierraDateTime
regular_dt = datetime(2025, 6, 10, 18, 45, tzinfo=timezone.utc)
sdt = SierraDateTime.from_datetime(regular_dt)
print(sdt)  # "2025-06-10T18:45:00Z"

# 4) Work with SierraDate for date-only fields
sdate = SierraDate.from_iso("2023-08-01")
print(sdate)  # "2023-08-01"
```

## License

This project is released under the [MIT License](./LICENSE).

## Authors

Ray Voelker – [ray.voelker@gmail.com](mailto:ray.voelker@gmail.com)

## Issues and Support

Please open an issue on GitHub if you encounter problems, bugs, or have feature requests. We welcome all contributions and feedback!

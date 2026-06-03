# Your first Sierra API call

This tutorial takes you from nothing to a successful read against the Sierra REST API, using
`sierra-ils-utils`. By the end you'll have authenticated and fetched a record.

!!! note "Conventions used in this guide"
    Record numbers shown here are **fictitious**, and hostnames like
    `your-catalog.example.org` are **placeholders** — replace them with your own library's values.

## 1. Get API credentials

Sierra's REST API uses OAuth2 client-credentials. You need a **client key** and **client secret**,
created by a Sierra administrator in the Sierra Admin app (under the API / "Sierra API keys" area).
You also need your API **base URL**, which looks like:

```
https://your-catalog.example.org/iii/sierra-api/v6/
```

Ask your administrator for all three if you don't have them.

## 2. Install

=== "pip"

    ```bash
    pip install sierra-ils-utils
    ```

=== "uv"

    ```bash
    uv add sierra-ils-utils
    ```

Requires Python 3.10+.

## 3. Keep secrets out of your code

Never hard-code the secret. Read it from the environment (or a secrets manager). A common
convention is three environment variables:

```bash
export SIERRA_API_BASE_URL="https://your-catalog.example.org/iii/sierra-api/v6/"
export SIERRA_API_KEY="your-client-key"
export SIERRA_API_SECRET="your-client-secret"
```

## 4. Authenticate and verify

`SierraRESTClient` fetches and refreshes OAuth2 tokens for you — you never manage tokens by hand.
The quickest way to confirm your credentials work is to hit the token-info endpoint:

```python
import os
from sierra_ils_utils import SierraRESTClient

with SierraRESTClient(
    base_url=os.environ["SIERRA_API_BASE_URL"],
    client_id=os.environ["SIERRA_API_KEY"],
    client_secret=os.environ["SIERRA_API_SECRET"],
) as client:
    response = client.request("GET", "info/token")
    response.raise_for_status()
    print("Auth OK:", response.status_code)  # 200
```

If you get a `200`, your credentials and base URL are correct.

## 5. Read your first records

Now fetch a few bibliographic records. Two things to notice, both of which have their own
[Quirks Catalog](../reference/quirks/index.md) entries:

- `params={"fields": ","}` — a bare comma asks Sierra to return **all** fields. Without it you get a
  minimal response. See [Reads & IDs](../reference/quirks/reads-and-ids.md).
- Always call `raise_for_status()` and check the status code — Sierra's status codes have
  [surprises](../reference/quirks/write-semantics.md) (a successful write is `204`, not `200`).

```python
import os
from sierra_ils_utils import SierraRESTClient

with SierraRESTClient(
    base_url=os.environ["SIERRA_API_BASE_URL"],
    client_id=os.environ["SIERRA_API_KEY"],
    client_secret=os.environ["SIERRA_API_SECRET"],
) as client:
    response = client.request(
        "GET",
        "bibs/",
        params={"limit": 5, "fields": ","},
    )
    response.raise_for_status()
    data = response.json()
    for bib in data.get("entries", []):
        print(bib["id"], bib.get("title"))
```

## 6. Async, when you need throughput

For bulk reads, use the async client and `await async_request(...)`. The shape is identical:

```python
import asyncio, os
from sierra_ils_utils import SierraRESTClient

async def main():
    async with SierraRESTClient(
        base_url=os.environ["SIERRA_API_BASE_URL"],
        client_id=os.environ["SIERRA_API_KEY"],
        client_secret=os.environ["SIERRA_API_SECRET"],
    ) as client:
        response = await client.async_request("GET", "bibs/", params={"limit": 5, "fields": ","})
        response.raise_for_status()
        print(response.json())

asyncio.run(main())
```

## Next steps

- Skim the **[Quirks Catalog](../reference/quirks/index.md)** before you write anything back to
  Sierra — the write path has the most surprises.
- Recipes for common tasks (bulk async fetching, safe updates, Create List queries) are coming as
  the guide grows.

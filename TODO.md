# TODO

## Async Client

I'd like to use async calls in a way that makes sense ... i'm not sure if that means only limiting it to situations where sierra-ils-utils can control the "loop"? 

...perhaps a .all() method could run the first call synch and if there are resulting "pages" for the endpoint then we could use an async to "get all"

For example:
```
for result in sierra_api.get(
    'patrons/holds',
    params={
        'limit': 2000,
        'offset': 0
    }
).all():
    pass
```

Could first run the HTTP get request sync, and then based on the `total`, it could determine how to divvy up the subsequent requests.

Here's a really great working example

```python
# import the modules
from sierra_ils_utils import SierraAPI
from google.colab import userdata

# setup the api client from sierra-ils-utils
sierra_api = SierraAPI(
    sierra_api_base_url=userdata.get('sierra_api_base_url'),
    sierra_api_key=userdata.get('sierra_api_key'),
    sierra_api_secret=userdata.get('sierra_api_secret')
)


# running a test of using httpx async client ... this functionality will be 
# integrated into `sierra-ils-utils`

import asyncio
import httpx
import json

async def fetch_data(session, limit, offset, timeout):
    url = sierra_api.base_url + 'patrons/holds'  # Use the base URL from the client
    params = {'limit': limit, 'offset': offset}  # Use the same parameters as the client
    try:
        response = await session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"Request failed: {e}")
        return None  # or handle the error as appropriate

async def all(limit, timeout):
    headers = sierra_api.session.headers  # Use the same headers as the client
    async with httpx.AsyncClient(headers=headers) as session:
        initial_data = await fetch_data(session, limit, 0, timeout)
        if not initial_data:
            return  # Handle the error appropriately

        total = initial_data['total']
        print(initial_data)
        yield initial_data

        num_requests = (total + limit - 1) // limit
        tasks = [fetch_data(session, limit, offset * limit, timeout) for offset in range(1, num_requests)]

        for future in asyncio.as_completed(tasks):
            result = await future
            if result:
                yield result


async def main():
    all_data = []  # List to collect all data chunks
    async for data in all(2000, httpx.Timeout(None)):
        if data:
            all_data.append(data)  # Add the data chunk to the list
            print(data['start'])

    # Write all data to file in one go
    with open('data.json', 'w') as f:
        json.dump(all_data, f)

# Execute the main function in a Jupyter Notebook
await main()
```

The above will asynchronously pull down all the hold data from Sierra -- in my test it took about 41 seconds for all 142_029 holds to download from the endpoint


## Sierra Error Codes

it could be nice to maybe handle sierra error codes better ... for example:

```json
{
    "code":113,
    "specificCode":0,
    "httpStatus":401,
    "name":"Unauthorized",
    "description":"Invalid or missing authorization header"
}
```
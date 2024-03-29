# sierra-ils-utils
Python wrappers for working with the Sierra ILS 

See this IUG 2024 Conference Presentation Blog Post for more details and example use-cases: [chimpy.me/blog/posts/iug-2024/](https://chimpy.me/blog/posts/iug-2024/) 

## Sierra API Client Documentation

### Introduction

This documentation provides an overview of `sierra-ils-utils' along with the design approach for extending the Sierra APIs with this client and various utilities.

The primary objective of `sierra-ils-utils` is to create a flexible and extensible structure that allows for easier, more straightforward use of the Sierra APIs.

### Quick Start

1. Install `sierra-ils-utils` from PyPI:
   
   ```bash
   pip install sierra-ils-utils
   ```

   or from a Jupyter Notebook:

   ```python
   %%capture
   !pip install sierra-ils-utils  # install from PyPI
   ```

2. Create a client -- loading API configurations:

   ```python
    # create the API client
    sierra_api = sierra_ils_utils.SierraAPI(
        sierra_api_base_url,  # Base URL of the Sierra API
                              #   e.g. https://library.edu/iii/sierra-api/v6/
        sierra_api_key,       # Sierra API Key
        sierra_api_secret     # Sierra API Secret
   )
   ```

3. Use the client to get data from Sierra
   
   ```python
    # GET a single item ...
    result = sierra_api.get(
        'items/',                # items endpoint
        params={                 # parameters for the request ...
            'limit': 1,          # ... limit the number of results to one
            'offset': 1_000_000  # ... offset the results
        }
    )

    # the result is an object, SierraAPIResponse
    result 
   ```

   ```json
   {
    "raw_response": "<Response [200 200]>",
    "response_model_name": "ItemResultSet",
    "data": {
        "total": 1,
        "start": 1000000,
        "entries": [
            {
                "id": "2000001",
                "updatedDate": "2013-01-05T23:31:01Z",
                "createdDate": "2012-06-27T16:36:21Z",
                "deletedDate": null,
                "deleted": false,
                "suppressed": null,
                "bibIds": [
                    "1929437"
                ],
                "location": {
                    "code": "3ha",
                    "name": "Main - Information & Reference - History Stacks"
                },
                "status": {
                    "code": "o",
                    "display": "LIBRARY USE ONLY",
                    "duedate": null
                },
                "volumes": [],
                "barcode": "1018953553014",
                "callNumber": "973.02 qC949",
                "itemType": null,
                "transitInfo": null,
                "copyNo": null,
                "holdCount": null,
                "fixedFields": null,
                "varFields": null
            }
        ]
    }
   }
   ```

### The Design Approach

The core approach of `sierra-ils-utils` revolves around three main components:

1. Generic HTTP Request Methods (GET, PUT, POST ...)
1. Endpoint Configurations derived from the Sierra Version `endpoints` dictionary
1. Data Response Models defined by the Sierra REST API Version

#### 1. Generic HTTP Request Methods

`sierra-ils-utils` provides HTTP methods -- for example `get()` -- as generic methods that can handle requests to endpoints defined in the ENDPOINTS dictionary.

By passing the endpoint name, HTTP method, and any required parameters or path variables, this method can construct the appropriate URL, send the request, and return the parsed response using the associated data model.
Benefits of the Generic Request Method:

- Code Reusability: One method to handle requests for all endpoints.
- Maintainability: Changes to the request logic can be made in one place, benefiting all endpoints.
- Extensibility: Easy to support new HTTP methods or endpoints by extending the ENDPOINTS dictionary without changing the core request logic.

#### 2. Endpoint Configuration (ENDPOINTS Dictionary)

The ENDPOINTS dictionary provides a centralized place to define the configuration for each API endpoint. Each key in this dictionary represents an endpoint and the associated value provides details such as the HTTP path, method, and expected response models for various HTTP status codes.

Example:

```python
ENDPOINTS = {
    "bibs": {
        "GET": {
            "path": "bibs/",
            "responses": {
                200: BibResultSet,
                400: ErrorCode,
                # ... other status codes ...
            }
        },
        # ... other HTTP methods ...
    }
}
```

##### Benefits of the ENDPOINTS Configuration:

- Centralized Configuration: All endpoint configurations are in one place, making it easier to manage and update.
- Flexibility: Can easily accommodate different response models for different HTTP status codes.
- Scalability: New endpoints or methods can be added without modifying the core logic of the API client.

#### 3. Data Response Models

Data models represent the structure of the response data we expect from the Sierra API. These models are Python classes that map to the expected JSON response structure from Sierra.

For example, the GET `bibs/` endpoint returns the `BibResultSet` data model  -- this represents the expected structure of the response. Each attribute of this model corresponds to a key in the JSON response. Nested JSON structures are represented by nested data models.

##### Benefits of Data Models:

- Type Safety: Provides a clear understanding of the data types and structure expected in the response.
- Code Readability: Named data models make the code more readable and self-documenting.
- Flexibility: Easy to modify and extend when the API response changes or when new fields are introduced.


## Future Considerations

**Extend Support for Other HTTP Methods**: 
    
As the Sierra API evolves or as you require more functionality, you can extend support for other HTTP methods (like DELETE, PUT, etc.) following the same pattern.

**Error Handling**: 

The current approach provides a basic structure for handling different response models based on HTTP status codes. This can be extended to provide more advanced error handling and logging mechanisms.

# sierra-ils-utils
Python wrappers for working with the Sierra ILS 

## Sierra API Client Documentation

### Introduction

This documentation provides an overview of the design approach for extending the Sierra API client. The primary objective is to create a flexible and extensible structure that allows for easy integration of new endpoints, response models, and HTTP methods.

### The Approach

The core of this approach revolves around three main components:

1. Data Models
1. Endpoint Configuration (ENDPOINTS dictionary)
1. Generic Request Method


#### 1. Data Models

Data models represent the structure of the response data we expect from the Sierra API. These are Python classes that map to the expected JSON response structure.

For example, for the GET bibs/ endpoint, the BibResultSet data model represents the expected structure of the response. Each attribute of this model corresponds to a key in the JSON response. Nested JSON structures are represented by nested data models.
Benefits of Data Models:

- Type Safety: Provides a clear understanding of the data types and structure expected in the response.
- Code Readability: Named data models make the code more readable and self-documenting.
- Flexibility: Easy to modify and extend when the API response changes or when new fields are introduced.

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

Benefits of the ENDPOINTS Configuration:

- Centralized Configuration: All endpoint configurations are in one place, making it easier to manage and update.
- Flexibility: Can easily accommodate different response models for different HTTP status codes.
- Scalability: New endpoints or methods can be added without modifying the core logic of the API client.

#### 3. Generic Request Method

The request_endpoint method is a generic function that can handle requests to any endpoint defined in the ENDPOINTS dictionary. By passing the endpoint name, HTTP method, and any required parameters or path variables, this method can construct the appropriate URL, send the request, and return the parsed response using the associated data model.
Benefits of the Generic Request Method:

- Code Reusability: One method to handle requests for all endpoints.
- Maintainability: Changes to the request logic can be made in one place, benefiting all endpoints.
- Extensibility: Easy to support new HTTP methods or endpoints by extending the ENDPOINTS dictionary without changing the core request logic.

## Future Considerations

**Extend Support for Other HTTP Methods**: 
    
As the Sierra API evolves or as you require more functionality, you can extend support for other HTTP methods (like DELETE, PUT, etc.) following the same pattern.

**Error Handling**: 

The current approach provides a basic structure for handling different response models based on HTTP status codes. This can be extended to provide more advanced error handling and logging mechanisms.

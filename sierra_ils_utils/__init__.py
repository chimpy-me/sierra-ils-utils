from .sierra_rest_client import SierraRESTClient

# Create aliases
SierraAPI = SierraRESTClient

__all__ = ["SierraRESTClient", "SierraAsyncPaginator", "SierraAPI", "Paginator"]
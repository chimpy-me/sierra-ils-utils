from importlib.metadata import version, PackageNotFoundError

from .sierra_rest_client import SierraRESTClient
from .sierra_datetime import SierraDateTime, SierraDate
from .utils import get_max_record_id

# Get version from package metadata
try:
    __version__ = version("sierra-ils-utils")
except PackageNotFoundError:
    __version__ = "unknown"

# Create an alias
SierraAPI = SierraRESTClient

__all__ = [
    "__version__",
    "SierraRESTClient",
    "SierraAPI",
    "SierraDateTime",
    "SierraDate",
    "get_max_record_id",
]
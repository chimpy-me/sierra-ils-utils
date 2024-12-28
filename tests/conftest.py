import asyncio
from httpx import Response
import pytest
import pytest_asyncio
import respx
from sierra_ils_utils import SierraRESTClient

@pytest.fixture
def mock_client():
    client = SierraRESTClient(
        base_url="http://fake.test",
        client_id="FAKE_ID",
        client_secret="FAKE_SECRET",
        max_retries=1
    )
    yield client
    client.close()  # or await client.aclose() if you need async close
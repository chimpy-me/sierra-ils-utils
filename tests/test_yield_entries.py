import pytest
from unittest.mock import patch, AsyncMock
from sierra_ils_utils import SierraRESTClient

# @pytest.fixture
# def mock_client():
#     """
#     Provides a SierraRESTClient with a fake base URL
#     to demonstrate usage and avoid making real network calls.
#     """
#     client = SierraRESTClient(
#         base_url="http://fake.test",
#         client_id="FAKE_ID",
#         client_secret="FAKE_SECRET",
#         max_retries=1
#     )
#     yield client
#     client.close()


# def test_yield_entries_multiple_pages(mock_client):
#     """
#     Example: Fetching multiple pages of entries using yield_entries.

#     Suppose we are fetching items from the "items/" endpoint and expect multiple
#     pages of data. This test simulates how the method works and shows
#     how to consume the generator in a real-world use case.
#     """

#     # Mock the behavior of `_fetch_page_async` to simulate paginated responses.
#     # For example:
#     # - The first page contains {"id": 0} and {"id": 1}
#     # - The second page contains {"id": 2} and {"id": 3}
#     # - The third page is empty, signaling the end.
#     async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
#         if start_id == 0:
#             return [{"id": 0}, {"id": 1}]
#         elif start_id == 2:
#             return [{"id": 2}, {"id": 3}]
#         else:
#             return []

#     with patch.object(
#         mock_client,
#         "_fetch_page_async",
#         new=AsyncMock(side_effect=fetch_side_effect)
#     ):
#         # Example usage:
#         # Consume the generator to fetch items from the "items/" endpoint.
#         print("Fetching items from the 'items/' endpoint...")
#         for i, entry in enumerate(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1)):
#             print(f"Entry {i}: {entry}")
#             # Stop early if needed
#             if i > 10:
#                 break

#         # Expected data:
#         # - Entries should include items with IDs: 0, 1, 2, 3
#         entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1))
#         assert len(entries) == 4
#         assert [e["id"] for e in entries] == [0, 1, 2, 3]


# def test_yield_entries_no_data(mock_client):
#     """
#     Example: Fetching entries when no data is available.

#     This test demonstrates how yield_entries behaves when no data is returned
#     from the endpoint. This might happen if there are no records matching the
#     query or if the system is empty.
#     """
#     # Simulate an empty response for all fetches.
#     with patch.object(
#         mock_client,
#         "_fetch_page_async",
#         new=AsyncMock(return_value=[])
#     ):
#         print("Attempting to fetch items from an empty endpoint...")
#         entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1))
#         print("No entries found.") if not entries else print(entries)

#         # Assert that the generator yields nothing.
#         assert entries == []


# def test_yield_entries_single_page(mock_client):
#     """
#     Example: Fetching a single page of entries.

#     This test demonstrates how yield_entries handles a situation where there
#     is only a single page of data available.
#     """
#     async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
#         if start_id == 0:
#             return [{"id": 0}, {"id": 1}]
#         return []

#     with patch.object(
#         mock_client,
#         "_fetch_page_async",
#         new=AsyncMock(side_effect=fetch_side_effect)
#     ):
#         print("Fetching a single page of items from the 'items/' endpoint...")
#         entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1))
#         print(f"Fetched entries: {entries}")

#         # Assert that the generator yields only one page of results.
#         assert len(entries) == 2
#         assert [e["id"] for e in entries] == [0, 1]


# def test_yield_entries_with_large_concurrency(mock_client):
#     """
#     Example: Using high concurrency to speed up paginated requests.

#     This test demonstrates how yield_entries can handle multiple concurrent
#     requests to fetch paginated data.
#     """
#     async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
#         if start_id == 0:
#             return [{"id": 0}, {"id": 1}]
#         elif start_id == 2:
#             return [{"id": 2}, {"id": 3}]
#         elif start_id == 4:
#             return [{"id": 4}, {"id": 5}]
#         else:
#             return []

#     with patch.object(
#         mock_client,
#         "_fetch_page_async",
#         new=AsyncMock(side_effect=fetch_side_effect)
#     ):
#         # Using a higher concurrency level to fetch data faster.
#         print("Fetching items with high concurrency...")
#         entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=3))
#         print(f"Fetched entries: {entries}")

#         # Assert that the generator fetches all available entries.
#         assert len(entries) == 6
#         assert [e["id"] for e in entries] == [0, 1, 2, 3, 4, 5]


def test_yield_entries_multiple_pages(mock_client):
    """
    Example: Fetching multiple pages of entries using yield_entries.

    Suppose we are fetching items from the "items/" endpoint and expect multiple
    pages of data. This test simulates how the method works and shows
    how to consume the generator in a real-world use case.
    """

    # Mock the behavior of `_fetch_page_async` to simulate paginated responses.
    async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
        if start_id == 0:
            return [{"id": 0}, {"id": 1}]
        elif start_id == 2:
            return [{"id": 2}, {"id": 3}]
        else:
            return []

    with patch.object(
        mock_client,
        "_fetch_page_async",
        new=AsyncMock(side_effect=fetch_side_effect)
    ):
        # Example usage:
        print("Fetching items from the 'items/' endpoint...")
        entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1))
        print(f"Fetched entries: {entries}")

        # Assert expected results
        assert len(entries) == 4
        assert [e["id"] for e in entries] == [0, 1, 2, 3]

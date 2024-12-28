import pytest
from unittest.mock import patch, AsyncMock
from sierra_ils_utils import SierraRESTClient

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
        entries = list(mock_client.yield_entries("items/", start_id=0, limit=2))
        print(f"Fetched entries: {entries}")

        # Assert expected results
        assert len(entries) == 4
        assert [e["id"] for e in entries] == [0, 1, 2, 3]

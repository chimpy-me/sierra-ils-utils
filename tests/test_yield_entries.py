from unittest.mock import patch, AsyncMock

def test_yield_entries_empty_response(mock_client):
    """
    Test that yield_entries immediately stops if
    _fetch_page_async returns no entries on the first fetch.
    """
    with patch.object(mock_client, "_fetch_page_async", new=AsyncMock(return_value=[])) as mock_fetch:
        entries = list(mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1))
        assert entries == []
        assert mock_fetch.call_count == 1


def test_yield_entries_single_batch(mock_client):
    """
    Test that yield_entries yields entries from a single batch
    and stops when the next batch is empty.
    """
    async def fetch_side_effect(endpoint, start_id, limit=2000, extra_params=None):
        if start_id == 0:
            return [{"id": 0}, {"id": 1}]
        else:
            return []

    with patch.object(mock_client, "_fetch_page_async", new=AsyncMock(side_effect=fetch_side_effect)) as mock_fetch:
        entries = list(
            mock_client.yield_entries(endpoint="items/", start_id=0, limit=2, concurrency=1)
        )
        assert len(entries) == 2
        assert [e["id"] for e in entries] == [0, 1]
        assert mock_fetch.call_count == 2  # first call non-empty, second call empty => stop


def test_yield_entries_multiple_batches(mock_client):
    """
    Test fetching multiple batches in a single 'concurrency=1' scenario
    to see how start_id increments each time.
    """

    # If start_id=0 => return {0,1}
    # If start_id=2 => return {2,3}
    # If start_id=4 => return {4,5}
    # If start_id=6 => empty => break
    async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
        if start_id < 6:
            return [{"id": start_id}, {"id": start_id + 1}]
        else:
            return []

    with patch.object(mock_client, "_fetch_page_async", new=AsyncMock(side_effect=fetch_side_effect)) as mock_fetch:
        entries_collected = list(
            mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=1)
        )

        expected_ids = [0, 1, 2, 3, 4, 5]
        actual_ids = [e["id"] for e in entries_collected]
        assert actual_ids == expected_ids
        # We expect 4 calls:
        #  1) start_id=0  => 2 items
        #  2) start_id=2  => 2 items
        #  3) start_id=4  => 2 items
        #  4) start_id=6  => empty => stop
        assert mock_fetch.call_count == 4


def test_yield_entries_concurrent_batches(mock_client):
    """
    Test concurrency > 1, verifying that multiple page ranges
    are fetched per iteration of the while loop.
    """

    async def fetch_side_effect(endpoint, start_id, limit=2, extra_params=None):
        """
        1st iteration:
          start_id=0 => returns [{id:0}, {id:1}]
          start_id=2 => returns [{id:2}]
        2nd iteration:
          start_id=3 => empty
          start_id=5 => empty
        => stop
        """
        if start_id == 0:
            return [{"id": 0}, {"id": 1}]
        elif start_id == 2:
            return [{"id": 2}]
        else:
            return []

    with patch.object(mock_client, "_fetch_page_async", new=AsyncMock(side_effect=fetch_side_effect)) as mock_fetch:
        entries_collected = list(
            mock_client.yield_entries("items/", start_id=0, limit=2, concurrency=2)
        )
        # After the first iteration's batch, we expect 3 items: 0,1,2 (sorted => 0,1,2)
        assert [x["id"] for x in entries_collected] == [0, 1, 2]

        # The while loop runs at least twice:
        # 1) concurrency=2 => start_id=0, start_id=2  => partial data
        # 2) concurrency=2 => start_id=3, start_id=5  => empty => break
        assert mock_fetch.call_count == 4

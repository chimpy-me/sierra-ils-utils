import pytest
import respx
from httpx import Response
from unittest.mock import MagicMock, AsyncMock
from sierra_ils_utils import SierraRESTClient
from sierra_ils_utils.utils import get_max_record_id, v6_create_list_query


class TestGetMaxRecordId:
    """Tests for the get_max_record_id utility function."""

    def test_upward_search_finds_max_id(self):
        """
        Test Case A: start yields entries, exponential search upward finds the max.
        Simulates a scenario where max valid ID is 150.
        """
        max_id = 150

        def mock_request(method, endpoint, params):
            """Return entries if min_id <= max_id, empty otherwise."""
            min_id = int(params['id'].strip('[,]').split(',')[0])
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if min_id <= max_id:
                # Return some entries (count doesn't matter, just > 0)
                response.json.return_value = {'entries': [{'id': i} for i in range(min(3, max_id - min_id + 1))]}
            else:
                response.json.return_value = {'entries': []}
            return response

        client = MagicMock()
        client.request = mock_request

        result = get_max_record_id(client, 'bibs/', start=0)
        assert result == max_id

    def test_upward_search_with_nonzero_start(self):
        """
        Test Case A with a non-zero start value that's below the max.
        """
        max_id = 500

        def mock_request(method, endpoint, params):
            min_id = int(params['id'].strip('[,]').split(',')[0])
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if min_id <= max_id:
                response.json.return_value = {'entries': [{'id': 1}]}
            else:
                response.json.return_value = {'entries': []}
            return response

        client = MagicMock()
        client.request = mock_request

        result = get_max_record_id(client, 'patrons/', start=100)
        assert result == max_id

    def test_downward_search_when_start_overshoots(self):
        """
        Test Case B: start is above max valid ID, binary search downward.
        """
        max_id = 75

        def mock_request(method, endpoint, params):
            min_id = int(params['id'].strip('[,]').split(',')[0])
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if min_id <= max_id:
                response.json.return_value = {'entries': [{'id': 1}]}
            else:
                response.json.return_value = {'entries': []}
            return response

        client = MagicMock()
        client.request = mock_request

        # Start at 1000, which is way above max_id of 75
        result = get_max_record_id(client, 'items/', start=1000)
        assert result == max_id

    def test_max_id_at_zero(self):
        """
        Edge case: max valid ID is 0.
        """
        max_id = 0

        def mock_request(method, endpoint, params):
            min_id = int(params['id'].strip('[,]').split(',')[0])
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if min_id <= max_id:
                response.json.return_value = {'entries': [{'id': 0}]}
            else:
                response.json.return_value = {'entries': []}
            return response

        client = MagicMock()
        client.request = mock_request

        result = get_max_record_id(client, 'bibs/', start=0)
        assert result == max_id

    def test_no_entries_at_all(self):
        """
        Edge case: no entries exist (even at ID 0).
        Should return 0 after downward search finds nothing.
        """
        def mock_request(method, endpoint, params):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.json.return_value = {'entries': []}
            return response

        client = MagicMock()
        client.request = mock_request

        result = get_max_record_id(client, 'bibs/', start=100)
        assert result == 0

    def test_respects_max_safety_cap(self):
        """
        Test that exponential search respects max_safety parameter.
        """
        # All IDs return entries (simulating infinite range)
        def mock_request(method, endpoint, params):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.json.return_value = {'entries': [{'id': 1}]}
            return response

        client = MagicMock()
        client.request = mock_request

        # With a small max_safety, should cap the search
        result = get_max_record_id(client, 'bibs/', start=0, max_safety=100)
        assert result == 100

    def test_correct_api_params_sent(self):
        """
        Verify that the correct parameters are sent to the API.
        """
        client = MagicMock()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {'entries': []}
        client.request.return_value = response

        get_max_record_id(client, 'patrons/', start=500, limit=25)

        # Check the first call
        call_args = client.request.call_args_list[0]
        assert call_args[0] == ('GET', 'patrons/')
        assert call_args[1]['params']['limit'] == 25
        assert call_args[1]['params']['fields'] == 'id'
        assert call_args[1]['params']['id'] == '[500,]'


class TestV6CreateListQuery:
    """Tests for the v6_create_list_query utility function."""

    @pytest.mark.asyncio
    async def test_basic_query_returns_records(self):
        """
        Test that a basic query returns hydrated records.
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}items/query"
        item1_url = f"{base_url}v6/items/12345"
        item2_url = f"{base_url}v6/items/12346"

        with respx.mock:
            # Mock token endpoint
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            # Mock query endpoint - returns links to items
            respx.post(query_url).mock(
                return_value=Response(200, json={
                    "total": 2,
                    "entries": [
                        {"link": item1_url},
                        {"link": item2_url},
                    ]
                })
            )

            # Mock individual item fetches
            respx.get(item1_url).mock(
                return_value=Response(200, json={"id": "12345", "barcode": "A000001"})
            )
            respx.get(item2_url).mock(
                return_value=Response(200, json={"id": "12346", "barcode": "A000002"})
            )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            query = {
                "queries": [{
                    "target": {"record": {"type": "item"}, "field": {"tag": "b"}},
                    "expr": {"op": "in", "operands": ["A000001", "A000002"]}
                }]
            }

            results = await v6_create_list_query(
                client, "items", query,
                fields="id,barcode"
            )

            assert len(results) == 2
            barcodes = {r["barcode"] for r in results}
            assert barcodes == {"A000001", "A000002"}

            await client.aclose()

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_list(self):
        """
        Test that a query with no matches returns an empty list.
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}items/query"

        with respx.mock:
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            respx.post(query_url).mock(
                return_value=Response(200, json={"total": 0, "entries": []})
            )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            query = {"queries": []}
            results = await v6_create_list_query(client, "items", query)

            assert results == []
            await client.aclose()

    @pytest.mark.asyncio
    async def test_pagination_fetches_all_records(self):
        """
        Test that pagination works correctly when query returns more than query_limit.
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}items/query"

        with respx.mock:
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            # First query returns 2 items (at limit)
            # Second query returns 1 item (less than limit, indicating end)
            query_route = respx.post(query_url)
            query_route.side_effect = [
                Response(200, json={
                    "entries": [
                        {"link": f"{base_url}v6/items/1"},
                        {"link": f"{base_url}v6/items/2"},
                    ]
                }),
                Response(200, json={
                    "entries": [
                        {"link": f"{base_url}v6/items/3"},
                    ]
                }),
            ]

            # Mock individual item fetches
            respx.get(f"{base_url}v6/items/1").mock(
                return_value=Response(200, json={"id": "1"})
            )
            respx.get(f"{base_url}v6/items/2").mock(
                return_value=Response(200, json={"id": "2"})
            )
            respx.get(f"{base_url}v6/items/3").mock(
                return_value=Response(200, json={"id": "3"})
            )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            query = {"queries": []}
            results = await v6_create_list_query(
                client, "items", query,
                query_limit=2  # Small limit to trigger pagination
            )

            assert len(results) == 3
            ids = {r["id"] for r in results}
            assert ids == {"1", "2", "3"}

            await client.aclose()

    @pytest.mark.asyncio
    async def test_endpoint_normalization(self):
        """
        Test that endpoint with slashes is normalized correctly.
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}bibs/query"
        bib_url = f"{base_url}v6/bibs/999"

        with respx.mock:
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            respx.post(query_url).mock(
                return_value=Response(200, json={
                    "entries": [{"link": bib_url}]
                })
            )

            respx.get(bib_url).mock(
                return_value=Response(200, json={"id": "999", "title": "Test Book"})
            )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            # Test with leading/trailing slashes
            query = {"queries": []}
            results = await v6_create_list_query(client, "/bibs/", query, fields="id,title")

            assert len(results) == 1
            assert results[0]["title"] == "Test Book"

            await client.aclose()

    @pytest.mark.asyncio
    async def test_concurrency_parameter(self):
        """
        Test that concurrency parameter is respected (verifies semaphore is used).
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}items/query"

        with respx.mock:
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            # Return 10 items
            entries = [{"link": f"{base_url}v6/items/{i}"} for i in range(10)]
            respx.post(query_url).mock(
                return_value=Response(200, json={"entries": entries})
            )

            # Mock all item fetches
            for i in range(10):
                respx.get(f"{base_url}v6/items/{i}").mock(
                    return_value=Response(200, json={"id": str(i)})
                )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            query = {"queries": []}
            results = await v6_create_list_query(
                client, "items", query,
                concurrency=2  # Low concurrency
            )

            assert len(results) == 10
            await client.aclose()

    @pytest.mark.asyncio
    async def test_extra_params_passed_to_get(self):
        """
        Test that extra **params are passed through to the GET requests.
        """
        base_url = "https://catalog.library.org/iii/sierra-api/v6/"
        token_url = f"{base_url}token"
        query_url = f"{base_url}items/query"
        item_url = f"{base_url}v6/items/123"

        with respx.mock:
            respx.post(token_url).mock(
                return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
            )

            respx.post(query_url).mock(
                return_value=Response(200, json={
                    "entries": [{"link": item_url}]
                })
            )

            # Capture the GET request to verify params
            get_route = respx.get(item_url).mock(
                return_value=Response(200, json={"id": "123"})
            )

            client = SierraRESTClient(
                base_url=base_url,
                client_id="client_id",
                client_secret="client_secret"
            )

            query = {"queries": []}
            await v6_create_list_query(
                client, "items", query,
                fields="id,barcode",
                suppressed="false"  # Extra param
            )

            # Check that the GET request included the extra param
            assert get_route.called
            request = get_route.calls[0].request
            assert b"suppressed=false" in request.url.query

            await client.aclose()

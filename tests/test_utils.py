import pytest
from unittest.mock import MagicMock
from sierra_ils_utils.utils import get_max_record_id


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

import pytest
import respx
import httpx
from httpx import Response
import asyncio
from sierra_ils_utils import SierraRESTClient

@pytest.mark.asyncio
async def test_async_token_fetch():
    """
    Tests that an async token fetch occurs if no token is set.
    """
    # Mock the token endpoint
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"
    
    with respx.mock:
        # Suppose the auth endpoint returns a valid token
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "FAKE_TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        )

        # Make an async request that triggers token retrieval
        route_url = "info/token"
        # Mock the GET endpoint after token retrieval
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )
        
        response = await client.async_request("GET", route_url)

        assert response.status_code == 200
        assert "FAKE_TOKEN" in client.access_token  # Confirm our class stored the token
        await client.aclose()


def test_sync_token_fetch():
    """
    Tests that a sync token fetch occurs if no token is set.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        # Suppose the auth endpoint returns a valid token
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "FAKE_TOKEN_SYNC", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        )

        route_url = "info/token"
        # Mock a GET
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )

        response = client.request("GET", route_url)
        assert response.status_code == 200
        assert "FAKE_TOKEN_SYNC" in client.access_token
        client.close()


def test_sync_401_refresh():
    """
    Tests that if we get a 401, we do one token refresh and retry once.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        # First token fetch
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "OLD_TOKEN", "expires_in": 100})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        )

        # Make an initial request to get the token
        route_url = "some/endpoint"
        first_attempt = respx.get("https://catalog.library.org/iii/sierra-api/v6/some/endpoint").mock(
            return_value=Response(401)  # Force a 401 on first attempt
        )

        # After refresh, we want to respond with 200
        # so let's define a second route, or just re-mock the same route
        second_attempt = first_attempt.side_effect = [
            Response(401),
            Response(200, json={"message": "success"})
        ]

        # Now for the new token fetch after 401
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "NEW_TOKEN", "expires_in": 3600})
        )
        
        response = client.request("GET", route_url)
        assert response.status_code == 200
        assert client.access_token == "NEW_TOKEN"
        client.close()


@pytest.mark.asyncio
async def test_async_5xx_retry():
    """
    Tests that if we get a 5xx error in async, the client retries, then eventually succeeds.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        # Return valid token
        respx.post(token_url).mock(return_value=Response(200, json={"access_token": "ASYNC_TOKEN", "expires_in": 3600}))

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=2  # We only want 2 attempts
        )

        route_url = "some/error/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            Response(503),  # First attempt => 503
            Response(200, json={"message": "finally ok"})  # Second attempt => success
        ]

        response = await client.async_request("GET", route_url)
        assert response.status_code == 200
        assert response.json()["message"] == "finally ok"
        await client.aclose()


def test_sync_5xx_retry():
    """
    Tests that if we get a 5xx error in sync, the client retries, then eventually succeeds.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "SYNC_TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=3,
            backoff_factor=0.01  # Fast backoff for tests
        )

        route_url = "some/error/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            Response(503),  # First attempt => 503
            Response(502),  # Second attempt => 502
            Response(200, json={"message": "finally ok"})  # Third attempt => success
        ]

        response = client.request("GET", route_url)
        assert response.status_code == 200
        assert response.json()["message"] == "finally ok"
        client.close()


def test_sync_5xx_exhausts_retries():
    """
    Tests that sync request returns the error response after exhausting retries.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "SYNC_TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=2,
            backoff_factor=0.01
        )

        route_url = "some/error/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            Response(503),  # First attempt
            Response(503),  # Second attempt - exhausts retries
        ]

        response = client.request("GET", route_url)
        assert response.status_code == 503  # Returns the error after retries exhausted
        client.close()


@pytest.mark.asyncio
async def test_async_401_refresh():
    """
    Tests that if we get a 401 in async, we force refresh the token and retry,
    even if the token hasn't technically expired yet.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        # First token fetch returns old token that hasn't expired yet
        token_mock = respx.post(token_url)
        token_mock.side_effect = [
            Response(200, json={"access_token": "OLD_TOKEN", "expires_in": 3600}),
            Response(200, json={"access_token": "NEW_TOKEN", "expires_in": 3600}),
        ]

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        )

        route_url = "some/endpoint"
        route_mock = respx.get("https://catalog.library.org/iii/sierra-api/v6/some/endpoint")
        route_mock.side_effect = [
            Response(401),  # First attempt with old token
            Response(200, json={"message": "success"})  # After token refresh
        ]

        response = await client.async_request("GET", route_url)
        assert response.status_code == 200
        assert client.access_token == "NEW_TOKEN"
        await client.aclose()


def test_sync_timeout_retry():
    """
    Tests that sync request retries on timeout and eventually succeeds.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=3,
            backoff_factor=0.01
        )

        route_url = "some/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            httpx.ReadTimeout("timeout"),  # First attempt times out
            Response(200, json={"message": "ok"})  # Second attempt succeeds
        ]

        response = client.request("GET", route_url)
        assert response.status_code == 200
        client.close()


def test_sync_timeout_exhausts_retries():
    """
    Tests that sync request raises exception after exhausting retries on timeout.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=2,
            backoff_factor=0.01
        )

        route_url = "some/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            httpx.ReadTimeout("timeout"),
            httpx.ReadTimeout("timeout"),
        ]

        with pytest.raises(httpx.ReadTimeout):
            client.request("GET", route_url)
        client.close()


@pytest.mark.asyncio
async def test_async_timeout_retry():
    """
    Tests that async request retries on timeout and eventually succeeds.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=3,
            backoff_factor=0.01
        )

        route_url = "some/endpoint"
        route_mock = respx.get(f"https://catalog.library.org/iii/sierra-api/v6/{route_url}")
        route_mock.side_effect = [
            httpx.ConnectTimeout("timeout"),  # First attempt times out
            Response(200, json={"message": "ok"})  # Second attempt succeeds
        ]

        response = await client.async_request("GET", route_url)
        assert response.status_code == 200
        await client.aclose()


def test_sync_401_does_not_infinite_loop():
    """
    Tests that repeated 401s don't cause infinite token refresh loops.

    Scenario: The token endpoint keeps returning tokens that immediately get 401'd.
    The client should only refresh once, retry once, then return the 401.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"
    token_call_count = 0

    with respx.mock:
        def token_side_effect(request):
            nonlocal token_call_count
            token_call_count += 1
            # Keep returning "valid" tokens that will get rejected
            return Response(200, json={"access_token": f"BAD_TOKEN_{token_call_count}", "expires_in": 3600})

        respx.post(token_url).mock(side_effect=token_side_effect)

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=10  # High retry count to prove we don't loop
        )

        route_url = "some/endpoint"
        # Always return 401 - simulating a broken auth system
        respx.get("https://catalog.library.org/iii/sierra-api/v6/some/endpoint").mock(
            return_value=Response(401)
        )

        response = client.request("GET", route_url)

        # Should return 401, not loop forever
        assert response.status_code == 401
        # Should only fetch token twice: once initially, once on 401 refresh
        assert token_call_count == 2
        client.close()


@pytest.mark.asyncio
async def test_async_401_does_not_infinite_loop():
    """
    Tests that repeated 401s don't cause infinite token refresh loops in async.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"
    token_call_count = 0

    with respx.mock:
        def token_side_effect(request):
            nonlocal token_call_count
            token_call_count += 1
            return Response(200, json={"access_token": f"BAD_TOKEN_{token_call_count}", "expires_in": 3600})

        respx.post(token_url).mock(side_effect=token_side_effect)

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=10
        )

        route_url = "some/endpoint"
        respx.get("https://catalog.library.org/iii/sierra-api/v6/some/endpoint").mock(
            return_value=Response(401)
        )

        response = await client.async_request("GET", route_url)

        assert response.status_code == 401
        assert token_call_count == 2  # Initial + one forced refresh
        await client.aclose()


def test_sync_context_manager():
    """
    Tests that the sync context manager properly closes the client.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )

        with SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        ) as client:
            response = client.request("GET", "info/token")
            assert response.status_code == 200

        # After exiting context, client should be closed
        assert client._sync_client.is_closed


@pytest.mark.asyncio
async def test_async_context_manager():
    """
    Tests that the async context manager properly closes the client.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )

        async with SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret"
        ) as client:
            response = await client.async_request("GET", "info/token")
            assert response.status_code == 200

        # After exiting context, async client should be closed
        assert client._async_client.is_closed


def test_custom_sync_client_injection():
    """
    Tests that a custom sync client can be injected.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )

        # Create a custom httpx client
        custom_client = httpx.Client(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            timeout=60.0  # Different timeout than default
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            sync_client=custom_client
        )

        # Verify custom client is used
        assert client._sync_client is custom_client

        response = client.request("GET", "info/token")
        assert response.status_code == 200
        client.close()


@pytest.mark.asyncio
async def test_custom_async_client_injection():
    """
    Tests that a custom async client can be injected.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"

    with respx.mock:
        respx.post(token_url).mock(
            return_value=Response(200, json={"access_token": "TOKEN", "expires_in": 3600})
        )
        respx.get("https://catalog.library.org/iii/sierra-api/v6/info/token").mock(
            return_value=Response(200, json={"message": "OK"})
        )

        # Create a custom httpx async client
        custom_client = httpx.AsyncClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            timeout=httpx.Timeout(60.0)
        )

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            async_client=custom_client
        )

        # Verify custom client is used
        assert client._async_client is custom_client

        response = await client.async_request("GET", "info/token")
        assert response.status_code == 200
        await client.aclose()


def test_token_refresh_on_expiry_during_5xx_retry():
    """
    Tests that token is refreshed if it expires during 5xx retry backoff.
    """
    token_url = "https://catalog.library.org/iii/sierra-api/v6/token"
    token_call_count = 0

    with respx.mock:
        def token_side_effect(request):
            nonlocal token_call_count
            token_call_count += 1
            # First token expires immediately (expires_in=0)
            # Second token is valid
            expires_in = 0 if token_call_count == 1 else 3600
            return Response(200, json={"access_token": f"TOKEN_{token_call_count}", "expires_in": expires_in})

        respx.post(token_url).mock(side_effect=token_side_effect)

        route_mock = respx.get("https://catalog.library.org/iii/sierra-api/v6/some/endpoint")
        route_mock.side_effect = [
            Response(503),  # First attempt fails with 5xx
            Response(200, json={"message": "ok"})  # Second attempt succeeds
        ]

        client = SierraRESTClient(
            base_url="https://catalog.library.org/iii/sierra-api/v6/",
            client_id="client_id",
            client_secret="client_secret",
            max_retries=2,
            backoff_factor=0.01  # Fast backoff for tests
        )

        response = client.request("GET", "some/endpoint")

        assert response.status_code == 200
        # Should have fetched token twice: initial (expired) + refresh on retry
        assert token_call_count == 2
        assert client.access_token == "TOKEN_2"
        client.close()

import pytest
import respx
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

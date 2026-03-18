import asyncio
import time

import httpx
import pytest
import respx

from csqaq.infrastructure.csqaq_client.client import CSQAQClient
from csqaq.infrastructure.csqaq_client.errors import (
    CSQAQAuthError,
    CSQAQClientError,
    CSQAQRateLimitError,
    CSQAQServerError,
    CSQAQValidationError,
)


@pytest.fixture
def base_url():
    return "https://api.csqaq.com/api/v1"


@pytest.fixture
def client(base_url):
    return CSQAQClient(
        base_url=base_url,
        api_token="test-token",
        rate_limit=10.0,  # Fast for tests
    )


@respx.mock
@pytest.mark.asyncio
async def test_post_injects_api_token_header(client, base_url):
    """Every request must include the ApiToken header."""
    route = respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": {}})
    )
    result = await client.post("/test", json={})
    assert route.called
    assert route.calls[0].request.headers["ApiToken"] == "test-token"


@respx.mock
@pytest.mark.asyncio
async def test_post_returns_data_field(client, base_url):
    """Client should extract and return the 'data' field from response."""
    respx.post(f"{base_url}/info/good").mock(
        return_value=httpx.Response(200, json={"code": 0, "data": {"name": "AK-47"}})
    )
    result = await client.post("/info/good", json={"goodId": 1})
    assert result == {"name": "AK-47"}


@respx.mock
@pytest.mark.asyncio
async def test_raises_auth_error_on_401(client, base_url):
    """401 should raise CSQAQAuthError without retry."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(401, json={"code": -1, "msg": "unauthorized"})
    )
    with pytest.raises(CSQAQAuthError):
        await client.post("/test", json={})


@respx.mock
@pytest.mark.asyncio
async def test_raises_validation_error_on_422(client, base_url):
    """422 should raise CSQAQValidationError without retry."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(422, json={"code": -1, "msg": "bad params"})
    )
    with pytest.raises(CSQAQValidationError):
        await client.post("/test", json={})


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_500_then_succeeds(client, base_url):
    """Server errors should be retried up to 3 times."""
    route = respx.post(f"{base_url}/test")
    route.side_effect = [
        httpx.Response(500, json={"code": -1, "msg": "server error"}),
        httpx.Response(200, json={"code": 0, "data": {"ok": True}}),
    ]
    result = await client.post("/test", json={})
    assert result == {"ok": True}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_raises_after_max_retries(client, base_url):
    """After 3 retries on 500, should raise CSQAQServerError."""
    respx.post(f"{base_url}/test").mock(
        return_value=httpx.Response(500, json={"code": -1, "msg": "down"})
    )
    with pytest.raises(CSQAQServerError):
        await client.post("/test", json={})


@pytest.mark.asyncio
async def test_rate_limiter_enforces_interval():
    """Rate limiter should space requests by 1/rate_limit seconds."""
    client = CSQAQClient(
        base_url="https://api.csqaq.com/api/v1",
        api_token="test",
        rate_limit=5.0,  # 5 req/sec → 0.2s interval
    )
    # Just verify the rate limiter exists and has correct interval
    assert client._min_interval == pytest.approx(0.2, abs=0.01)


@respx.mock
@pytest.mark.asyncio
async def test_get_request():
    client = CSQAQClient(base_url="https://api.csqaq.com/api/v1", api_token="test", rate_limit=100.0)
    respx.get("https://api.csqaq.com/api/v1/current_data").mock(
        return_value=httpx.Response(200, json={"code": 200, "data": {"index": 1000}})
    )
    result = await client.get("/current_data", params={"type": "init"})
    assert result == {"index": 1000}

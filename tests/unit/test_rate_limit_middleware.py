async def test_middleware_returns_429_when_rate_limit_exceeded(gateway_client):
    """Test: rate limit middleware blocks request when rate limit is exceeded."""
    gateway_app_from_client = gateway_client._transport.app

    # Simulate rate limiter blocking the request
    gateway_app_from_client.state.limiter.allow_next = False

    resp = await gateway_client.get("/hello")

    assert resp.status_code == 429


async def test_middleware_allows_request_when_within_rate_limit(gateway_client):
    """Test: rate limit middleware allows request when rate limit is not exceeded."""
    gateway_app_from_client = gateway_client._transport.app

    # Simulate rate limiter allowing request
    gateway_app_from_client.state.limiter.allow_next = True

    resp = await gateway_client.get("/hello")

    data = resp.json()

    assert resp.status_code == 200
    assert data["message"] == "hello from upstream"
    assert 'x-ratelimit-remaining' in resp.headers

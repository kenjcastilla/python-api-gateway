async def test_nonexistent_route_returns_404(gateway_client):
    """Test: request non-existent routes returns 404 error status code."""
    resp = await gateway_client.get('/nonexistent')
    print(f'Response status code: {resp.status_code}')

    assert resp.status_code == 404
    assert resp.json()['detail'] == 'No upstream route found'


async def test_upstream_connection_failure_returns_502(gateway_client):
    """Test: upstream connection failures return 502 error (bad gateway) status code."""
    from gateway.main import application as gateway_app
    from unittest.mock import AsyncMock

    # Mock http_client to raise exception
    gateway_app.state.http_client.request = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    resp = await gateway_client.get("/hello")  # valid route

    assert resp.status_code == 502
    assert 'Connection refused' in resp.json()['detail']


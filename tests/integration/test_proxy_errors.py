async def test_upstream_failure_returns_404_502(gateway_client):
    resp = await gateway_client.get('/nonexistent')

    assert resp.status_code in (404, 502)

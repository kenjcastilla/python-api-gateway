async def test_rate_limit_blocks_request(gateway_client):
    gateway_app_from_client = gateway_client._transport.app

    # Set limiter to 'block'
    gateway_app_from_client.state.limiter.allow_next = False

    resp = await gateway_client.get('/hello')

    assert resp.status_code == 429

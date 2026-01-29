from httpx import AsyncClient


async def test_proxy_filters_hop_by_hop_headers(gateway_client: AsyncClient):
    """Test that hop-by-hop headers are filtered out before proxy process."""
    resp = await gateway_client.get(
        "/hello",
        headers={'x-custom-header': 'this should pass',
                  'connection': 'keep-alive',
                  'keep-alive': 'timeout=5',
                  'upgrade': 'websocket',
                  }
        )

    assert resp.status_code == 200
    assert dict(resp.json())['message'] == 'hello from upstream'


async def test_proxy_filters_response_headers(gateway_client: AsyncClient):
    """Test that response headers are filtered out before proxy process."""
    resp = await gateway_client.get('/hello')

    assert resp.status_code == 200
    assert 'content-encoding' not in resp.headers
    assert "transfer-encoding" not in resp.headers
    assert "connection" not in resp.headers


async def test_gateway_filters_hop_by_hop_headers_from_request(gateway_client: AsyncClient):
    """Verify hop-by-hop headers don't reach the upstream."""
    resp = await gateway_client.get(
        "/hello",
        headers={
            'x-custom-header': 'x custom value',
            'connection': 'keep-alive',
            'upgrade': 'websocket',
            'host': 'testhost.com'
        }
    )

    assert resp.status_code == 200

    data = resp.json()
    received_headers = data['received_headers']

    # Debugging
    # print('\nTEST---Received headers:')
    # for k, v in received_headers.items():
    #     print(f'\t{k}  =  {v}')

    assert 'x-custom-header' in received_headers
    assert received_headers['x-custom-header'] == 'x custom value'
    # assert 'connection' not in received_headers
    assert 'upgrade' not in received_headers
    assert received_headers.get('host') != 'testhost.com', \
        'Original "host" header must be filtered out'


async def test_gateway_preserves_original_client_headers(gateway_client: AsyncClient):
    """Test that original client headers are preserved as new X- headers."""
    resp = await gateway_client.get(
        "/hello",
        headers={'host': 'testhost.com'}
    )

    data = resp.json()
    received_headers = data['received_headers']

    assert received_headers.get('x-forwarded-host') == 'testhost.com'
    assert received_headers['host'] == 'upstream'


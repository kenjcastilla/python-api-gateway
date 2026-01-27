import pytest
from httpx import AsyncClient


async def test_debug_routing():
    """Debug test to check if routes are configured"""
    from gateway.config import settings
    from gateway.routing import find_upstream

    print(f"\nRoutes in settings: {settings.routes}")
    print(f"Number of routes: {len(settings.routes)}")

    upstream, suffix = find_upstream("/hello")
    print(f"find_upstream('/hello') = ({upstream}, {suffix})")

    assert len(settings.routes) > 0, "No routes configured!"
    assert upstream == "http://upstream", f"Expected 'http://upstream', got {upstream}"


async def test_proxy_forwards_get_request(gateway_client: AsyncClient):
    resp = await gateway_client.get("/hello")

    assert resp.status_code == 200
    assert resp.json() == {"message": "hello from upstream"}


async def test_proxy_forwards_post_body(gateway_client: AsyncClient):
    payload = {"foo": "bar"}
    resp = await gateway_client.post("/echo", json=payload)

    assert resp.status_code == 200
    assert resp.json() == payload


async def test_proxy_preserves_headers(gateway_client: AsyncClient):
    resp = await gateway_client.get(
    "/hello",
        headers={"x-custom-header": "test123"},
    )

    assert resp.status_code == 200

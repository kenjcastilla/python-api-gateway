import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from gateway.app import application as gateway_app

@pytest.fixture
def upstream_app() -> FastAPI:
    app = FastAPI()     # mock upstream app for testing

    @app.get("/hello")
    async def hello():  # testing path+method forwarding and response body
        return { "message": "hello from upstream" }

    @app.post("/echo")
    async def echo(payload: dict): # testing body forwarding and proxy correctness
        return payload

    return app


@pytest.fixture
async def gateway_client(upstream_app: FastAPI):
    """Gateway test client with upstream mocked via ASGITransport"""
    upstream_transport = ASGITransport(app=upstream_app) # from gateway to upstream app
    upstream_client = AsyncClient(
        transport=upstream_transport,
        base_url="http://upstream"
    )
    # Temporarily change gateway client associated with real gateway app to fake upstream
    #   for testing
    gateway_app.state.http_client = upstream_client

    gateway_transport = ASGITransport(app=gateway_app) # from test to gateway app
    async with AsyncClient(
            transport=gateway_transport,
            base_url="http://gateway"
    ) as client:
        yield client

    await upstream_client.aclose()

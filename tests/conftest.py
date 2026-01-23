# Centralized pytest configuration file (fixtures, hooks, plugins, etc.)

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from gateway.testing.fake_limiter import FakeRateLimiter
from gateway.config import settings, RouteRule
from gateway.main import application as gateway_app

#----Routes overrides for tests----
@pytest.fixture(scope='session', autouse=True)
def set_routes():
    settings.routes = [
        RouteRule(prefix='/hello', upstream='http://upstream'),
        RouteRule(prefix='/echo', upstream='http://upstream'),
    ]


@pytest.fixture
def upstream_app() -> FastAPI:
    app = FastAPI()     # mock upstream app for tests

    @app.get("/")
    async def hello():  # tests path+method forwarding and response body
        return { "message": "hello from upstream" }

    @app.post("/")
    async def echo(payload: dict): # tests body forwarding and proxy correctness
        return payload

    return app


@pytest.fixture
async def gateway_client(upstream_app: FastAPI):
    """Gateway test client with upstream mocked via ASGITransport"""
    # transport from gateway to fake upstream
    upstream_transport = ASGITransport(app=upstream_app)
    upstream_client = AsyncClient(
        transport=upstream_transport,
        base_url="http://upstream"
    )
    async with LifespanManager(gateway_app) as manager:
        # Change state variables associated with real gateway app to tests variables
        gateway_app.state.limiter = FakeRateLimiter()
        gateway_app.state.http_client = upstream_client

        gateway_transport = ASGITransport(app=gateway_app)
        async with AsyncClient(
                transport=gateway_transport,
                base_url="http://gateway") as client:
            yield client

    await upstream_client.aclose()

# Centralized pytest configuration file (fixtures, hooks, plugins, etc.)
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI, Request
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis

from gateway.rate_limit import RateLimiter
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
async def redis_client():
    """Real Redis client for integration testing"""
    redis = Redis.from_url('redis://localhost:6379', decode_responses=True)

    # Verify Redis is running
    try:
        await redis.ping()
    except Exception as e:
        pytest.skip('Redis not available', e)

    yield redis

    # Cleanup
    await redis.flushdb()
    await redis.aclose()


@pytest.fixture
async def rate_limiter(redis_client):
    """Real rate limiter for integration testing"""
    limiter = RateLimiter(redis_client)
    await limiter.load()

    yield limiter


@pytest.fixture
def upstream_app() -> FastAPI:
    app = FastAPI()     # mock upstream app for tests

    @app.get("/")
    async def hello(request: Request):  # tests path+method forwarding and response body
        return {
            "message": "hello from upstream",
            "received_headers": dict(request.headers),
        }

    @app.post("/")
    async def echo(payload: dict): # tests body forwarding and proxy correctness
        return payload

    return app


@pytest.fixture
async def gateway_client(upstream_app: FastAPI):
    """Gateway test client with upstream mocked via ASGITransport"""
    # Transport to fake upstream
    upstream_transport = ASGITransport(app=upstream_app)
    upstream_client = AsyncClient(
        transport=upstream_transport,
        base_url="http://upstream"
    )
    # Lifespan management to handle async testing with gateway.main app
    async with LifespanManager(gateway_app) as manager:
        # Change state variables associated with real gateway app to tests variables
        gateway_app.state.limiter = FakeRateLimiter()
        gateway_app.state.http_client = upstream_client

        # client with transport to gateway app
        gateway_transport = ASGITransport(app=gateway_app)
        async with AsyncClient(
                transport=gateway_transport,
                base_url="http://gateway") as client:
            yield client

    await upstream_client.aclose()

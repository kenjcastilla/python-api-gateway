from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
from os import getenv
from redis.asyncio import Redis
from .rate_limit import RateLimiter
from .routing import find_upstream


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown logic."""
    #---- Startup ----
    if not hasattr(app.state, 'limiter'):
        redis = Redis.from_url(getenv("REDIS_URL", "redis://localhost:6379"))
        print('Redis ping successful:', await redis.ping())

        limiter = RateLimiter(redis)
        await limiter.load()

        app.state.redis = redis
        app.state.limiter = limiter

    if not hasattr(app.state, 'http_client'):
        app.state.http_client = httpx.AsyncClient(timeout=20.0)

    try:
        yield
    finally:
        #---- Shutdown ----
        if hasattr(app.state, 'http_client'):
            await app.state.http_client.aclose()
        if hasattr(app.state, 'redis'):
            await app.state.redis.aclose()

application = FastAPI(lifespan=lifespan)


@application.api_route(
    path="/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request):
    upstream, suffix = find_upstream("/" + path)
    if not upstream:
        raise HTTPException(status_code=404, detail="No upstream route found")

    url = upstream.rstrip("/") + suffix
    raw_headers = request.headers.raw   # raw headers from client
    hop_by_hop_headers = {
            b'connection',
            b'keep-alive',
            b'proxy-authentication',
            b'proxy-authorization',
            b'te',
            b'trailers',
            b'transfer-encoding',
            b'upgrade',
            b'host',
        }
    headers = [
        (k, v) for k, v in raw_headers if k.lower() not in hop_by_hop_headers
    ] # headers excluding hop_by_hop headers

    body = await request.body()

    # ---- Rate Limiting ----
    api_key = request.headers.get("x-api-key") or request.client.host
    key = f"rl:{api_key}:global"

    allowed, _ = await request.app.state.limiter.allow(key, capacity=50, rate=1.0)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # ---- Proxy Request ----
    try:
        resp = await request.app.state.http_client.request(
            request.method,
            url,
            headers=headers,
            content=body,
            params=request.query_params
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    filtered_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in { "content-encoding", "transfer-encoding", "connection" }
    }

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filtered_headers
    )

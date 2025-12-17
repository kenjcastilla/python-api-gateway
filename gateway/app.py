from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
from redis.asyncio import Redis
from .rate_limit import RateLimiter
from .routing import find_upstream

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown logic."""
    #---- Startup ----
    redis = Redis.from_url("redis://localhost:6379")
    await redis.ping()

    limiter = RateLimiter(redis)
    await limiter.load()

    app.state.redis = redis
    app.state.limiter = limiter
    app.state.http_client = httpx.AsyncClient(timeout=20.0)

    try:
        yield
    finally:
        #---- Shutdown ----
        await app.state.http_client.aclose()
        await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request):
    upstream, suffix = find_upstream("/" + path)
    if not upstream:
        raise HTTPException(status_code=404, detail="No upstream route found")

    url = upstream.rstrip("/") + suffix

    headers = dict(request.headers)
    for h in (
        'connection',
        'keep-alive',
        'proxy-authentication',
        'proxy-authorization',
        'te',
        'trailers',
        'transfer-encoding',
        'upgrade',
        'host',
    ): headers.pop(h, None)

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



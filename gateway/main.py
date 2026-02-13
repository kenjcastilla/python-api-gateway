from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
from os import getenv
from redis.asyncio import Redis

from .middleware import RateLimitMiddleware
from .rate_limit import RateLimiter
from .routing import find_upstream


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown logic."""
    #---- Startup ----
    if not hasattr(app.state, 'limiter'):
        redis = Redis.from_url(getenv("REDIS_URL", "redis://localhost:6379"))
        print("Redis ping success:", await redis.ping())

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

application.add_middleware(RateLimitMiddleware, capacity=50, rate=1.0)

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

    # Debugging
    # print('\n\nMAIN---all headers (raw) from initial request:')
    # for k, v in raw_headers:
    #     print(f"\t{k}  =  {v}")

    hop_by_hop_headers = {
            b'connection',
            b'keep-alive',
            b'proxy-authentication',
            b'proxy-authorization',
            b'te',
            b'trailers',
            b'transfer-encoding',
            b'upgrade',
        }

    # decoded headers from raw_headers excluding hop_by_hop headers
    headers = dict()
    for k, v in raw_headers:
        if k == b'host':
            # Preserve original host in new 'X-Forwarded-Host' header
            headers['X-Forwarded-Host'] = v.decode('latin-1')
        elif k not in hop_by_hop_headers:
            headers[k.decode('latin-1')] = v.decode('latin-1')

    headers['X-Forwarded-Proto'] = request.url.scheme
    headers['X-Real-IP'] = request.client.host

    # Debugging
    # print('\nMAIN---headers after removing hopybyhops:')
    # for k, v in headers.items():
    #     print(f"\t{k}  =  {v}")

    body = await request.body()

    # ---- Rate Limiting ----
    # api_key = request.headers.get('x-api-key') or request.client.host
    # key = f"rl:{api_key}:global"
    #
    # allowed, _ = await request.app.state.limiter.allow(key, capacity=50, rate=1.0)
    # if not allowed:
    #     raise HTTPException(status_code=429, detail="Rate limit exceeded")

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

    # Debugging
    # print('\nMAIN---response headers after state client proxy request:')
    # for k, v in resp.headers.items():
    #     print(f"\t{k}  =  {v}")

    filtered_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in {'content-encoding', 'transfer-encoding', 'connection'}
    }

    #Debugging
    # print('\nMAIN---proxy request headers after filtering:')
    # for k, v in filtered_headers.items():
    #     print(f"\t{k}  =  {v}")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filtered_headers
    )

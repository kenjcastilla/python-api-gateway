from fastapi import Request, HTTPException
from .rate_limit import RateLimiter

class RateLimitMiddleware:
    def __init__(self, app, limiter: RateLimiter):
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        api_key = request.headers.get("x-api-key") or scope.get("client")[0]
        key = f"rl:{api_key}:global"

        allowed, _ = await self.limiter.allow(key, capacity=50, rate=1.0)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        await self.app(scope, receive, send)

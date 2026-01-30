from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware for rate limiting all incoming requests.
    Implements token-bucket algorithm with Redis backend.
    """
    def __init__(self, app, capacity: int = 50, rate: float = 1.0):
        super().__init__(app)
        self.capacity = capacity
        self.rate = rate

    async def dispatch(self, request: Request, call_next):
        """Process each request through rate limiter"""

        # Get limiter from app state (set in lifespan)
        limiter = request.app.state.limiter

        # Extract API key (or client IP)
        api_key = request.headers.get('x-api-key') or request.client.host
        key = f"rl:{api_key}:global"

        # Check rate limit
        allowed, remaining_tokens = await limiter.allow(
            key,
            capacity=self.capacity,
            rate=self.rate,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"X-RateLimit-Remaining": str(int(remaining_tokens))},
            )

        # Add rate limit information to response headers
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining_tokens))

        return response

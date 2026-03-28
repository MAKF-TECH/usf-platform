import time

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Health/metrics paths that bypass rate limiting
_EXEMPT_PATHS = frozenset({"/health", "/metrics", "/healthz", "/readyz"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter using Valkey/Redis.

    Keyed per tenant per minute window. Falls back gracefully if Redis
    is unavailable (fail-open to avoid blocking legitimate traffic).
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Get tenant from JWT (already decoded in auth middleware)
        tenant_id = getattr(request.state, "tenant_id", "anonymous")
        key = f"ratelimit:{tenant_id}:{int(time.time() // 60)}"

        try:
            redis = request.app.state.redis if hasattr(request.app.state, "redis") else request.app.state.cache
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
        except Exception:
            # Fail-open: if Valkey is unreachable, allow the request
            response = await call_next(request)
            return response

        if count > self.rpm:
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limit_exceeded", "retry_after": 60},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - count))
        return response
